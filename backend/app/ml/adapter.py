"""Isolated ML adapter. Person B owns extraction; this only calls their entry point."""

from __future__ import annotations

import importlib
import uuid
from typing import Any, Protocol

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
