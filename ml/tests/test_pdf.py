"""Tests for ml/preprocessing/pdf_handler.py.

Covers:
- Native text PDF (OCR must NOT be called)
- Scanned PDF with mocked OCR (OCR must be called, result returned)
- Scanned PDF with OCR unavailable (PDFProcessingError must be raised, not silent empty)
- Multi-page PDF with mixed native + scanned pages
- Empty PDF (zero pages → empty string)
- Invalid PDF bytes → PDFProcessingError
"""

import pymupdf as fitz
import pytest
from unittest.mock import MagicMock

from ml.preprocessing.pdf_handler import process_pdf, PDFProcessingError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LONG_NATIVE = (
    "Hello, this is native PDF text. It is long enough to bypass OCR. "
    "Yes it is very long indeed, more than 50 characters."
)


def _make_pdf_bytes(*page_texts: str) -> bytes:
    """Create a minimal in-memory PDF with the given text layers per page."""
    doc = fitz.open()
    for txt in page_texts:
        page = doc.new_page()
        if txt:
            page.insert_text((50, 50), txt)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def _make_scanned_pdf_bytes(n_pages: int = 1) -> bytes:
    """Create a PDF with n blank (image-only, no text layer) pages."""
    doc = fitz.open()
    for _ in range(n_pages):
        doc.new_page()
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Native-text tests
# ---------------------------------------------------------------------------

def test_native_text_from_path(tmp_path):
    """Native text PDF: result contains text, OCR is never called."""
    pdf_path = tmp_path / "native.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), _LONG_NATIVE)
    doc.save(str(pdf_path))
    doc.close()

    mock_ocr = MagicMock()
    result = process_pdf(str(pdf_path), ocr_runner=mock_ocr)

    assert "Hello, this is native PDF text" in result
    mock_ocr.assert_not_called()


def test_native_text_from_bytes():
    """Native text PDF supplied as bytes: same behaviour."""
    pdf_bytes = _make_pdf_bytes(_LONG_NATIVE)

    mock_ocr = MagicMock()
    result = process_pdf(pdf_bytes, ocr_runner=mock_ocr)

    assert "Hello, this is native PDF text" in result
    mock_ocr.assert_not_called()


# ---------------------------------------------------------------------------
# Scanned-page tests (mocked OCR)
# ---------------------------------------------------------------------------

def test_scanned_page_invokes_ocr(tmp_path):
    """A blank/scanned page triggers the OCR runner exactly once."""
    pdf_path = tmp_path / "scanned.pdf"
    doc = fitz.open()
    doc.new_page()          # blank → no text layer
    doc.save(str(pdf_path))
    doc.close()

    mock_ocr = MagicMock(return_value="OCR extracted text")
    result = process_pdf(str(pdf_path), ocr_runner=mock_ocr)

    assert "OCR extracted text" in result
    mock_ocr.assert_called_once()


def test_scanned_pdf_bytes_invokes_ocr():
    """Scanned PDF supplied as bytes also triggers OCR."""
    pdf_bytes = _make_scanned_pdf_bytes(1)

    mock_ocr = MagicMock(return_value="OCR from bytes")
    result = process_pdf(pdf_bytes, ocr_runner=mock_ocr)

    assert "OCR from bytes" in result
    mock_ocr.assert_called_once()


# ---------------------------------------------------------------------------
# OCR unavailable / failure propagation (the robustness fix)
# ---------------------------------------------------------------------------

def test_scanned_pdf_ocr_unavailable_raises():
    """Scanned PDF with no Tesseract: PDFProcessingError must be raised.

    This is the key regression test for the original bug.
    Previously the exception was silently swallowed and near-empty text was
    returned, causing a false HTTP 200 with zero extraction results.
    After the fix, the caller receives a clear PDFProcessingError instead.
    """
    pdf_bytes = _make_scanned_pdf_bytes(1)

    def failing_ocr(img_bytes, lang):
        raise RuntimeError("Tesseract OCR engine is not installed.")

    with pytest.raises(PDFProcessingError, match="OCR failed"):
        process_pdf(pdf_bytes, ocr_runner=failing_ocr)


def test_scanned_pdf_ocr_failure_contains_page_number():
    """The PDFProcessingError message identifies the failing page number."""
    pdf_bytes = _make_scanned_pdf_bytes(2)

    call_count = 0

    def failing_ocr_on_second_page(img_bytes, lang):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Tesseract failed.")
        return "First page OCR text here, long enough to matter really."

    # Page 1 returns native-length text via OCR (>= 0 chars, so appended)
    # Page 2 raises → PDFProcessingError for page 2
    with pytest.raises(PDFProcessingError, match="page 2"):
        process_pdf(pdf_bytes, ocr_runner=failing_ocr_on_second_page)


# ---------------------------------------------------------------------------
# Multi-page / mixed tests
# ---------------------------------------------------------------------------

def test_mixed_pages_native_then_scanned():
    """Page 1 native text, page 2 scanned: both processed; OCR called once."""
    pdf_bytes = _make_pdf_bytes(_LONG_NATIVE, "")   # page 2 = blank

    mock_ocr = MagicMock(return_value="Page 2 OCR output.")
    result = process_pdf(pdf_bytes, ocr_runner=mock_ocr)

    assert "Hello, this is native PDF text" in result
    assert "Page 2 OCR output." in result
    mock_ocr.assert_called_once()


def test_mixed_pages_page_order_preserved():
    """Text from earlier pages appears before text from later pages."""
    pdf_bytes = _make_pdf_bytes(_LONG_NATIVE, "")

    mock_ocr = MagicMock(return_value="Second page OCR.")
    result = process_pdf(pdf_bytes, ocr_runner=mock_ocr)

    pos_native = result.index("Hello")
    pos_ocr = result.index("Second page OCR")
    assert pos_native < pos_ocr, "Native text from page 1 must precede OCR text from page 2"


def test_multi_scanned_pages_ocr_called_per_page():
    """Every scanned page triggers the OCR runner independently."""
    pdf_bytes = _make_scanned_pdf_bytes(3)

    mock_ocr = MagicMock(return_value="OCR text.")
    process_pdf(pdf_bytes, ocr_runner=mock_ocr)

    assert mock_ocr.call_count == 3


# ---------------------------------------------------------------------------
# Edge / error cases
# ---------------------------------------------------------------------------

def test_empty_pdf_returns_empty_string():
    """A PDF with zero pages returns empty string without error."""
    # Manually crafted minimal zero-page PDF (PyMuPDF refuses to .write() one)
    zero_page_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n119\n%%EOF"
    )
    result = process_pdf(zero_page_pdf)
    assert result == ""


def test_invalid_pdf_bytes_raises_pdf_processing_error():
    """Non-PDF bytes raise PDFProcessingError (not an unhandled exception)."""
    with pytest.raises(PDFProcessingError):
        process_pdf(b"Not a PDF at all")
