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
from ml.ocr.confidence import apply_ocr_confidence_to_entities, apply_ocr_confidence_to_relationships
from ml.ocr.layout_blocks import OCRBlock, extract_tesseract_blocks

__all__ = [
    "InvalidImageError",
    "OCREngineUnavailableError",
    "OCRError",
    "OCRProcessingError",
    "OCRResult",
    "UnsupportedImageFormatError",
    "OCRBlock",
    "apply_ocr_confidence_to_entities",
    "apply_ocr_confidence_to_relationships",
    "extract_tesseract_blocks",
    "extract_ocr_result",
    "extract_text_from_image",
    "is_ocr_available",
    "run_tesseract",
]
