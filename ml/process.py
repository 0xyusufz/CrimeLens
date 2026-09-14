"""CrimeLens ML - Process Document Alias (Person B).

Provides a direct import path for `ml.process.process_document` to support
Person A's adapter discovery candidates:
    _PERSON_B_CANDIDATES = (
        ("ml.process",   "process_document"),
        ("ml.pipeline",  "process_document"),
        ("ml.extract",   "process_document"),
    )
"""

from ml.pipeline import process_document

__all__ = ["process_document"]
