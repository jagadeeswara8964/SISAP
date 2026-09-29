"""Optional LLM abstraction for requirement extraction.

SISAP works fully offline in DEMO_MODE: if no API key is configured the
``NullProvider`` is used and the deterministic rule-based extractor runs
instead. Only ``SISAP_LLM_API_KEY`` (server-side) is ever read; nothing is
exposed to the frontend.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Protocol

from config import settings
from utils import get_logger

logger = get_logger("llm")

SYSTEM_PROMPT = (
    "You are a procurement standards analyst. Extract structured requirements from an "
    "Indian tender or product specification. Respond with JSON only, using exactly these "
    "keys: product, category, intended_use, materials, technical_requirements, "
    "performance_requirements, safety_requirements, testing_requirements, "
    "installation_requirements, certification_requirements. Use short phrases. "
    "Never invent requirements that are not stated in the document. If a field is absent, "
    "use an empty string or empty list."
)

REQUIREMENT_KEYS = (
    "product",
    "category",
    "intended_use",
    "materials",
    "technical_requirements",
    "performance_requirements",
    "safety_requirements",
    "testing_requirements",
    "installation_requirements",
    "certification_requirements",
)

_LIST_KEYS = {k for k in REQUIREMENT_KEYS if k.endswith("s") or k == "materials"}


class LLMProvider(Protocol):
    name: str

    def extract_requirements(self, text: str) -> dict | None: ...


class NullProvider:
    """Used when no LLM is configured (DEMO_MODE)."""

    name = "none"

    def extract_requirements(self, text: str) -> dict | None:
        return None


class _HttpProvider:
    """Shared JSON-over-HTTP helper (no third-party SDK required)."""

    name = "http"

    def __init__(self, url: str, headers: dict, payload: dict, timeout: int = 60) -> None:
        self._url = url
        self._headers = headers
        self._payload = payload
        self._timeout = timeout

    def _post(self) -> dict:
        request = urllib.request.Request(
            self._url,
            data=json.dumps(self._payload).encode("utf-8"),
            headers=self._headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _coerce(raw: str) -> dict | None:
        """Parse the model's JSON payload into the requirement object shape."""
        if not raw:
            return None
        candidate = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
        if fenced:
            candidate = fenced.group(1).strip()
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None

        result: dict = {}
        for key in REQUIREMENT_KEYS:
            value = parsed.get(key, "" if key in ("product", "category", "intended_use") else [])
            if key in _LIST_KEYS:
                if isinstance(value, str):
                    value = [part.strip() for part in re.split(r"[;\n]", value) if part.strip()]
                elif isinstance(value, list):
                    value = [str(item).strip() for item in value if str(item).strip()]
                else:
                    value = [str(value)]
            else:
                value = "" if value is None else str(value).strip()
            result[key] = value
        return result


class AnthropicProvider(_HttpProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        url = (base_url or "https://api.anthropic.com") + "/v1/messages"
        super().__init__(
            url=url,
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            payload={
                "model": model,
                "max_tokens": 1500,
                "temperature": 0,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": "Tender text:\n" + text[:20000]}],
            },
        )

    def extract_requirements(self, text: str) -> dict | None:
        try:
            payload = self._post()
            content = payload.get("content", [])
            raw = "".join(block.get("text", "") for block in content if isinstance(block, dict))
            return self._coerce(raw)
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            logger.warning("anthropic extraction failed: %s", exc)
            return None


class OpenAICompatProvider(_HttpProvider):
    name = "openai-compatible"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        url = (base_url or "https://api.openai.com/v1") + "/chat/completions"
        super().__init__(
            url=url,
            headers={"content-type": "application/json", "authorization": f"Bearer {api_key}"},
            payload={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "Tender text:\n" + text[:20000]},
                ],
            },
        )

    def extract_requirements(self, text: str) -> dict | None:
        try:
            payload = self._post()
            choices = payload.get("choices", [])
            raw = choices[0]["message"]["content"] if choices else ""
            return self._coerce(raw)
        except (urllib.error.URLError, KeyError, IndexError, ValueError) as exc:
            logger.warning("openai-compatible extraction failed: %s", exc)
            return None


def get_llm_provider() -> LLMProvider:
    """Resolve the configured LLM provider, or the NullProvider in DEMO_MODE."""
    if not settings.llm_api_key:
        return NullProvider()

    provider = settings.llm_provider
    if provider == "anthropic" or (provider == "auto" and settings.llm_base_url is None):
        return AnthropicProvider(settings.llm_api_key, settings.llm_model, settings.llm_base_url)
    return OpenAICompatProvider(settings.llm_api_key, settings.llm_model, settings.llm_base_url)
