"""Lightweight document-understanding and evidence provenance primitives.

This module intentionally does not call a provider or summarize evidence.  It
creates deterministic blocks and a document-type hint so downstream providers
can be given bounded, traceable input.  The hint is advisory only and never
changes the frozen extraction contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


DOCUMENT_TYPES = (
    "FIR",
    "CDR",
    "TRANSACTION_LEDGER",
    "SEIZURE_MEMO",
    "TRANSCRIPT",
    "GENERIC_EVIDENCE",
)


@dataclass(frozen=True)
class EvidenceBlock:
    """A stable character-range reference into normalized document text."""

    block_id: str
    text: str
    start_char: int
    end_char: int
    ordinal: int
    page_number: int = 1
    line_id: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class DocumentUnderstanding:
    """Internal understanding result; not serialized into API envelopes."""

    document_id: str
    document_type: str
    source_kind: str
    blocks: tuple[EvidenceBlock, ...]
    ocr_confidence: float | None = None

    @property
    def block_count(self) -> int:
        return len(self.blocks)


def _classify_document(text: str, filename: str | None = None) -> str:
    haystack = f"{filename or ''}\n{text}".lower()
    scores = {
        "FIR": ("first information report", "fir", "crime no", "police station"),
        "CDR": ("call detail record", "cdr", "caller", "callee", "cell id"),
        "TRANSACTION_LEDGER": (
            "transaction ledger",
            "bank statement",
            "sender",
            "recipient",
            "upi",
            "transaction id",
        ),
        "SEIZURE_MEMO": ("seizure memo", "seized", "inventory of articles", "panchnama"),
        "TRANSCRIPT": ("transcript", "statement of", "question:", "answer:"),
    }
    ranked = sorted(
        ((sum(token in haystack for token in tokens), name) for name, tokens in scores.items()),
        key=lambda item: (-item[0], item[1]),
    )
    return ranked[0][1] if ranked and ranked[0][0] else "GENERIC_EVIDENCE"


def _coerce_bbox(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        return tuple(float(item) for item in value)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def _make_ocr_blocks(text: str, ocr_blocks: Iterable[dict[str, Any]]) -> tuple[EvidenceBlock, ...]:
    blocks: list[EvidenceBlock] = []
    search_start = 0
    for ordinal, raw in enumerate(ocr_blocks, start=1):
        snippet = str(raw.get("text") or "").strip()
        if not snippet:
            continue
        start = text.find(snippet, search_start)
        if start < 0:
            start = text.find(snippet)
        if start < 0:
            continue
        end = start + len(snippet)
        search_start = end
        confidence = raw.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None
        blocks.append(
            EvidenceBlock(
                block_id=f"block_{ordinal:03d}",
                text=text[start:end],
                start_char=start,
                end_char=end,
                ordinal=ordinal,
                page_number=max(1, int(raw.get("page") or 1)),
                line_id=(int(raw["line_id"]) if raw.get("line_id") is not None else None),
                bbox=_coerce_bbox(raw.get("bbox")),
                confidence=confidence,
            )
        )
    return tuple(blocks)


def _make_source_page_blocks(
    text: str,
    source_pages: Iterable[dict[str, Any]],
) -> tuple[EvidenceBlock, ...]:
    blocks: list[EvidenceBlock] = []
    search_start = 0
    for ordinal, raw in enumerate(source_pages, start=1):
        page_text = str(raw.get("text") or "").strip()
        if not page_text:
            continue
        start = text.find(page_text, search_start)
        if start < 0:
            start = text.find(page_text)
        if start < 0:
            continue
        end = start + len(page_text)
        search_start = end
        confidence = raw.get("confidence")
        try:
            confidence = max(0.0, min(1.0, float(confidence))) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None
        blocks.append(
            EvidenceBlock(
                block_id=f"block_{ordinal:03d}",
                text=text[start:end],
                start_char=start,
                end_char=end,
                ordinal=ordinal,
                page_number=max(1, int(raw.get("page") or raw.get("page_number") or ordinal)),
                confidence=confidence,
            )
        )
    return tuple(blocks)


def _make_blocks(
    text: str,
    block_size: int = 2400,
    ocr_blocks: Iterable[dict[str, Any]] | None = None,
    source_pages: Iterable[dict[str, Any]] | None = None,
) -> tuple[EvidenceBlock, ...]:
    if not text:
        return ()

    if ocr_blocks:
        captured = _make_ocr_blocks(text, ocr_blocks)
        if captured:
            return captured
    if source_pages:
        captured = _make_source_page_blocks(text, source_pages)
        if captured:
            return captured

    # Prefer paragraphs/sentences, then bound unusually large blocks.  Ranges
    # always point into the exact normalized text passed to this function.
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|$)", text):
        start, end = match.span()
        if end - start <= block_size:
            spans.append((start, end))
            continue
        cursor = start
        while cursor < end:
            cut = min(cursor + block_size, end)
            if cut < end:
                boundary = text.rfind(" ", cursor, cut)
                if boundary > cursor + block_size // 2:
                    cut = boundary
            spans.append((cursor, cut))
            cursor = cut
            while cursor < end and text[cursor].isspace():
                cursor += 1

    return tuple(
        EvidenceBlock(
            block_id=f"block_{index:03d}",
            text=text[start:end],
            start_char=start,
            end_char=end,
            ordinal=index,
        )
        for index, (start, end) in enumerate(spans, start=1)
        if text[start:end].strip()
    )


def understand_document(
    text: str,
    document_id: str,
    *,
    filename: str | None = None,
    source_kind: str = "text",
    ocr_confidence: float | None = None,
    ocr_blocks: Iterable[dict[str, Any]] | None = None,
    source_pages: Iterable[dict[str, Any]] | None = None,
) -> DocumentUnderstanding:
    """Build deterministic document type and block provenance metadata."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if ocr_confidence is not None:
        ocr_confidence = max(0.0, min(1.0, float(ocr_confidence)))
    return DocumentUnderstanding(
        document_id=str(document_id),
        document_type=_classify_document(text, filename),
        source_kind=source_kind,
        blocks=_make_blocks(text, ocr_blocks=ocr_blocks, source_pages=source_pages),
        ocr_confidence=ocr_confidence,
    )


def evidence_is_grounded(snippet: str, text: str) -> bool:
    """Return whether a snippet is grounded in the source text."""
    if not snippet or not text:
        return False
    s_raw = snippet.strip()
    if s_raw in text:
        return True
    s_clean = " ".join(s_raw.split()).lower()
    t_clean = " ".join(text.split()).lower()
    if s_clean in t_clean:
        return True
    words = [w for w in re.findall(r"\w+", s_clean) if len(w) > 2]
    if not words:
        return False
    matched = sum(1 for w in words if w in t_clean)
    return (matched / len(words)) >= 0.65


__all__ = [
    "DOCUMENT_TYPES",
    "DocumentUnderstanding",
    "EvidenceBlock",
    "evidence_is_grounded",
    "understand_document",
]
