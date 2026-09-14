"""CSV → StructuredRecord ingestion for CrimeLens backend.

This module belongs to Person A / backend. It never touches the ML tier.
ML receives structured data via the existing adapter (collect_person_b_intelligence).

Supported CSV shapes
--------------------
TRANSACTION
  Required columns: source (or sender), target (or recipient), amount, timestamp (or transaction_time)
  Optional columns: currency, record_id

CDR
  Required columns: caller (or entity), callee, timestamp (or call_time)
  Optional columns: duration, location, record_id

Detection is header-based. Unrecognised schemas are rejected with a clear error.
"""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import StructuredRecord
from app.models.enums import RecordType

# ── Public error types ────────────────────────────────────────────────────────


class CsvParseError(ValueError):
    """Raised when CSV content cannot be parsed into known StructuredRecord types."""


class EmptyCsvError(CsvParseError):
    """Raised when the CSV has no data rows (or is entirely empty)."""


class UnrecognisedCsvSchemaError(CsvParseError):
    """Raised when the CSV columns do not match any supported schema."""


class MissingRequiredColumnsError(CsvParseError):
    """Raised when identified schema is present but required columns are absent."""


# ── Column aliases ────────────────────────────────────────────────────────────

_TX_SOURCE_COLS = {"source", "sender"}
_TX_TARGET_COLS = {"target", "recipient"}
_TX_TIME_COLS = {"timestamp", "transaction_time", "time", "date"}
_TX_REQUIRED = (_TX_SOURCE_COLS, _TX_TARGET_COLS, _TX_TIME_COLS, {"amount"})

_CDR_CALLER_COLS = {"caller", "entity"}
_CDR_CALLEE_COLS = {"callee"}
_CDR_TIME_COLS = {"timestamp", "call_time", "time", "date"}
_CDR_REQUIRED = (_CDR_CALLER_COLS, _CDR_CALLEE_COLS, _CDR_TIME_COLS)


def _lower_headers(row: dict) -> dict[str, str]:
    return {k.strip().lower(): k for k in row.keys()}


def _pick(lower_headers: dict[str, str], candidates: set[str]) -> str | None:
    """Return the first matching canonical column name from the CSV headers."""
    for c in candidates:
        if c in lower_headers:
            return lower_headers[c]
    return None


# ── Schema detection ──────────────────────────────────────────────────────────


def _detect_schema(lower_headers: dict[str, str]) -> RecordType | None:
    """Return RecordType for the CSV or None if unrecognised.

    Transaction is detected when both source-like and target-like columns plus
    'amount' are present.
    CDR is detected when caller-like and callee-like columns are present.
    """
    has_tx_source = any(c in lower_headers for c in _TX_SOURCE_COLS)
    has_tx_target = any(c in lower_headers for c in _TX_TARGET_COLS)
    has_amount = "amount" in lower_headers
    if has_tx_source and has_tx_target and has_amount:
        return RecordType.TRANSACTION

    has_cdr_caller = any(c in lower_headers for c in _CDR_CALLER_COLS)
    has_cdr_callee = any(c in lower_headers for c in _CDR_CALLEE_COLS)
    if has_cdr_caller and has_cdr_callee:
        return RecordType.CDR

    return None


# ── Row normalisation ─────────────────────────────────────────────────────────


def _normalise_transaction(row: dict, lower_headers: dict[str, str]) -> dict[str, Any]:
    """Map a raw CSV row to the ML adapter's expected TRANSACTION dict.

    Required keys in output: sender, recipient, amount, transaction_time.
    Optional: currency, record_id.
    """
    def get(candidates: set[str]) -> str:
        col = _pick(lower_headers, candidates)
        return row.get(col, "").strip() if col else ""

    sender = get(_TX_SOURCE_COLS)
    recipient = get(_TX_TARGET_COLS)
    ts = get(_TX_TIME_COLS)
    raw_amount = get({"amount"})

    if not sender:
        raise MissingRequiredColumnsError("Transaction row missing sender/source value")
    if not recipient:
        raise MissingRequiredColumnsError("Transaction row missing recipient/target value")
    if not ts:
        raise MissingRequiredColumnsError("Transaction row missing timestamp/transaction_time value")
    try:
        amount = float(raw_amount)
    except (ValueError, TypeError):
        raise MissingRequiredColumnsError(f"Transaction row 'amount' is not numeric: {raw_amount!r}")

    result: dict[str, Any] = {
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "transaction_time": ts,
    }

    currency_col = _pick(lower_headers, {"currency"})
    if currency_col and row.get(currency_col, "").strip():
        result["currency"] = row[currency_col].strip()
    else:
        result["currency"] = "INR"

    record_id_col = _pick(lower_headers, {"record_id", "id", "txn_id", "transaction_id"})
    if record_id_col and row.get(record_id_col, "").strip():
        result["record_id"] = row[record_id_col].strip()

    return result


