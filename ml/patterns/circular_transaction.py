"""Circular transaction detection for CrimeLens.

Detects directed 3-node transaction cycles (A → B → C → A) where:
- A, B, and C are distinct nodes
- Direction is strictly preserved
- Complete cycle occurs within 30 days (earliest to latest transaction <= 30 days)

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

# 30-day fixed MVP demo threshold in seconds (30 days * 24 hours * 3600 seconds)
CIRCULAR_WINDOW_SECONDS: float = 30 * 24 * 3600.0


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


def detect_circular_transactions(records: list[dict[str, Any] | TransactionRecord]) -> list[Pattern]:
    """Detect 3-node circular transactions in financial records within 30 days.

    Args:
        records: List of TransactionRecord instances or raw transaction dictionaries.

    Returns:
        list[Pattern]: Validated Pattern instances with type CIRCULAR_TRANSACTION.
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
            # Safely ignore unusable, invalid, or malformed records
            continue

    if len(parsed_txs) < 3:
        return []

    # 2. Sort transactions deterministically
    parsed_txs.sort(key=lambda t: (t.transaction_datetime, t.record_id or "", t.sender, t.recipient))

    # 3. Index transactions by sender for fast directed traversal
    by_sender: dict[str, list[TransactionRecord]] = defaultdict(list)
    for t in parsed_txs:
        by_sender[t.sender].append(t)

    patterns: list[Pattern] = []
    seen_cycles: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    pattern_counter = 1

    # 4. Directed 3-node cycle search: tx1 (A → B), tx2 (B → C), tx3 (C → A)
    for tx1 in parsed_txs:
        a = tx1.sender
        b = tx1.recipient
        if a == b:
            continue

        for tx2 in by_sender.get(b, []):
            c = tx2.recipient
            # Distinct node checks: A, B, and C must all be distinct
            if c == a or c == b:
                continue
            # Distinct transaction check: do not reuse same transaction
            if tx1.record_id and tx2.record_id and tx1.record_id == tx2.record_id:
                continue

            for tx3 in by_sender.get(c, []):
                if tx3.recipient != a:
                    continue
                # Distinct transaction checks
                if tx3.record_id and (tx3.record_id == tx1.record_id or tx3.record_id == tx2.record_id):
                    continue

                # Time window evaluation: latest - earliest <= 30 days
                times = [tx1.transaction_datetime, tx2.transaction_datetime, tx3.transaction_datetime]
                min_time = min(times)
                max_time = max(times)
                delta_seconds = (max_time - min_time).total_seconds()

                if delta_seconds <= CIRCULAR_WINDOW_SECONDS:
                    # Canonical rotation to deduplicate cycle representations
                    cycle_nodes = [a, b, c]
                    min_node = min(cycle_nodes)
                    min_idx = cycle_nodes.index(min_node)
                    canon_nodes = tuple(cycle_nodes[min_idx:] + cycle_nodes[:min_idx])

                    ev_ids = sorted([str(tx1.record_id), str(tx2.record_id), str(tx3.record_id)])
                    dedup_key = (canon_nodes, tuple(ev_ids))
                    if dedup_key in seen_cycles:
                        continue
                    seen_cycles.add(dedup_key)

                    days_span = delta_seconds / 86400.0
                    a_canon, b_canon, c_canon = canon_nodes
                    explanation = (
                        f"Circular fund transfer detected: {a_canon} → {b_canon} → {c_canon} → {a_canon} "
                        f"completed in {days_span:.1f} days (max allowed: 30 days)."
                    )

                    patterns.append(
                        Pattern(
                            id=f"pattern_{pattern_counter:03d}",
                            type=PatternType.CIRCULAR_TRANSACTION,
                            severity=Severity.HIGH,
                            status=RelationshipStatus.INFERRED,
                            entities=list(canon_nodes),
                            explanation=explanation,
                            evidence_ids=ev_ids,
                        )
                    )
                    pattern_counter += 1

    return patterns
