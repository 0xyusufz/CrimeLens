"""Circular transaction detection (Foundation stub).

Detects cycles in fund transfers (e.g., A -> B -> C -> A).
Status semantics: INFERRED or PREDICTED (never DETECTED, never coerced to CONFIRMED).
"""

from typing import Any

from shared.schemas.models import Pattern


def detect_circular_transactions(records: list[dict[str, Any]]) -> list[Pattern]:
    """Detect circular transactions in financial records.

    To be implemented in future pattern detection phase.
    """
    return []
