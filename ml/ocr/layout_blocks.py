"""Tesseract TSV parsing for page/line/bounding-box provenance."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import os
import shutil
import subprocess
import tempfile
from typing import Iterable

from ml.ocr.tesseract import OCRProcessingError, OCREngineUnavailableError


@dataclass(frozen=True)
class OCRBlock:
    page: int
    line_id: int
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return {
            "page": self.page,
            "line_id": self.line_id,
            "text": self.text,
            "bbox": list(self.bbox),
            "confidence": self.confidence,
        }


def _find_tesseract() -> str:
    executable = shutil.which("tesseract")
    if executable:
        return executable
    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.isfile(candidate):
            return candidate
    raise OCREngineUnavailableError("Tesseract OCR engine is not installed or not found in system PATH.")


def extract_tesseract_blocks(image_bytes: bytes, lang: str = "eng") -> list[OCRBlock]:
    """Extract line-level OCR blocks with confidence and bounding boxes."""
    executable = _find_tesseract()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temporary:
        temporary.write(image_bytes)
        path = temporary.name
    try:
        result = subprocess.run(
            [executable, path, "stdout", "-l", lang, "tsv"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            raise OCRProcessingError(f"Tesseract TSV extraction failed: {result.stderr.strip()}")
    finally:
        if os.path.exists(path):
            os.remove(path)

    groups: dict[tuple[int, int, int, int], list[dict[str, str]]] = {}
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        text = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf") or -1)
        except ValueError:
            confidence = -1
        if not text or confidence < 0:
            continue
        key = (
            int(row.get("page_num") or 1),
            int(row.get("block_num") or 0),
            int(row.get("par_num") or 0),
            int(row.get("line_num") or 0),
        )
        groups.setdefault(key, []).append(row)

    blocks: list[OCRBlock] = []
    for line_id, ((page, _, _, _), words) in enumerate(sorted(groups.items()), start=1):
        lefts = [float(word.get("left") or 0) for word in words]
        tops = [float(word.get("top") or 0) for word in words]
        rights = [float(word.get("left") or 0) + float(word.get("width") or 0) for word in words]
        bottoms = [float(word.get("top") or 0) + float(word.get("height") or 0) for word in words]
        confidences = [max(0.0, min(100.0, float(word.get("conf") or 0))) for word in words]
        blocks.append(
            OCRBlock(
                page=page,
                line_id=line_id,
                text=" ".join((word.get("text") or "").strip() for word in words),
                bbox=(min(lefts), min(tops), max(rights), max(bottoms)),
                confidence=round(sum(confidences) / len(confidences) / 100.0, 4),
            )
        )
    return blocks


__all__ = ["OCRBlock", "extract_tesseract_blocks"]
