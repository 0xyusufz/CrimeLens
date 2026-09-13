"""Document loading interface for file and text inputs (Foundation stub)."""


def load_document(content_or_path: str) -> str:
    """Load and return raw document text for ingestion.

    To be expanded in future preprocessing phase.
    """
    if not isinstance(content_or_path, str):
        raise TypeError("content_or_path must be a string")
    return content_or_path
