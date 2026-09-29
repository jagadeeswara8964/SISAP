"""Text cleaning and section detection for tender documents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from utils import get_logger, normalise_whitespace

logger = get_logger("text")

# Section headings commonly used in Indian tender / specification documents.
SECTION_PATTERNS: list[tuple[str, str]] = [
    ("scope_of_work", r"scope of work|scope of supply|brief scope"),
    ("technical_specification", r"technical specification|technical requirement|specification of"),
    ("qualifying_requirement", r"qualifying requirement|eligibility|pre qualification"),
    ("safety_requirements", r"safety requirement|safety provision|statutory requirement|fire safety"),
    ("testing_and_inspection", r"testing|inspection and (?:quality|testing)|acceptance test|factory acceptance"),
    ("installation", r"installation|erection|commissioning|site requirement"),
    ("certification", r"certification|type approval|bis certification|hallmarking|licence"),
    ("materials", r"material (?:specification|requirement)|bill of material|raw material"),
    ("drawings", r"drawing|dimensional drawing|general arrangement"),
    ("terms_and_conditions", r"terms and condition|general condition|contract condition"),
    ("packing_and_delivery", r"packing|delivery schedule|warranty|guarantee"),
    ("payments", r"payment terms|price bid|financial bid"),
]

_SECTION_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+)*)[\.\)]?\s+(?P<title>[A-Z][A-Za-z0-9 ,\-/&()]{3,70})$", re.MULTILINE
)

# Boilerplate that carries no requirement signal.
_NOISE_PATTERNS = [
    re.compile(r"page\s+\d+\s+of\s+\d+", re.IGNORECASE),
    re.compile(r"\b(?:www\.|https?://)\S+", re.IGNORECASE),
    re.compile(r"^\s*(?:tender|nit)\s+(?:no|number)\b.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
]


@dataclass
class Section:
    key: str
    title: str
    text: str


@dataclass
class ProcessedText:
    text: str
    sections: list[Section] = field(default_factory=list)
    sentences: list[str] = field(default_factory=list)
    heading_candidates: list[str] = field(default_factory=list)

    @property
    def section_text(self) -> dict[str, str]:
        return {section.key: section.text for section in self.sections}


class TextProcessor:
    """Cleans raw extracted text and detects logical sections."""

    def process(self, raw_text: str) -> ProcessedText:
        cleaned = self.clean(raw_text)
        sections = self.detect_sections(cleaned)
        sentences = self.segment_sentences(cleaned)
        return ProcessedText(
            text=cleaned,
            sections=sections,
            sentences=sentences,
            heading_candidates=[section.title for section in sections],
        )

    # -- cleaning -----------------------------------------------------------
    def clean(self, raw_text: str) -> str:
        text = normalise_whitespace(raw_text or "")
        text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        for pattern in _NOISE_PATTERNS:
            text = pattern.sub(" ", text)
        # Repair words broken across a hard line wrap (e.g. "speci fication").
        text = re.sub(r"([a-z]{2,})-\n([a-z]{2,})", r"\1\2", text)
        text = re.sub(r"(?<=[a-z])\n(?=[a-z]{2,})", " ", text)
        text = normalise_whitespace(text)
        return text

    # -- sections -----------------------------------------------------------
    def detect_sections(self, text: str) -> list[Section]:
        """Split the document into sections using numbered headings and keywords."""
        matches = list(_SECTION_RE.finditer(text))
        if matches:
            sections: list[Section] = []
            if matches[0].start() > 0:
                sections.append(Section("preamble", "Preamble", text[: matches[0].start()].strip()))
            for index, match in enumerate(matches):
                start = match.start()
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                body = text[match.end() : end].strip()
                title = match.group("title").strip()
                sections.append(Section(self._classify_heading(title), title, body))
            if len(sections) > 1:
                return [section for section in sections if section.text]

        return self._keyword_sections(text)

    def _classify_heading(self, title: str) -> str:
        lowered = title.lower()
        for key, pattern in SECTION_PATTERNS:
            if re.search(pattern, lowered):
                return key
        return "other"

    def _keyword_sections(self, text: str) -> list[Section]:
        """Fallback: bucket paragraphs into keyword-matched sections."""
        buckets: dict[str, list[str]] = {}
        for paragraph in re.split(r"\n{2,}", text):
            if len(paragraph.strip()) < 20:
                continue
            key = self._classify_paragraph(paragraph)
            buckets.setdefault(key, []).append(paragraph.strip())
        return [Section(key, key.replace("_", " ").title(), "\n\n".join(parts)) for key, parts in buckets.items()]

    def _classify_paragraph(self, paragraph: str) -> str:
        lowered = paragraph.lower()
        best_key, best_score = "other", 0
        for key, pattern in SECTION_PATTERNS:
            score = len(re.findall(pattern, lowered))
            if score > best_score:
                best_key, best_score = key, score
        return best_key

    # -- sentences ----------------------------------------------------------
    def segment_sentences(self, text: str) -> list[str]:
        """Split into requirement-bearing sentences, dropping very short fragments."""
        candidates = re.split(r"(?<=[.;])\s+|\n", text)
        sentences = []
        for candidate in candidates:
            sentence = candidate.strip(" -\t")
            if len(sentence) < 15:
                continue
            if sentence.lower().startswith(("figure", "table", "note:", "sl. no")):
                continue
            sentences.append(sentence)
        return sentences


text_processor = TextProcessor()
