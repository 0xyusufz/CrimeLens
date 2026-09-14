"""Isolated ML adapter. Person B owns extraction; this only calls their entry point."""

from __future__ import annotations

import importlib
import uuid
from typing import Any, Optional, Protocol

from pydantic import ValidationError

from shared.schemas import ExtractionEnvelope


class MlUnavailableError(Exception):
    """Person B has not provided a callable process_document yet."""


class MlContractError(Exception):
    """ML output did not match the shared ExtractionEnvelope contract."""


class MlDocumentProcessor(Protocol):
    def process_document(
        self,
        document_bytes: bytes,
        filename: str,
        document_id: str,
    ) -> Any:
        """Return an ExtractionEnvelope or JSON that validates as one."""


_PERSON_B_CANDIDATES = (
    ("ml.process", "process_document"),
    ("ml.pipeline", "process_document"),
    ("ml.extract", "process_document"),
)

_PERSON_B_PATTERN_CANDIDATES = (
    ("ml.process", "detect_patterns"),
    ("ml.pipeline", "detect_patterns"),
    ("ml.extract", "detect_patterns"),
)


def load_person_b_detect_patterns():
    """Return Person B's pattern entry point if it exists. Does not implement patterns here."""
    for module_name, attr in _PERSON_B_PATTERN_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        fn = getattr(module, attr, None)
        if callable(fn):
            return fn
    return None


def collect_person_b_intelligence(
    processor: MlDocumentProcessor,
    document_bytes: bytes,
    filename: str,
    document_id: uuid.UUID,
    *,
    session: Optional[Any] = None,
) -> tuple[list, list]:
    """Return (patterns_raw, leads_raw). Empty when Person B has no pattern entry point.

    When ``session`` is provided and the root ml.pipeline is available (post-merge),
    the backend fetches StructuredRecord rows for the case and passes them as structured
    data to ml.pipeline.process_document so the ML never touches the database directly.
    """
    detect = getattr(processor, "detect_patterns", None)
    if not callable(detect):
        detect = load_person_b_detect_patterns()

    if detect is None and session is not None:
        # Post-merge path: root ml.pipeline.process_document is available but has no
        # standalone detect_patterns. Bridge backend StructuredRecords into ML pipeline.
        return _collect_via_pipeline(document_bytes, filename, document_id, session)

    if detect is None:
        return [], []
    try:
        raw = detect(document_bytes, filename, str(document_id))
    except MlUnavailableError:
        return [], []
    except Exception as exc:
        raise MlContractError("ML pattern output failed contract validation.") from exc
    if raw is None:
        return [], []
    if isinstance(raw, list):
        return raw, []
    if isinstance(raw, dict):
        return raw.get("patterns") or [], raw.get("leads") or []
    raise MlContractError("ML pattern output failed contract validation.")


