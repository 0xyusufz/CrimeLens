"""Text normalization and sanitization interface.

Produces deterministic, clean text while strictly preserving:
- Line structure and paragraphs
- Identifiers (phones, accounts, vehicle plates)
- Dates, times, and transaction amounts
- Non-English Unicode characters and currency symbols
- Exact wording required for downstream evidence snippets

Idempotent: normalize_text(normalize_text(t)) == normalize_text(t)
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class PreprocessedText:
    """Container preserving both raw and normalized text for evidence tracing."""

    raw_text: str
    normalized_text: str
    line_count: int
    char_count: int


def normalize_text(text: str) -> str:
    """Normalize whitespace and line endings while preserving content and identifiers.

    Args:
        text: Raw document text string.

    Returns:
        str: Cleaned, normalized text.

    Raises:
        TypeError: If input is not a string.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not text:
        return ""

    # 1. Unicode normalization (NFC preserves characters, accents, and currency symbols)
    normalized = unicodedata.normalize("NFC", text)

    # 2. Line ending normalization (CRLF / CR -> LF)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Normalize horizontal whitespace per line and strip line margins
    # Matches horizontal whitespace characters (spaces, tabs, non-breaking spaces)
    cleaned_lines = []
    for line in normalized.split("\n"):
        # Collapse multiple horizontal whitespace characters to a single space
        line_clean = re.sub(r"[^\S\n]+", " ", line).strip()
        cleaned_lines.append(line_clean)

    joined = "\n".join(cleaned_lines)

    # 4. Collapse 3 or more consecutive newlines to 2 newlines (preserves paragraph separation)
    collapsed = re.sub(r"\n{3,}", "\n\n", joined)

    # 5. Trim leading and trailing whitespace from the full document
    return collapsed.strip()


def preprocess_text(raw_text: str) -> PreprocessedText:
    """Preprocess text, returning a container with both raw and normalized text."""
    normalized = normalize_text(raw_text)
    lines = normalized.split("\n") if normalized else []
    return PreprocessedText(
        raw_text=raw_text,
        normalized_text=normalized,
        line_count=len(lines),
        char_count=len(normalized),
    )
