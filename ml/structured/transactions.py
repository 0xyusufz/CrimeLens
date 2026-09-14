"""Structured financial transaction handler for CrimeLens.

Validates and normalizes financial transaction records.
Preserves sender, recipient, amount, currency, transaction_time, and location metadata.
Does NOT perform currency conversion, financial risk scoring, or pattern detection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Optional

from ml.resolution.resolver import normalize_account
from shared.schemas.enums import RelationshipStatus, RelationshipType
from shared.schemas.models import Relationship


@dataclass(frozen=True)
class TransactionRecord:
    """Internal validated representation of a financial transaction."""

    sender: str
    recipient: str
    amount: float
    currency: str
    transaction_time: str
    transaction_datetime: datetime
    location: Optional[str] = None
    record_id: Optional[str] = None
    raw_data: Optional[dict[str, Any]] = None

    @property
    def normalized_sender(self) -> str:
        return normalize_account(self.sender)

    @property
    def normalized_recipient(self) -> str:
        return normalize_account(self.recipient)


def parse_transaction(data: dict[str, Any] | TransactionRecord) -> TransactionRecord:
    """Validate and normalize a structured transaction record.

    Args:
        data: Dictionary containing transaction fields or an existing TransactionRecord.

    Returns:
        TransactionRecord: Validated and normalized transaction data structure.

    Raises:
        ValueError: If required fields are missing, invalid, or sender == recipient.
    """
    if isinstance(data, TransactionRecord):
        return data

    if not isinstance(data, dict):
        raise ValueError(f"Transaction record must be a dictionary, got {type(data).__name__}")

    # 1. Sender validation
    sender = data.get("sender")
    if sender is None or not str(sender).strip():
        raise ValueError("Transaction record missing required 'sender' field")
    sender_str = str(sender).strip()

    # 2. Recipient validation
    recipient = data.get("recipient")
    if recipient is None or not str(recipient).strip():
        raise ValueError("Transaction record missing required 'recipient' field")
    recipient_str = str(recipient).strip()

    # 3. Same sender and recipient check
    norm_sender = normalize_account(sender_str)
    norm_recip = normalize_account(recipient_str)
    if norm_sender and norm_recip and norm_sender == norm_recip:
        raise ValueError("Transaction sender and recipient cannot be the same entity")

    # 4. Amount validation
    amount_val = data.get("amount")
    if amount_val is None:
        raise ValueError("Transaction record missing required 'amount' field")

    try:
        amount_num = float(amount_val)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid transaction amount '{amount_val}': must be numeric") from e

    if amount_num <= 0:
        raise ValueError(f"Invalid transaction amount '{amount_val}': must be greater than zero")

    # 5. Currency validation
    currency_val = data.get("currency")
    if currency_val is None or not str(currency_val).strip():
        raise ValueError("Transaction record missing required 'currency' field")

    currency_str = str(currency_val).strip().upper()
    if not re.match(r"^[A-Z]{3}$", currency_str):
        raise ValueError(f"Invalid currency '{currency_val}': must be a valid 3-letter ISO code")

    # 6. Transaction time validation
    tx_time = data.get("transaction_time") or data.get("time") or data.get("timestamp")
    if tx_time is None or not str(tx_time).strip():
        raise ValueError("Transaction record missing required 'transaction_time' field")

    if isinstance(tx_time, datetime):
        tx_dt = tx_time
        time_str = tx_time.isoformat()
    else:
        time_str = str(tx_time).strip()
        try:
            tx_dt = datetime.fromisoformat(time_str)
        except ValueError as e:
            raise ValueError(f"Invalid transaction_time format '{time_str}': must be ISO 8601") from e

    location = str(data["location"]).strip() if data.get("location") else None
    record_id = str(data["record_id"]).strip() if data.get("record_id") else str(data.get("id") or "") or None

    return TransactionRecord(
        sender=sender_str,
        recipient=recipient_str,
        amount=amount_num,
        currency=currency_str,
        transaction_time=time_str,
        transaction_datetime=tx_dt,
        location=location,
        record_id=record_id,
        raw_data=dict(data),
    )


def parse_transactions(records: list[dict[str, Any] | TransactionRecord]) -> list[TransactionRecord]:
    """Parse and validate a list of transaction records."""
    return [parse_transaction(r) for r in records]


def transaction_to_relationship(
    tx: TransactionRecord | dict[str, Any],
    document_id: str,
    source_entity_id: str,
    target_entity_id: str,
    rel_id: str = "rel_001",
) -> Relationship:
    """Convert a validated TransactionRecord into a Phase 5 Relationship object.

    Enforces sender -> SENT_MONEY_TO -> recipient direction.
    """
    rec = parse_transaction(tx)
    snippet = f"Transaction {rec.record_id or 'log'}: {rec.sender} sent {rec.currency} {rec.amount} to {rec.recipient} at {rec.transaction_time}"

    # Determine extracted_at preserving timezone if present or defaulting to UTC
    extracted_at = rec.transaction_datetime if rec.transaction_datetime.tzinfo else rec.transaction_datetime.replace(tzinfo=timezone.utc)

    return Relationship(
        id=rel_id,
        source_entity_id=source_entity_id,
        relationship=RelationshipType.SENT_MONEY_TO,
        target_entity_id=target_entity_id,
        confidence=0.98,
        status=RelationshipStatus.CONFIRMED,
        source_document_id=document_id,
        source_record_id=rec.record_id,
        evidence_snippet=snippet,
        extracted_at=extracted_at,
    )
