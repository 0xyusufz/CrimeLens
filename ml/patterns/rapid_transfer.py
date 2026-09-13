"""Rapid transfer chain detection (Foundation stub).

Detects rapid pass-through or layering transfer chains.
Status semantics: INFERRED or PREDICTED (never DETECTED).
"""

from typing import Any

from shared.schemas.models import Pattern


def detect_rapid_transfers(records: list[dict[str, Any]]) -> list[Pattern]:
    """Detect rapid consecutive transfer chains.

    To be implemented in future pattern detection phase.
    """
    return []
