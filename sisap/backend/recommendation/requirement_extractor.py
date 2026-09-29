"""Requirement extraction engine.

Pipeline:
    tender text -> sentence segmentation -> keyword/rule classification ->
    structured RequirementObject

An LLM provider is used when configured and enabled; otherwise the deterministic
rule-based path runs, which is what DEMO_MODE relies on.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from ai.llm_provider import LLMProvider, NullProvider, get_llm_provider
from utils import get_logger

logger = get_logger("requirement_extractor")

# ---------------------------------------------------------------- vocabularies
GENERAL_PRODUCT_LEXICON: list[str] = [
    # electrical
    "control panel", "switchgear panel", "switchgear and controlgear assembly", "switchgear assembly",
    "controlgear assembly", "switchboard", "distribution board", "power distribution board",
    "motor control centre", "motor control center", "controlgear", "switchgear",
    "feeder pillar", "busbar trunking system", "busduct", "bus duct", "cable tray", "power cable",
    "control cable", "armoured cable", "transformer", "distribution transformer", "dry type transformer",
    "circuit breaker", "miniature circuit breaker", "moulded case circuit breaker", "fuse", "contactor",
    "earthing electrode", "earth electrode", "earthing system", "wiring installation", "luminarie",
    "ups", "inverter", "battery bank", "capacitor bank", "apfc panel",
    # construction
    "portland cement", "ordinary portland cement", "portland pozzolana cement", "portland slag cement",
    "sulphate resisting cement", "ready mix concrete", "reinforced concrete", "plain concrete",
    "concrete", "cement", "aggregate", "fine aggregate", "coarse aggregate", "reinforcement bar",
    "deformed bar", "tmt bar", "structural steel", "steel section", "steel plate", "steel sheet",
    "steel tube", "hollow section", "paint", "primer", "flooring tile", "formwork", "shuttering",
    # water systems
    "water supply pipe", "upvc pipe", "pvc pipe", "hdpe pipe", "polyethylene pipe", "pipe", "valve",
    "gate valve", "ball valve", "pump", "centrifugal pump", "water tank", "storage tank",
    "flushing cistern", "plumbing system", "sanitary fitting", "overhead tank",
    # mechanical
    "pressure vessel", "air receiver", "casting", "cast iron component", "fastener", "bolt", "stud",
    "gear box", "compressor", "heat exchanger",
    # safety / ppe
    "safety helmet", "industrial safety helmet", "safety shoe", "safety footwear", "safety belt",
    "full body harness", "safety glove", "leather mitten", "eye protector", "safety goggle",
    "face shield", "ppe", "personal protective equipment", "fire extinguisher",
    # electronics
    "information technology equipment", "computer", "monitor", "network switch", "server", "printer",
    "electronic apparatus", "power adapter",
]

MATERIAL_LEXICON: list[str] = [
    "steel", "mild steel", "stainless steel", "carbon steel", "structural steel", "aluminium",
    "aluminum", "copper", "brass", "cast iron", "grey iron", "wrought iron", "zinc", "galvanised steel",
    "pvc", "upvc", "cpvc", "polyethylene", "hdpe", "mdpe", "polypropylene", "xlpe", "rubber", "epoxy",
    "polyester", "polycarbonate", "ceramic", "vitreous china", "concrete", "cement", "mortar", "grout",
    "clay", "sand", "aggregate", "granite", "marble", "glass", "wood", "plywood", "timber", "leather",
    "fibre glass", "frp", "asbestos free sheet", "tiles", "brick", "gypsum", "fly ash", "slag",
    "bitumen", "insulating oil", "crgo steel", "silicon steel",
]

APPLICATION_LEXICON: list[str] = [
    "indoor industrial use", "indoor installation", "outdoor installation", "outdoor use",
    "industrial installation", "commercial building", "residential building", "multi storeyed building",
    "power distribution", "motor control", "substation", "switchroom", "plant room", "control room",
    "building wiring", "panel wiring", "underground installation", "buried installation",
    "high rise building", "water supply", "drainage", "sanitation", "sewage", "irrigation",
    "marine environment", "coastal area", "hazardous area", "explosive atmosphere", "fire prone area",
    "food processing", "pharmaceutical", "textile", "chemical plant", "refinery", "power plant",
    "transport", "railway", "metro", "airport", "hospital", "school", "data centre", "telecom",
    "construction site", "workshop", "foundry", "mine",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Electrical": [
        "electrical", "electric", "voltage", "current", "switchgear", "controlgear", "panel", "cable",
        "transformer", "circuit breaker", "earthing", "wiring", "kv", "amp", "kva", "kw", "volt",
        "busbar", "switchboard", "contactor", "fuse", "ip rating", "insulation",
    ],
    "Cement": ["cement", "opc", "ppc", "psc", "clinker", "fineness", "setting time", "grade cement"],
    "Construction": [
        "concrete", "reinforcement", "aggregate", "formwork", "flooring", "plaster", "masonry",
        "structural", "seismic", "earthquake", "building", "civil work", "rcc",
    ],
    "Steel": ["steel", "tmt", "rebar", "structural steel", "hollow section", "plate", "sheet", "welding"],
    "Water Systems": [
        "water supply", "plumbing", "pipe", "pipeline", "valve", "pump", "tank", "drainage",
        "sanitation", "water", "cistern", "sump",
    ],
    "Mechanical Equipment": [
        "mechanical", "pressure vessel", "casting", "compressor", "pump", "gear", "fabrication",
        "machining", "boiler", "heat exchanger",
    ],
    "Safety Equipment": [
        "safety", "ppe", "helmet", "shoe", "glove", "goggle", "harness", "protective", "fall protection",
        "eye protection", "respirator",
    ],
    "Electronics": [
        "electronics", "computer", "monitor", "network", "server", "display", "audio", "video",
        "information technology", "adapter", "charger",
    ],
}

# Weighted signals used to classify a sentence into a requirement bucket.
BUCKET_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "certification_requirements": [
        (r"\bcertificat\w*", 3.0), (r"\bbis\b", 2.5), (r"\bisi\b", 2.5), (r"\btype approval\b", 3.0),
        (r"\bhallmark\w*", 2.0), (r"\blicen[cs]e\b", 2.0), (r"\bmarking\b", 1.5),
        (r"\bthird party inspection\b", 2.0), (r"\bqco\b", 2.0), (r"\bconformity\w*", 2.0),
        (r"\bstamping\b", 1.5), (r"\bregistration with bis\b", 3.0),
    ],
    "testing_requirements": [
        (r"\btest(?:s|ed|ing)?\b", 2.5), (r"\bmethod of test\b", 3.0), (r"\btype test\b", 3.0),
        (r"\broutine test\b", 3.0), (r"\bacceptance test\b", 3.0), (r"\bfactory acceptance\b", 3.0),
        (r"\binspection\b", 2.0), (r"\bsampling\b", 2.0), (r"\bquality (?:control|assurance)\b", 2.0),
        (r"\bcertificate of test\b", 2.5), (r"\bnon[- ]destructive\b", 2.5), (r"\bndt\b", 2.0),
        (r"\bhydrostatic test\b", 3.0), (r"\bendurance\b", 1.5), (r"\bcalibrat\w*", 2.0),
    ],
    "safety_requirements": [
        (r"\bsafety\b", 3.0), (r"\bsafe\b", 2.0), (r"\bprotection against\b", 2.5),
        (r"\bearthing\b", 2.5), (r"\bearth(?:ed)?\b", 1.5), (r"\bshock\b", 2.5),
        (r"\bhazard\w*", 2.5), (r"\bfire\b", 2.0), (r"\bflame\w*", 2.0), (r"\barc\b", 2.0),
        (r"\bemergency\b", 2.0), (r"\bppe\b", 2.5), (r"\bpersonal protective\b", 2.5),
        (r"\bclearance\b", 1.5), (r"\bcreepage\b", 1.5), (r"\bstatutory\b", 1.5),
        (r"\bintrinsically safe\b", 2.5), (r"\bexplosive atmosphere\b", 2.0),
    ],
    "installation_requirements": [
        (r"\binstallation\b", 3.0), (r"\binstall\b", 2.5), (r"\berection\b", 2.5), (r"\berected\b", 2.5),
        (r"\bmounting\b", 2.5), (r"\bmounted\b", 2.0), (r"\bcommissioning\b", 2.5), (r"\bsite\b", 1.5),
        (r"\bfoundation\b", 2.0), (r"\blaying\b", 2.0), (r"\bjointing\b", 2.0), (r"\bcable entry\b", 2.5),
        (r"\bcable tray\b", 2.0), (r"\bconduit\b", 2.0), (r"\bventilation\b", 1.5), (r"\bmaintenance\b", 1.5),
        (r"\berection drawing\b", 2.5), (r"\btrench\w*", 2.0),
    ],
    "performance_requirements": [
        (r"\bperformance\b", 2.5), (r"\befficiency\b", 2.5), (r"\bcapacity\b", 2.0),
        (r"\brating\b", 1.5), (r"\btemperature rise\b", 2.5), (r"\boutput\b", 2.0),
        (r"\blife\b", 1.5), (r"\bendurance\b", 2.0), (r"\bnoise\b", 2.0), (r"\bvoltage drop\b", 2.5),
        (r"\bdegree of protection\b", 2.5), (r"\bip\d{2}\b", 2.5), (r"\bpower factor\b", 2.5),
        (r"\bconsumption\b", 1.5), (r"\bwithstand\b", 2.0), (r"\bip protection\b", 2.5),
        (r"\bprotection class\b", 2.0), (r"\bclass of insulation\b", 2.5), (r"\blosses\b", 1.5),
    ],
    "technical_requirements": [
        (r"\bdimension\w*", 2.0), (r"\bsize\b", 1.5), (r"\bthickness\b", 2.0), (r"\btolerance\b", 2.0),
        (r"\bfinish\b", 1.5), (r"\bdesign\b", 1.5), (r"\bconstruction\b", 1.5), (r"\bmaterial\b", 2.0),
        (r"\bvoltage\b", 2.0), (r"\bcurrent\b", 1.5), (r"\bkv\b", 1.5), (r"\bamp(?:ere)?s?\b", 1.5),
        (r"\bspecification\b", 1.5), (r"\bstandard\b", 1.5), (r"\bshall\b", 1.5), (r"\bmust\b", 1.5),
        (r"\brequired\b", 1.5), (r"\bgrade\b", 1.5), (r"\bcoating\b", 1.5), (r"\bpaint\b", 1.5),
        (r"\bweight\b", 1.5), (r"\bcolour\b", 1.0),
    ],
}

# Priority order used to break scoring ties (more specific buckets win).
BUCKET_PRIORITY = [
    "certification_requirements",
    "testing_requirements",
    "safety_requirements",
    "installation_requirements",
    "performance_requirements",
    "technical_requirements",
]

_LEADING_NOISE_RE = re.compile(
    r"^(?:\(?[a-z0-9]{1,3}[\).]\s*|[-•*]\s*|"
    r"(?:the|this|all)\s+(?:tender|specification|document|vendor|supplier|contractor|bidder|offer|"
    r"equipment|material|item|panel|product)\s+(?:shall|must|should|is required to|are required to|"
    r"needs to|has to)\s+|"
    r"(?:the|this)\s+\w+\s+(?:shall|must|should)\s+(?:be|have|conform|comply|meet)\s+)+",
    re.IGNORECASE,
)

_NUMBERING_RE = re.compile(
    r"^\s*(?:\(?\d+(?:\.\d+)*[\).]?|\d+\.|[a-z][\)\.]|[-•*])\s+", re.IGNORECASE
)
# A line that begins a new list item / clause.
_ITEM_START_RE = re.compile(r"^\s*(?:\(?\d+(?:\.\d+)*[\)\.]?|[a-z][\)\.]|[-•*])\s+", re.IGNORECASE)
# A short all-caps line is almost always a heading, not a requirement.
_HEADING_RE = re.compile(r"^[A-Z0-9 .,/\-&()]{4,70}$")
# Sentences about the document itself (demo/evaluator notes) are not requirements.
_META_SENTENCE_RE = re.compile(
    r"\b(?:demonstration document|for evaluators|this is a demonstration|sisap|demo dataset)\b", re.IGNORECASE
)


@dataclass
class ExtractionResult:
    requirements: dict
    extraction_method: str
    sentences_classified: int = 0
    matched_products: list[str] = field(default_factory=list)
    matched_materials: list[str] = field(default_factory=list)
    matched_applications: list[str] = field(default_factory=list)


class RequirementExtractor:
    """Extracts a structured requirement object from tender text."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        standards: Sequence[dict] | None = None,
    ) -> None:
        self._llm = llm_provider if llm_provider is not None else get_llm_provider()
        self._standards = list(standards or [])
        self._product_terms = self._build_product_terms()
        self._material_terms = MATERIAL_LEXICON
        self._application_terms = APPLICATION_LEXICON
        self._category_terms = CATEGORY_KEYWORDS

    # -- vocabulary construction -------------------------------------------
    def _build_product_terms(self) -> list[str]:
        """Dataset product types first (domain specific), then the general lexicon."""
        terms: list[str] = list(GENERAL_PRODUCT_LEXICON)
        seen = {term.lower() for term in terms}
        for standard in self._standards:
            for product in standard.get("product_types", []) or []:
                key = product.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    terms.append(product.strip())
        # Longer terms first so that "switchgear assembly" wins over "switchgear".
        return sorted(terms, key=lambda term: (-len(term), term))

    # -- public API ---------------------------------------------------------
    def extract(self, text: str, use_llm: bool = False) -> ExtractionResult:
        text = (text or "").strip()
        if not text:
            return ExtractionResult(requirements=self._empty(), extraction_method="empty")

        if use_llm and not isinstance(self._llm, NullProvider):
            llm_result = self._llm.extract_requirements(text)
            if llm_result:
                logger.info("requirements extracted via LLM provider")
                merged = self._empty()
                merged.update(llm_result)
                return ExtractionResult(
                    requirements=merged,
                    extraction_method="llm",
                    matched_products=self._match_terms(text, self._product_terms),
                    matched_materials=self._match_terms(text, self._material_terms),
                    matched_applications=self._match_terms(text, self._application_terms),
                )
            logger.warning("LLM extraction unavailable; falling back to rule-based extraction")

        return self._rule_based_extract(text)

    # -- rule based extraction ---------------------------------------------
    def _rule_based_extract(self, text: str) -> ExtractionResult:
        lowered = text.lower()
        sentences = self._sentences(text)

        products = self._match_terms(text, self._product_terms)
        materials = self._match_terms(text, self._material_terms)
        applications = self._match_terms(text, self._application_terms)

        product = self._select_product(products, text)
        category = self._infer_category(lowered, products)
        intended_use = self._infer_intended_use(sentences, applications)

        buckets: dict[str, list[str]] = {key: [] for key in BUCKET_PRIORITY}
        for sentence in sentences:
            if _META_SENTENCE_RE.search(sentence):
                continue
            bucket = self._classify_sentence(sentence)
            if bucket is None:
                continue
            phrase = self._to_requirement_phrase(sentence)
            if phrase and phrase not in buckets[bucket]:
                buckets[bucket].append(phrase)

        requirements = {
            "product": product,
            "category": category,
            "intended_use": intended_use,
            "materials": materials[:12],
            "technical_requirements": buckets["technical_requirements"][:14],
            "performance_requirements": buckets["performance_requirements"][:14],
            "safety_requirements": buckets["safety_requirements"][:14],
            "testing_requirements": buckets["testing_requirements"][:14],
            "installation_requirements": buckets["installation_requirements"][:14],
            "certification_requirements": buckets["certification_requirements"][:14],
        }
        return ExtractionResult(
            requirements=requirements,
            extraction_method="rule-based",
            sentences_classified=len(sentences),
            matched_products=products,
            matched_materials=materials,
            matched_applications=applications,
        )

    def _sentences(self, text: str) -> list[str]:
        """Flow wrapped lines into items, then split each item into sentences.

        PDF extraction inserts line breaks mid-sentence, so lines are re-joined
        unless they start a new clause/item or look like a heading.
        """
        dehyphenated = re.sub(r"(?<=[a-z])-(?=\n[a-z])", "", text)
        sentences: list[str] = []

        for block in re.split(r"\n\s*\n", dehyphenated):
            current = ""
            for raw_line in block.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                core = _NUMBERING_RE.sub("", line).strip()
                if _HEADING_RE.match(core) and not core.endswith((".", ";", ":")):
                    if current:
                        sentences.append(current)
                        current = ""
                    sentences.append(core)
                    continue
                if not current:
                    current = line
                elif _ITEM_START_RE.match(line) and current.rstrip().endswith((".", ":", ";", "!", "?")):
                    sentences.append(current)
                    current = line
                else:
                    current = f"{current} {line}"
            if current:
                sentences.append(current)

        results: list[str] = []
        for item in sentences:
            if self._is_heading(item):
                continue
            for sentence in re.split(r"(?<=[.;])\s+(?=[A-Z0-9\"(])", item):
                cleaned = sentence.strip(" -\t")
                if len(cleaned) < 20 or len(cleaned) > 600:
                    continue
                if cleaned.lower().startswith(("figure", "table", "note:", "sl. no", "page ", "annexure")):
                    continue
                results.append(cleaned)
        return results[:400]

    @staticmethod
    def _is_heading(item: str) -> bool:
        """True for short all-caps lines such as section headings."""
        if re.search(r"[a-z]", item):
            return False
        return len(item) < 70

    @staticmethod
    def _match_terms(text: str, terms: Iterable[str]) -> list[str]:
        """Count lexicon terms in the text, tolerating simple plural forms."""
        lowered = text.lower()
        matched: list[tuple[int, int, str]] = []
        for term in terms:
            key = term.lower()
            if len(key) < 3:
                continue
            count = len(re.findall(RequirementExtractor._term_pattern(key), lowered))
            if count:
                matched.append((count, len(key), term))
        matched.sort(key=lambda item: (-item[0], -item[1]))
        return [term for _, _, term in matched]

    @staticmethod
    def _term_pattern(key: str) -> str:
        """Word-boundary pattern for a term, allowing a trailing plural suffix."""
        return r"(?<![a-z0-9])" + re.escape(key) + r"(?:s|es)?(?![a-z0-9])"

    def _select_product(self, products: list[str], text: str) -> str:
        """Pick the most representative product term.

        Preference order: a term appearing in the document head (title / scope
        area, which usually names the product), then frequency, then length.
        """
        if not products:
            return ""

        # The document head (title / scope) almost always names the product.
        head = text[:400].lower()
        head_counts = {
            term: len(re.findall(self._term_pattern(term.lower()), head))
            for term in products
            if len(term) >= 3
        }
        head_counts = {term: count for term, count in head_counts.items() if count}
        if head_counts:
            best = max(head_counts.items(), key=lambda item: (item[1], len(item[0])))
            return best[0]

        # Otherwise prefer the most frequent specific (multi-word) term.
        specific = [term for term in products if " " in term or len(term) > 6]
        return (specific or products)[0]

    def _infer_category(self, lowered_text: str, products: list[str]) -> str:
        """Infer the product category.

        Two signals are combined:
          1. category keyword hits in the document, and
          2. a vote from the standards whose product_types match the extracted
             products, weighted by how specific the matched product term is.
        """
        scores: dict[str, float] = {}
        for category, keywords in self._category_terms.items():
            scores[category] = float(sum(1 for keyword in keywords if keyword in lowered_text))

        for term in products[:4]:
            specificity = len(term) / 10.0
            for standard in self._standards:
                if any(term.lower() == product.lower() for product in standard.get("product_types", []) or []):
                    category = standard.get("category", "")
                    if category:
                        scores[category] = scores.get(category, 0.0) + specificity

        if not scores or max(scores.values()) <= 0:
            return ""
        return max(scores, key=lambda category: scores[category])

    def _infer_intended_use(self, sentences: list[str], applications: list[str]) -> str:
        """Derive a short intended-use phrase from application matches."""
        if applications:
            return ", ".join(applications[:3])
        for sentence in sentences[:20]:
            match = re.search(r"\b(?:for|in|used for|suitable for)\s+([^.;:]{6,90})", sentence, re.IGNORECASE)
            if match:
                phrase = match.group(1).strip(" ,")
                if 6 <= len(phrase) <= 90:
                    return phrase
        return ""

    @staticmethod
    def _classify_sentence(sentence: str) -> str | None:
        lowered = sentence.lower()
        scores: dict[str, float] = {}
        for bucket, signals in BUCKET_SIGNALS.items():
            score = 0.0
            for pattern, weight in signals:
                if re.search(pattern, lowered):
                    score += weight
            scores[bucket] = score

        best_score = max(scores.values()) if scores else 0
        if best_score < 2.0:
            return None
        best_buckets = [bucket for bucket in BUCKET_PRIORITY if scores.get(bucket) == best_score]
        return best_buckets[0]

    @staticmethod
    def _to_requirement_phrase(sentence: str) -> str:
        phrase = sentence.strip()
        for _ in range(4):
            stripped = _NUMBERING_RE.sub("", phrase).strip(" -:;,")
            stripped = _LEADING_NOISE_RE.sub("", stripped).strip(" -:;,")
            if stripped == phrase:
                break
            phrase = stripped
        phrase = re.sub(r"\s+", " ", phrase)
        if len(phrase) > 200:
            phrase = phrase[:199].rstrip() + "…"
        return phrase[:1].upper() + phrase[1:] if phrase else ""

    @staticmethod
    def _empty() -> dict:
        return {
            "product": "",
            "category": "",
            "intended_use": "",
            "materials": [],
            "technical_requirements": [],
            "performance_requirements": [],
            "safety_requirements": [],
            "testing_requirements": [],
            "installation_requirements": [],
            "certification_requirements": [],
        }