def _collect_via_pipeline(
    document_bytes: bytes,
    filename: str,
    document_id: uuid.UUID,
    session: Any,
) -> tuple[list, list]:
    """Bridge path: fetch StructuredRecords from PostgreSQL, translate field names, invoke
    ml.pipeline.process_document with return_full_analysis=True.

    Backend is responsible for database access. ML receives plain data dicts.
    """
    try:
        pipeline_mod = importlib.import_module("ml.pipeline")
        process_document_fn = getattr(pipeline_mod, "process_document", None)
        if not callable(process_document_fn):
            return [], []
    except ImportError:
        return [], []

    # --- Backend fetches structured records (DB access stays in backend) ---
    from sqlalchemy import select
    from app.models.document import Document, StructuredRecord
    from app.models.enums import RecordType

    doc = session.get(Document, document_id)
    if doc is None:
        return [], []

    records = list(
        session.scalars(
            select(StructuredRecord).where(StructuredRecord.case_id == doc.case_id)
        ).all()
    )

    # Translate PostgreSQL StructuredRecord.raw_json → ml.structured field names.
    # Transaction: source/target/amount/timestamp → sender/recipient/amount/currency/transaction_time
    # CDR:         entity/location/timestamp       → caller/callee/call_time/location
    transactions: list[dict] = []
    cdrs: list[dict] = []

    for r in records:
        payload = r.raw_json or {}
        rec_id = str(r.id)  # use PostgreSQL UUID as record_id for deterministic fingerprints

        if r.record_type == RecordType.TRANSACTION:
            src = payload.get("source") or payload.get("sender") or ""
            tgt = payload.get("target") or payload.get("recipient") or ""
            ts = payload.get("timestamp") or payload.get("transaction_time") or ""
            amt = payload.get("amount", 0)
            if src and tgt and ts:
                transactions.append({
                    "sender": src,
                    "recipient": tgt,
                    "amount": float(amt),
                    "currency": payload.get("currency", "INR"),
                    "transaction_time": ts,
                    "record_id": rec_id,
                })
        elif r.record_type == RecordType.CDR:
            entity = payload.get("entity") or payload.get("caller") or ""
            location = payload.get("location") or ""
            ts = payload.get("timestamp") or payload.get("call_time") or ""
            if entity and ts:
                cdrs.append({
                    "caller": entity,
                    "callee": payload.get("callee", entity + "_unknown"),
                    "call_time": ts,
                    "location": location,
                    "record_id": rec_id,
                })

    if not transactions and not cdrs:
        return [], []

    # --- Call ML pipeline with prepared data (ML never touches DB) ---
    try:
        result = process_document_fn(
            document_bytes,
            filename,
            str(document_id),
            return_full_analysis=True,
            transactions=transactions,
            cdrs=cdrs,
        )
    except Exception as exc:
        raise MlContractError(f"ml.pipeline.process_document failed: {exc}") from exc

    if not isinstance(result, dict):
        return [], []

    raw_patterns = result.get("patterns") or []
    raw_leads = result.get("leads") or []

    # Serialize Pydantic Pattern/Lead objects to dicts if needed (shared.schemas models).
    def _to_dict(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        return obj

    # Also inject deterministic fingerprint as `id` so backend upsert deduplication works.
    # ml.pipeline uses sequential ids like "pattern_001"; we keep them as-is since the
    # backend's _upsert_output already deduplicates on (case_id, kind, source_id).
    # The sequential IDs will repeat across runs IF evidence_ids are stable (same records).
    # For full idempotency we override with a content-based fingerprint here.
    import hashlib
    case_id_str = str(doc.case_id)

    serialized_patterns = []
    for p in raw_patterns:
        pd = _to_dict(p)
        entities = pd.get("entities") or []
        ev_ids = pd.get("evidence_ids") or []
        stable = "|".join([
            case_id_str,
            pd.get("type", ""),
            ",".join(sorted(str(e) for e in entities)),
            ",".join(sorted(str(e) for e in ev_ids)),
        ])
        pd["id"] = hashlib.sha256(stable.encode()).hexdigest()[:32]
        serialized_patterns.append(pd)

    serialized_leads = []
    for ld in raw_leads:
        ld_d = _to_dict(ld)
        entity_ids = ld_d.get("entity_ids") or []
        ev_ids = ld_d.get("evidence_ids") or []
        stable = "|".join([
            case_id_str,
            ld_d.get("type", "") + "_LEAD",
            ",".join(sorted(str(e) for e in entity_ids)),
            ",".join(sorted(str(e) for e in ev_ids)),
        ])
        ld_d["id"] = hashlib.sha256(stable.encode()).hexdigest()[:32]
        serialized_leads.append(ld_d)

    return serialized_patterns, serialized_leads



def load_person_b_process_document():
    """Return Person B's callable if it exists. Does not implement ML here."""
    for module_name, attr in _PERSON_B_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        fn = getattr(module, attr, None)
        if callable(fn):
            return fn
    return None


class PersonBDocumentProcessor:
    """Thin wrapper around Person B's process_document(bytes, filename, document_id)."""

    def process_document(
        self,
        document_bytes: bytes,
        filename: str,
        document_id: str,
    ) -> Any:
        fn = load_person_b_process_document()
        if fn is None:
            raise MlUnavailableError(
                "Person B ML process_document is not available yet."
            )
        return fn(document_bytes, filename, document_id)


def fixture_extraction_payload(document_id: str) -> dict[str, Any]:
    """TEMPORARY test/dev ExtractionEnvelope. Not Person B's ML pipeline."""
    return {
        "document_id": document_id,
        "entities": [
            {
                "id": "mention_001",
                "type": "PERSON",
                "name": "Rahul Sharma",
                "confidence": 0.96,
            },
            {
                "id": "mention_002",
                "type": "PERSON",
                "name": "Amit Kumar",
                "confidence": 0.94,
            },
            {
                "id": "mention_003",
                "type": "PHONE",
                "name": "9876543210",
                "confidence": 0.99,
            },
            {
                "id": "mention_004",
                "type": "LOCATION",
                "name": "Bhubaneswar",
                "confidence": 0.91,
            },
        ],
        "relationships": [
            {
                "id": "rel_001",
                "source_entity_id": "mention_001",
                "relationship": "CALLED",
                "target_entity_id": "mention_002",
                "confidence": 0.98,
                "status": "CONFIRMED",
                "source_document_id": document_id,
                "evidence_snippet": "Rahul called Amit Kumar.",
                "extracted_at": "2026-09-13T10:30:00",
            },
            {
                "id": "rel_002",
                "source_entity_id": "mention_001",
                "relationship": "ASSOCIATED_WITH",
                "target_entity_id": "mention_003",
                "confidence": 0.88,
                "status": "INFERRED",
                "source_document_id": document_id,
                "evidence_snippet": "Rahul's number is 9876543210.",
                "extracted_at": "2026-09-13T10:30:00",
            },
            {
                "id": "rel_003",
                "source_entity_id": "mention_001",
                "relationship": "LOCATED_AT",
                "target_entity_id": "mention_004",
                "confidence": 0.70,
                "status": "PREDICTED",
                "source_document_id": document_id,
                "evidence_snippet": "Call associated with Bhubaneswar.",
                "extracted_at": "2026-09-13T10:30:00",
            },
        ],
    }


class FixtureDocumentProcessor:
    """TEMPORARY deterministic adapter for backend integration tests.

    Person B replaces this by exporting process_document from ml.process,
    ml.pipeline, or ml.extract. This class contains no OCR/NER/models.
    """

    def process_document(
        self,
        document_bytes: bytes,
        filename: str,
        document_id: str,
    ) -> Any:
        return ExtractionEnvelope.model_validate(fixture_extraction_payload(document_id))


def get_ml_processor() -> MlDocumentProcessor:
    return PersonBDocumentProcessor()


def _document_ids_match(envelope_document_id: str, document_id: uuid.UUID) -> bool:
    try:
        return uuid.UUID(envelope_document_id) == document_id
    except ValueError:
        return False


def run_document_processor(
    processor: MlDocumentProcessor,
    document_bytes: bytes,
    filename: str,
    document_id: uuid.UUID,
) -> ExtractionEnvelope:
    """Call ML and validate the shared ExtractionEnvelope. No persistence."""
    try:
        raw = processor.process_document(document_bytes, filename, str(document_id))
        if isinstance(raw, ExtractionEnvelope):
            envelope = raw
        else:
            envelope = ExtractionEnvelope.model_validate(raw)
    except MlUnavailableError:
        raise
    except ValidationError as exc:
        raise MlContractError("ML output failed contract validation.") from exc
    except MlContractError:
        raise
    except Exception as exc:
        raise MlContractError("ML output failed contract validation.") from exc

    if not _document_ids_match(envelope.document_id, document_id):
        raise MlContractError("ML document_id does not match the processed document.")
    return envelope
