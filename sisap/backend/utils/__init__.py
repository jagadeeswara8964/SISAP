"""Shared utilities: logging and text normalisation helpers."""

from __future__ import annotations

import logging
import re
import sys

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """Return a consistently formatted logger for the given module name."""
    global _CONFIGURED
    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"))
        root = logging.getLogger("sisap")
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False
        _CONFIGURED = True
    return logging.getLogger(f"sisap.{name}")


_WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_NON_PRINTABLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalise_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs and blank lines without destroying structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = _NON_PRINTABLE_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return _MULTI_NEWLINE_RE.sub("\n\n", text).strip()


def truncate(text: str, limit: int = 240) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback
