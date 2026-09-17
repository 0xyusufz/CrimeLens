"""Tesseract OCR wrapper interface and execution module.

Responsible for:
- Validating image bytes/files (PNG, JPEG, TIFF, BMP)
- Executing Tesseract CLI when available
- Providing structured OCRResult metadata
- Providing clear, informative errors when the engine is unavailable or images are invalid
- Feeding extracted raw text into the Phase 2 normalizer

Does NOT perform entity extraction, relationship extraction, resolution, or DB operations.
"""

import os
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# Supported image extensions for OCR
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".tif",
    ".bmp",
    ".gif",
}

# Image magic bytes signatures for validation
IMAGE_MAGIC_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"BM", "BMP"),
    (b"II*\x00", "TIFF"),
    (b"MM\x00*", "TIFF"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
]


class OCRError(Exception):
    """Base exception for all OCR errors."""


class OCREngineUnavailableError(OCRError, RuntimeError):
    """Raised when Tesseract or the configured OCR engine is not available."""


class OCRProcessingError(OCRError, RuntimeError):
    """Raised when the OCR engine encounters an execution error."""


class InvalidImageError(OCRError, ValueError):
    """Raised when image bytes or image file is corrupt or invalid."""


class UnsupportedImageFormatError(OCRError, ValueError):
    """Raised when an image format is unsupported."""


@dataclass(frozen=True)
class OCRResult:
    """Internal container for OCR text extraction result."""

    raw_text: str
    engine: str = "tesseract"
    language: str = "eng"
    is_empty: bool = False


def is_ocr_available() -> bool:
    """Check if the Tesseract binary is available in PATH or common install paths."""
    if shutil.which("tesseract"):
        return True
    common_win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    return any(os.path.isfile(p) for p in common_win_paths)


def validate_image_bytes(data: bytes) -> str:
    """Validate image bytes against known magic headers.

    Returns the detected format name or raises InvalidImageError.
    """
    if not isinstance(data, bytes) or len(data) < 2:
        raise InvalidImageError("Image data must be non-empty bytes.")

    for signature, fmt in IMAGE_MAGIC_SIGNATURES:
        if data.startswith(signature):
            return fmt

    raise InvalidImageError("Invalid or corrupted image format: unrecognized magic bytes header.")


def run_tesseract(image_bytes: bytes, lang: str = "eng") -> str:
    """Execute the local Tesseract CLI on image bytes.

    Args:
        image_bytes: Raw binary content of the image.
        lang: Tesseract language code (e.g. 'eng').

    Returns:
        str: Raw text output from Tesseract.

    Raises:
        OCREngineUnavailableError: If Tesseract executable is not found.
        OCRProcessingError: If Tesseract returns a non-zero exit code.
    """
    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        common_win_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in common_win_paths:
            if os.path.isfile(candidate):
                tesseract_cmd = candidate
                break

    if not tesseract_cmd:
        raise OCREngineUnavailableError(
            "Tesseract OCR engine is not installed or not found in system PATH. "
            "Please install Tesseract-OCR to enable image text extraction."
        )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_file.write(_preprocess_image(image_bytes))
        tmp_path = tmp_file.name

    try:
        proc = subprocess.run(
            [tesseract_cmd, tmp_path, "stdout", "-l", lang],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            raise OCRProcessingError(
                f"Tesseract OCR failed with return code {proc.returncode}: {proc.stderr.strip()}"
            )
        return proc.stdout
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _preprocess_image(image_bytes: bytes) -> bytes:
    """Improve common photographed/scanned pages without making OCR mandatory."""
    try:
        from PIL import Image, ImageFilter, ImageOps

        image = Image.open(io.BytesIO(image_bytes)).convert("L")
        image = ImageOps.exif_transpose(image)
        image = ImageOps.autocontrast(image)
        if image.width < 1600:
            scale = 1600 / max(image.width, 1)
            image = image.resize((1600, max(1, int(image.height * scale))))
        image = image.filter(ImageFilter.MedianFilter(size=3))
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True)
        return output.getvalue()
    except Exception:
        # Pillow is an enhancement, not a hard runtime requirement.
        return image_bytes


def extract_ocr_result(
    image_input: bytes | str | Path,
    lang: str = "eng",
    engine_runner: Optional[Callable[[bytes, str], str]] = None,
) -> OCRResult:
    """Extract text from an image, returning an OCRResult container.

    Args:
        image_input: Image bytes, or path (str / Path) to an image file.
        lang: Language string for OCR.
        engine_runner: Optional runner function (image_bytes, lang) -> str for testing/mocking.

    Returns:
        OCRResult: Extracted text and metadata.
    """
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_input}")
        if not path.is_file():
            raise FileNotFoundError(f"Path is not a regular file: {image_input}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            raise NotImplementedError(
                "PDF OCR rasterization will be supported when page rendering is configured; "
                "provide image files (PNG, JPG, TIFF, BMP) directly."
            )
        if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            raise UnsupportedImageFormatError(
                f"Unsupported image file extension '{suffix}'. Supported: {sorted(SUPPORTED_IMAGE_EXTENSIONS)}"
            )

        image_bytes = path.read_bytes()
    elif isinstance(image_input, bytes):
        image_bytes = image_input
    else:
        raise TypeError("image_input must be bytes or a file path (str/Path).")

    # Validate image bytes
    validate_image_bytes(image_bytes)

    # Run OCR engine
    runner = engine_runner or run_tesseract
    raw_text = runner(image_bytes, lang)

    return OCRResult(
        raw_text=raw_text,
        engine="tesseract",
        language=lang,
        is_empty=not (raw_text and raw_text.strip()),
    )


def extract_text_from_image(
    image_input: bytes | str | Path,
    lang: str = "eng",
    engine_runner: Optional[Callable[[bytes, str], str]] = None,
) -> str:
    """Convenience entry point returning the raw extracted text string from an image."""
    result = extract_ocr_result(image_input, lang=lang, engine_runner=engine_runner)
    return result.raw_text
