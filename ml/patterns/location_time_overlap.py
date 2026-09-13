"""Spatio-temporal co-location detection (Foundation stub).

Detects co-presence of suspect entities within time and location windows.
Status semantics: INFERRED or PREDICTED (never DETECTED).
"""

from typing import Any

from shared.schemas.models import Pattern


def detect_location_time_overlaps(records: list[dict[str, Any]]) -> list[Pattern]:
    """Detect location-time overlaps across entity events.

    To be implemented in future pattern detection phase.
    """
    return []
