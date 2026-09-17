"""Page-wise OCR fallback for image-only PDFs."""

from __future__ import annotations

from typing import Any

from ml.ocr.tesseract import extract_text_from_image


def extract_text_from_pdf(data: bytes, lang: str = "eng") -> dict[str, Any]:
    """Render and OCR a scanned PDF while preserving page numbers."""
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for scanned PDF OCR.") from exc

    try:
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("Invalid PDF document.") from exc

    pages: list[str] = []
    blocks: list[dict[str, Any]] = []
    try:
        for page_number, page in enumerate(pdf, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_bytes = pixmap.tobytes("png")
            text = extract_text_from_image(page_bytes, lang=lang)
            pages.append(text.strip())
            blocks.append({
                "page": page_number,
                "line_id": 1,
                "text": text.strip(),
                "confidence": 0.75,
                "bbox": None,
            })
    finally:
        pdf.close()

    return {"text": "\n\n".join(page for page in pages if page), "blocks": blocks}


__all__ = ["extract_text_from_pdf"]
