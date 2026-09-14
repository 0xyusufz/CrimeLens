"""Rapid transfer chain detection for CrimeLens.

Detects directed 3-node fund transfer chains (A → B → C) completed within 48 hours where:
- A, B, and C are distinct nodes
- Direction is strictly forward: B receives from A, then B sends to C
- transaction_1.time <= transaction_2.time
- delta <= 48 hours (boundary: exactly 48 hours qualifies, > 48 hours does not)
- Distinct transaction occurrences (no reuse of same transaction)

Status semantics: INFERRED (never DETECTED, never coerced to CONFIRMED).
Does NOT perform database persistence, canonical UUID minting, or criminal prediction.
"""

from collections import defaultdict
from datetime import datetime, timezone
import re
from typing import Any

from ml.structured import TransactionRecord, parse_transaction
from shared.schemas.enums import PatternType, RelationshipStatus, Severity
from shared.schemas.models import Pattern

# 48-hour fixed MVP demo threshold in seconds (48 hours * 3600 seconds)
RAPID_TRANSFER_WINDOW_SECONDS: float = 48 * 3600.0


def _to_utc_naive(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for safe comparison."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _deterministic_tx_id(tx: TransactionRecord) -> str:
    """Create a stable deterministic identifier based on structured fields when record_id is absent."""
    if tx.record_id and str(tx.record_id).strip():
        return str(tx.record_id).strip()
    clean_sender = re.sub(r"\W", "_", tx.sender.strip())
    clean_recipient = re.sub(r"\W", "_", tx.recipient.strip())
    clean_time = re.sub(r"\W", "", tx.transaction_time.strip())
    return f"tx_{clean_sender}_{clean_recipient}_{clean_time}"


def detect_rapid_transfers(records: list[dict[str, Any] | TransactionRecord]) -> list[Pattern]:
    """Detect rapid consecutive transfer chains in financial records.

    Args:
        records: List of TransactionRecord instances or raw transaction dictionaries.

    Returns:
        list[Pattern]: Validated Pattern instances with type RAPID_TRANSFER_CHAIN.
    """
    if not records:
        return []

    # 1. Parse and validate records into TransactionRecord objects
    parsed_txs: list[TransactionRecord] = []
    seen_records: set[tuple[Any, ...]] = set()

    for r in records:
        try:
            tx = parse_transaction(r)
            tx_id = _deterministic_tx_id(tx)
            normalized_dt = _to_utc_naive(tx.transaction_datetime)

            # Deduplicate identical transaction records deterministically
            dedup_tx_key = (tx_id, tx.sender, tx.recipient, tx.amount, tx.currency, normalized_dt)
            if dedup_tx_key in seen_records:
                continue
            seen_records.add(dedup_tx_key)

            parsed_txs.append(
                TransactionRecord(
                    sender=tx.sender,
                    recipient=tx.recipient,
                    amount=tx.amount,
                    currency=tx.currency,
                    transaction_time=tx.transaction_time,
                    transaction_datetime=normalized_dt,
                    location=tx.location,
                    record_id=tx_id,
                    raw_data=tx.raw_data,
                )
            )
        except Exception:
            continue

    if len(parsed_txs) < 2:
        return []

    # 2. Sort transactions deterministically
    parsed_txs.sort(key=lambda t: (t.transaction_datetime, t.record_id or "", t.sender, t.recipient))

    # 3. Index transactions by sender for fast forward matching
    by_sender: dict[str, list[TransactionRecord]] = defaultdict(list)
    for t in parsed_txs:
        by_sender[t.sender].append(t)

    patterns: list[Pattern] = []
    seen_chains: set[tuple[str, str, str, str, str]] = set()
    pattern_counter = 1

    # 4. Forward 3-node chain search: tx1 (A → B), tx2 (B → C)
    for tx1 in parsed_txs:
        a = tx1.sender
        b = tx1.recipient
        if a == b:
            continue

        for tx2 in by_sender.get(b, []):
            c = tx2.recipient
            # Distinct 3-node check: A != B, B != C, A != C
            if c == a or c == b:
                continue

            # Distinct transaction check: do not reuse the same transaction record as both edges
            if tx1.record_id and tx2.record_id and tx1.record_id == tx2.record_id:
                continue

            # Time ordering check: tx1 must occur at or before tx2
            if tx1.transaction_datetime > tx2.transaction_datetime:
                continue

            delta_seconds = (tx2.transaction_datetime - tx1.transaction_datetime).total_seconds()

            # Time window check: 0 <= delta <= 48 hours
            if 0.0 <= delta_seconds <= RAPID_TRANSFER_WINDOW_SECONDS:
                ev_ids = [str(tx1.record_id), str(tx2.record_id)]
                dedup_key = (a, b, c, str(tx1.record_id), str(tx2.record_id))
                if dedup_key in seen_chains:
                    continue
                seen_chains.add(dedup_key)

                hours_span = delta_seconds / 3600.0
                explanation = (
                    f"Rapid fund transfer chain detected: {a} → {b} → {c} "
                    f"completed in {hours_span:.1f} hours (max allowed: 48 hours)."
                )

                patterns.append(
                    Pattern(
                        id=f"pattern_{pattern_counter:03d}",
                        type=PatternType.RAPID_TRANSFER_CHAIN,
                        severity=Severity.HIGH,
                        status=RelationshipStatus.INFERRED,
                        entities=[a, b, c],
                        explanation=explanation,
                        evidence_ids=ev_ids,
                    )
                )
                pattern_counter += 1

    return patterns


# Alias for explicit naming consistency
detect_rapid_transfer_chains = detect_rapid_transfers