def _normalise_cdr(row: dict, lower_headers: dict[str, str]) -> dict[str, Any]:
    """Map a raw CSV row to the ML adapter's expected CDR dict.

    Required keys in output: caller, callee, call_time.
    Optional: duration, location, record_id.
    """
    def get(candidates: set[str]) -> str:
        col = _pick(lower_headers, candidates)
        return row.get(col, "").strip() if col else ""

    caller = get(_CDR_CALLER_COLS)
    callee = get(_CDR_CALLEE_COLS)
    ts = get(_CDR_TIME_COLS)

    if not caller:
        raise MissingRequiredColumnsError("CDR row missing caller/entity value")
    if not callee:
        raise MissingRequiredColumnsError("CDR row missing callee value")
    if not ts:
        raise MissingRequiredColumnsError("CDR row missing timestamp/call_time value")

    result: dict[str, Any] = {
        "caller": caller,
        "callee": callee,
        "call_time": ts,
    }

    duration_col = _pick(lower_headers, {"duration", "duration_s", "duration_sec"})
    if duration_col and row.get(duration_col, "").strip():
        try:
            result["duration"] = int(float(row[duration_col]))
        except (ValueError, TypeError):
            pass  # optional — skip if non-numeric

    location_col = _pick(lower_headers, {"location", "cell", "cell_id", "tower"})
    if location_col and row.get(location_col, "").strip():
        result["location"] = row[location_col].strip()

    record_id_col = _pick(lower_headers, {"record_id", "id", "cdr_id", "call_id"})
    if record_id_col and row.get(record_id_col, "").strip():
        result["record_id"] = row[record_id_col].strip()

    return result


# ── CSV parsing ───────────────────────────────────────────────────────────────


def parse_csv_bytes(data: bytes) -> tuple[RecordType, list[dict[str, Any]]]:
    """Parse CSV bytes into a (RecordType, list_of_normalised_dicts) tuple.

    Raises CsvParseError (or a subclass) on any validation failure.
    Does NOT touch the database.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception as exc:
            raise CsvParseError("CSV file could not be decoded as UTF-8 or latin-1.") from exc

    reader = csv.DictReader(io.StringIO(text))
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise CsvParseError(f"CSV parsing failed: {exc}") from exc

    if not rows:
        raise EmptyCsvError("CSV file contains no data rows.")

    # Use headers from first row
    lower_headers = _lower_headers(rows[0])
    schema = _detect_schema(lower_headers)
    if schema is None:
        raise UnrecognisedCsvSchemaError(
            "CSV columns do not match any supported schema. "
            "Expected TRANSACTION (source/sender, target/recipient, amount, timestamp) "
            "or CDR (caller/entity, callee, timestamp)."
        )

    normalised: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=2):  # row 1 is header
        lh = _lower_headers(row)
        try:
            if schema == RecordType.TRANSACTION:
                normalised.append(_normalise_transaction(row, lh))
            else:
                normalised.append(_normalise_cdr(row, lh))
        except MissingRequiredColumnsError as exc:
            raise MissingRequiredColumnsError(f"Row {i}: {exc}") from exc

    return schema, normalised


# ── Idempotent persistence ────────────────────────────────────────────────────


def _row_fingerprint(document_id: uuid.UUID, record_type: RecordType, payload: dict[str, Any]) -> str:
    """Deterministic fingerprint for a (document, type, payload) triple.

    Used as the idempotency key: the same CSV row processed twice produces
    the same fingerprint, so we skip duplicates without a full table scan.
    """
    # Sort keys so dict ordering does not affect the hash.
    stable = f"{document_id}|{record_type.value}|{sorted(payload.items())}"
    return hashlib.sha256(stable.encode()).hexdigest()


def upsert_structured_records(
    session: Session,
    *,
    document_id: uuid.UUID,
    case_id: uuid.UUID,
    record_type: RecordType,
    payloads: list[dict[str, Any]],
) -> int:
    """Persist normalised records idempotently. Returns the count of new rows created.

    Existing rows for (document_id, record_type, raw_json) are skipped.
    We use a SHA-256 fingerprint stored in raw_json["_fp"] for O(1) deduplication
    without adding a new DB column.
    """
    # Fetch existing fingerprints for this document in one query.
    existing = session.scalars(
        select(StructuredRecord).where(
            StructuredRecord.document_id == document_id,
            StructuredRecord.record_type == record_type,
        )
    ).all()
    existing_fps: set[str] = {
        row.raw_json.get("_fp", "") for row in existing if row.raw_json
    }

    created = 0
    for payload in payloads:
        fp = _row_fingerprint(document_id, record_type, payload)
        if fp in existing_fps:
            continue
        tagged = dict(payload)
        tagged["_fp"] = fp
        session.add(
            StructuredRecord(
                document_id=document_id,
                case_id=case_id,
                record_type=record_type,
                raw_json=tagged,
            )
        )
        existing_fps.add(fp)
        created += 1

    session.flush()
    return created
