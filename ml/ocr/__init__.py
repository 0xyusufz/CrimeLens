"""OCR interfaces and execution subpackage."""

from ml.ocr.tesseract import (
    InvalidImageError,
    OCREngineUnavailableError,
    OCRError,
    OCRProcessingError,
    OCRResult,
    UnsupportedImageFormatError,
    extract_ocr_result,
    extract_text_from_image,
    is_ocr_available,
    run_tesseract,
)

__all__ = [
    "InvalidImageError",
    "OCREngineUnavailableError",
    "OCRError",
    "OCRProcessingError",
    "OCRResult",
    "UnsupportedImageFormatError",
    "extract_ocr_result",
    "extract_text_from_image",
    "is_ocr_available",
    "run_tesseract",
]
