"""Text normalization and sanitization interface (Foundation stub)."""


def normalize_text(text: str) -> str:
    """Normalize whitespace and strip unneeded trailing characters.

    To be expanded in future preprocessing phase.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return " ".join(text.split())
