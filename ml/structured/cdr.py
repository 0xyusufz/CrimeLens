"""Structured Call Detail Record (CDR) handler for CrimeLens.

Validates and normalizes CDR records into a consistent internal representation.
Preserves caller, callee, call_time, duration, and location/cell_id metadata.
Does NOT perform entity resolution, database persistence, or pattern detection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ml.resolution.resolver import normalize_phone
from shared.schemas.enums import RelationshipStatus, RelationshipType
from shared.schemas.models import Relationship


@dataclass(frozen=True)
class CDRRecord:
    """Internal validated representation of a Call Detail Record."""

    caller: str
    callee: str
    call_time: str
    call_datetime: datetime
    duration: Optional[int | float] = None
    location: Optional[str] = None
    cell_id: Optional[str] = None
    record_id: Optional[str] = None
    raw_data: Optional[dict[str, Any]] = None

    @property
    def normalized_caller(self) -> str:
        return normalize_phone(self.caller)

    @property
    def normalized_callee(self) -> str:
        return normalize_phone(self.callee)


def parse_cdr(data: dict[str, Any] | CDRRecord) -> CDRRecord:
    """Validate and normalize a structured CDR record.

    Args:
        data: Dictionary containing CDR fields or an existing CDRRecord.

    Returns:
        CDRRecord: Validated and normalized CDR data structure.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if isinstance(data, CDRRecord):
        return data

    if not isinstance(data, dict):
        raise ValueError(f"CDR record must be a dictionary, got {type(data).__name__}")

    # 1. Caller validation
    caller = data.get("caller")
    if caller is None or not str(caller).strip():
        raise ValueError("CDR record missing required 'caller' field")
    caller_str = str(caller).strip()

    # 2. Callee validation
    callee = data.get("callee")
    if callee is None or not str(callee).strip():
        raise ValueError("CDR record missing required 'callee' field")
    callee_str = str(callee).strip()

    # 3. Caller != Callee
    norm_caller = normalize_phone(caller_str)
    norm_callee = normalize_phone(callee_str)
    if norm_caller and norm_callee and norm_caller == norm_callee:
        raise ValueError("CDR caller and callee cannot be the same entity")

    # 4. Call time validation
    call_time = data.get("call_time") or data.get("time") or data.get("timestamp")
    if call_time is None or not str(call_time).strip():
        raise ValueError("CDR record missing required 'call_time' field")

    if isinstance(call_time, datetime):
        call_dt = call_time
        time_str = call_time.isoformat()
    else:
        time_str = str(call_time).strip()
        try:
            call_dt = datetime.fromisoformat(time_str)
        except ValueError as e:
            raise ValueError(f"Invalid call_time format '{time_str}': must be ISO 8601") from e

    # 5. Duration validation
    duration_val = data.get("duration")
    duration: Optional[int | float] = None
    if duration_val is not None:
        try:
            duration_num = float(duration_val)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid duration '{duration_val}': must be numeric") from e

        if duration_num < 0:
            raise ValueError(f"Invalid duration '{duration_val}': cannot be negative")

        duration = int(duration_num) if duration_num.is_integer() else duration_num

    location = str(data["location"]).strip() if data.get("location") else None
    cell_id = str(data["cell_id"]).strip() if data.get("cell_id") else None
    record_id = str(data["record_id"]).strip() if data.get("record_id") else str(data.get("id") or "") or None

    return CDRRecord(
        caller=caller_str,
        callee=callee_str,
        call_time=time_str,
        call_datetime=call_dt,
        duration=duration,
        location=location,
        cell_id=cell_id,
        record_id=record_id,
        raw_data=dict(data),
    )


def parse_cdrs(records: list[dict[str, Any] | CDRRecord]) -> list[CDRRecord]:
    """Parse and validate a list of CDR records."""
    return [parse_cdr(r) for r in records]


def cdr_to_relationship(
    cdr: CDRRecord | dict[str, Any],
    document_id: str,
    source_entity_id: str,
    target_entity_id: str,
    rel_id: str = "rel_001",
) -> Relationship:
    """Convert a validated CDRRecord into a Phase 5 Relationship object.

    Enforces caller -> CALLED -> callee direction.
    """
    rec = parse_cdr(cdr)
    snippet = f"CDR {rec.record_id or 'log'}: {rec.caller} called {rec.callee} at {rec.call_time}"
    if rec.duration is not None:
        snippet += f" (duration: {rec.duration}s)"

    # Determine extracted_at preserving timezone if present or defaulting to UTC
    extracted_at = rec.call_datetime if rec.call_datetime.tzinfo else rec.call_datetime.replace(tzinfo=timezone.utc)

    return Relationship(
        id=rel_id,
        source_entity_id=source_entity_id,
        relationship=RelationshipType.CALLED,
        target_entity_id=target_entity_id,
        confidence=0.98,
        status=RelationshipStatus.CONFIRMED,
        source_document_id=document_id,
        source_record_id=rec.record_id,
        evidence_snippet=snippet,
        extracted_at=extracted_at,
    )
