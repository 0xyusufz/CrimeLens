"""PDF processing implementation using PyMuPDF.

Handles both native text extraction and scanned image rasterization.

Routing:
- Native/text PDF  → page.get_text() → existing extraction pipeline
- Scanned PDF      → page.get_pixmap() → existing Tesseract OCR → existing extraction pipeline
- Image files      → existing Tesseract path (unchanged, not handled here)
- TXT / CSV        → existing text / structured-record paths (unchanged, not handled here)

OCR failures (e.g. Tesseract not installed) are raised as PDFProcessingError so the
caller receives a clear, actionable error rather than a false HTTP 200 with empty results.
"""

import pymupdf as fitz  # PyMuPDF – modern API, suppresses the fitz deprecation warning
from typing import Callable, Optional


class PDFProcessingError(ValueError):
    """Raised when a PDF cannot be opened, parsed, or when OCR is required but unavailable."""


def process_pdf(
    pdf_input: bytes | str,
    lang: str = "eng",
    ocr_runner: Optional[Callable[[bytes, str], str]] = None,
) -> str:
    """Extract text from a PDF, falling back to OCR for scanned/image-only pages.

    For each page:
    - If extractable text is found (≥ 50 chars), it is used directly.
    - If a page has little/no text, it is rasterized and passed to the OCR runner.

    Args:
        pdf_input: PDF bytes or an absolute file path string.
        lang: BCP-47 language hint for the OCR engine (e.g. ``'eng'``).
        ocr_runner: Optional ``(image_bytes: bytes, lang: str) -> str`` callable.
            Defaults to ``ml.ocr.tesseract.extract_text_from_image``.

    Returns:
        str: Concatenated page text (native or OCR), pages separated by ``\\n\\n``.
             Returns ``""`` for a PDF with zero pages.

    Raises:
        PDFProcessingError: If the PDF cannot be opened, or if OCR is required
            but fails (e.g. Tesseract is not installed).
    """
    if ocr_runner is None:
        from ml.ocr.tesseract import extract_text_from_image
        ocr_runner = lambda img_bytes, l: extract_text_from_image(img_bytes, lang=l)

    # Open the PDF from bytes or path.
    try:
        if isinstance(pdf_input, bytes):
            doc = fitz.open(stream=pdf_input, filetype="pdf")
        else:
            doc = fitz.open(pdf_input)
    except Exception as exc:
        raise PDFProcessingError(f"Failed to open PDF: {exc}") from exc

    texts: list[str] = []

    try:
        if len(doc) == 0:
            return ""

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Attempt native text extraction first.
            native_text = page.get_text("text").strip()

            # If the page has substantial native text, use it directly.
            # Threshold of 50 chars guards against sparse header-only pages.
            if len(native_text) >= 50:
                texts.append(native_text)
                continue

            # Page has little/no native text → assume scanned; attempt OCR.
            pix = page.get_pixmap(dpi=300)   # 300 DPI gives Tesseract a readable image
            img_bytes = pix.tobytes("png")

            # OCR failures (engine missing, image corrupt, etc.) are propagated
            # so the caller gets a clear error instead of silently empty text.
            try:
                ocr_text = ocr_runner(img_bytes, lang)
            except Exception as exc:
                raise PDFProcessingError(
                    f"OCR failed on page {page_num + 1}: {exc}"
                ) from exc

            ocr_text = (ocr_text or "").strip()
            if ocr_text:
                texts.append(ocr_text)
            # If OCR returns empty string for this page, skip it silently —
            # an empty scanned page is a valid case (e.g. blank separator page).

    finally:
        doc.close()

    return "\n\n".join(texts)
