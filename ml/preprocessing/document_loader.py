"""Document loading interface for file and text inputs.

Handles raw text strings and file loading.
Distinguishes between plain text content and scanned/image documents that will
require OCR in Phase 3.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCANNED_FILE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".bmp",
    ".pdf",
}


@dataclass(frozen=True)
class DocumentSource:
    """Metadata container for loaded document content."""

    content: str
    is_file: bool = False
    file_path: Optional[str] = None
    needs_ocr: bool = False


def is_scanned_file(path_str: str) -> bool:
    """Check whether a file path points to an image/scanned document requiring OCR."""
    return Path(path_str).suffix.lower() in SCANNED_FILE_EXTENSIONS


def load_document(content_or_path: str) -> str:
    """Load and return raw document text for pipeline ingestion.

    Args:
        content_or_path: Raw text string or a path to a plain text file.

    Returns:
        str: Raw text content.

    Raises:
        TypeError: If input is not a string.
        ValueError: If file is a scanned image/PDF requiring OCR (Phase 3).
        FileNotFoundError: If a file path is explicitly detected but does not exist.
    """
    if not isinstance(content_or_path, str):
        raise TypeError("content_or_path must be a string")

    # If empty or whitespace-only, return as-is for normalizer handling
    if not content_or_path.strip():
        return content_or_path

    # Check if content_or_path looks like a filesystem path with a known extension
    potential_path = Path(content_or_path)
    if potential_path.suffix:
        if potential_path.suffix.lower() in SCANNED_FILE_EXTENSIONS:
            raise ValueError(
                f"Document '{content_or_path}' is an image/scanned document. "
                "OCR processing belongs to Phase 3."
            )
        if potential_path.exists() and potential_path.is_file():
            try:
                return potential_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return potential_path.read_text(encoding="latin-1")

    # Otherwise, content_or_path is treated directly as the document text
    return content_or_path
