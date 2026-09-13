"""Spatio-temporal co-location detection for CrimeLens.

Detects co-presence of distinct suspect entities within 2 hours at the same location.
Requirements:
- Reliable, normalized location information
- Reliable, valid timestamps
- Temporal difference abs(time_1 - time_2) <= 2 hours (boundary: exactly 2h qualifies, >2h does not)
- Distinct entities (Entity A != Entity B)
- Insufficient data (missing location or timestamp) strictly suppresses pattern generation.

Status semantics: INFERRED (never DETECTED, never coerced to CONFIRMED).
Does NOT perform database persistence, canonical UUID minting, or criminal prediction.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from ml.resolution.resolver import normalize_location
from ml.structured import CDRRecord, TransactionRecord, parse_cdr, parse_transaction
from shared.schemas.enums import PatternType, RelationshipStatus, Severity
from shared.schemas.models import Pattern

# 2-hour fixed MVP demo threshold in seconds (2 hours * 3600 seconds)
LOCATION_TIME_WINDOW_SECONDS: float = 2 * 3600.0


def _to_utc_naive(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for safe comparison."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@dataclass(frozen=True)
class _EventPoint:
    entity: str
    location: str
    normalized_location: str
    timestamp: datetime
    record_id: str


def _extract_event_points(records: list[Any]) -> list[_EventPoint]:
    """Extract validated event points with location, timestamp, and entity from structured records."""
    points: list[_EventPoint] = []
    seen_points: set[tuple[str, str, str, datetime]] = set()

    for r in records:
        if not r:
            continue

        # Case A: CDRRecord
        if isinstance(r, CDRRecord):
            if r.location and str(r.location).strip() and r.call_datetime:
                norm_loc = normalize_location(str(r.location))
                if norm_loc:
                    dt = _to_utc_naive(r.call_datetime)
                    rec_id = r.record_id or f"cdr_{re.sub(r'\\W', '', r.caller)}_{re.sub(r'\\W', '', r.callee)}_{re.sub(r'\\W', '', r.call_time)}"
                    dedup_key = (rec_id, r.caller, norm_loc, dt)
                    if dedup_key not in seen_points:
                        seen_points.add(dedup_key)
                        points.append(
                            _EventPoint(
                                entity=r.caller,
                                location=str(r.location).strip(),
                                normalized_location=norm_loc,
                                timestamp=dt,
                                record_id=str(rec_id),
                            )
                        )
            continue

        # Case B: TransactionRecord
        if isinstance(r, TransactionRecord):
            if r.location and str(r.location).strip() and r.transaction_datetime:
                norm_loc = normalize_location(str(r.location))
                if norm_loc:
                    dt = _to_utc_naive(r.transaction_datetime)
                    rec_id = r.record_id or f"tx_{re.sub(r'\\W', '', r.sender)}_{re.sub(r'\\W', '', r.recipient)}_{re.sub(r'\\W', '', r.transaction_time)}"
                    dedup_key = (rec_id, r.sender, norm_loc, dt)
                    if dedup_key not in seen_points:
                        seen_points.add(dedup_key)
                        points.append(
                            _EventPoint(
                                entity=r.sender,
                                location=str(r.location).strip(),
                                normalized_location=norm_loc,
                                timestamp=dt,
                                record_id=str(rec_id),
                            )
                        )
            continue

        # Case C: Dictionary
        if isinstance(r, dict):
            # Try parsing as CDR if caller and callee present
            if "caller" in r and "callee" in r:
                try:
                    cdr = parse_cdr(r)
                    if cdr.location and str(cdr.location).strip():
                        norm_loc = normalize_location(str(cdr.location))
                        if norm_loc:
                            dt = _to_utc_naive(cdr.call_datetime)
                            rec_id = cdr.record_id or f"cdr_{re.sub(r'\\W', '', cdr.caller)}_{re.sub(r'\\W', '', cdr.callee)}_{re.sub(r'\\W', '', cdr.call_time)}"
                            dedup_key = (rec_id, cdr.caller, norm_loc, dt)
                            if dedup_key not in seen_points:
                                seen_points.add(dedup_key)
                                points.append(
                                    _EventPoint(
                                        entity=cdr.caller,
                                        location=str(cdr.location).strip(),
                                        normalized_location=norm_loc,
                                        timestamp=dt,
                                        record_id=str(rec_id),
                                    )
                                )
                    continue
                except Exception:
                    pass

            # Try parsing as Transaction if sender and recipient present
            if "sender" in r and "recipient" in r:
                try:
                    tx = parse_transaction(r)
                    if tx.location and str(tx.location).strip():
                        norm_loc = normalize_location(str(tx.location))
                        if norm_loc:
                            dt = _to_utc_naive(tx.transaction_datetime)
                            rec_id = tx.record_id or f"tx_{re.sub(r'\\W', '', tx.sender)}_{re.sub(r'\\W', '', tx.recipient)}_{re.sub(r'\\W', '', tx.transaction_time)}"
                            dedup_key = (rec_id, tx.sender, norm_loc, dt)
                            if dedup_key not in seen_points:
                                seen_points.add(dedup_key)
                                points.append(
                                    _EventPoint(
                                        entity=tx.sender,
                                        location=str(tx.location).strip(),
                                        normalized_location=norm_loc,
                                        timestamp=dt,
                                        record_id=str(rec_id),
                                    )
                                )
                    continue
                except Exception:
                    pass

            # Generic event dict with entity, location, and timestamp
            entity = r.get("entity") or r.get("person") or r.get("name") or r.get("caller") or r.get("sender")
            loc = r.get("location") or r.get("place") or r.get("city")
            time_val = r.get("timestamp") or r.get("time") or r.get("call_time") or r.get("transaction_time")

            if not entity or not str(entity).strip():
                continue
            if not loc or not str(loc).strip():
                continue
            if not time_val:
                continue

            # Parse timestamp safely
            if isinstance(time_val, datetime):
                dt = _to_utc_naive(time_val)
            else:
                try:
                    dt = _to_utc_naive(datetime.fromisoformat(str(time_val).strip()))
                except ValueError:
                    continue

            norm_loc = normalize_location(str(loc))
            if not norm_loc:
                continue

            entity_str = str(entity).strip()
            loc_str = str(loc).strip()
            clean_ent = re.sub(r"\W", "_", entity_str)
            clean_time = re.sub(r"\W", "", dt.isoformat())
            rec_id = str(r.get("record_id") or r.get("id") or f"ev_{clean_ent}_{norm_loc}_{clean_time}")

            dedup_key = (rec_id, entity_str, norm_loc, dt)
            if dedup_key not in seen_points:
                seen_points.add(dedup_key)
                points.append(
                    _EventPoint(
                        entity=entity_str,
                        location=loc_str,
                        normalized_location=norm_loc,
                        timestamp=dt,
                        record_id=rec_id,
                    )
                )

    return points


def detect_location_time_overlaps(records: list[dict[str, Any] | CDRRecord | TransactionRecord]) -> list[Pattern]:
    """Detect spatio-temporal co-presence across entity events within 2 hours at the same location.

    Args:
        records: List of structured event records, CDRRecords, or TransactionRecords.

    Returns:
        list[Pattern]: Validated Pattern instances with type LOCATION_TIME_OVERLAP.
    """
    if not records:
        return []

    points = _extract_event_points(records)
    if len(points) < 2:
        return []

    # Sort deterministically
    points.sort(key=lambda p: (p.timestamp, p.normalized_location, p.entity, p.record_id))

    patterns: list[Pattern] = []
    seen_overlaps: set[tuple[str, str, str, tuple[str, ...]]] = set()
    pattern_counter = 1

    n = len(points)
    for i in range(n):
        for j in range(i + 1, n):
            p1 = points[i]
            p2 = points[j]

            # 1. Location match: same normalized location
            if p1.normalized_location != p2.normalized_location:
                continue

            # 2. Distinct entities: Entity A != Entity B
            if p1.entity.strip().lower() == p2.entity.strip().lower():
                continue

            # 3. Distinct record check
            if p1.record_id == p2.record_id:
                continue

            # 4. Temporal difference check: abs(time_1 - time_2) <= 2 hours
            delta_seconds = abs((p1.timestamp - p2.timestamp).total_seconds())
            if delta_seconds <= LOCATION_TIME_WINDOW_SECONDS:
                ev_ids = sorted([str(p1.record_id), str(p2.record_id)])
                entities = sorted([p1.entity, p2.entity])

                dedup_key = (entities[0], entities[1], p1.normalized_location, tuple(ev_ids))
                if dedup_key in seen_overlaps:
                    continue
                seen_overlaps.add(dedup_key)

                minutes = delta_seconds / 60.0
                explanation = (
                    f"Location-time overlap detected at {p1.location} between {entities[0]} and {entities[1]} "
                    f"within {minutes:.0f} minutes (max allowed: 2 hours)."
                )

                patterns.append(
                    Pattern(
                        id=f"pattern_{pattern_counter:03d}",
                        type=PatternType.LOCATION_TIME_OVERLAP,
                        severity=Severity.MEDIUM,
                        status=RelationshipStatus.INFERRED,
                        entities=entities,
                        explanation=explanation,
                        evidence_ids=ev_ids,
                    )
                )
                pattern_counter += 1

    return patterns

