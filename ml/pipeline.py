"""CrimeLens ML Pipeline Orchestration Interface (Phase 10).

Integrates the end-to-end intelligence flow:
Document Text / Image
  ↓
Document Loading & Preprocessing (Phase 2) / OCR (Phase 3)
  ↓
Entity Mention Extraction (Phase 4)
  ↓
Structured Ingestion (Phase 7: Transactions & CDRs)
  ↓
Relationship Extraction (Phase 5)
  ↓
Entity Resolution Proposals (Phase 6)
  ↓
Suspicious Pattern Detection (Phase 8)
  ↓
Investigative Lead Generation (Phase 9)
  ↓
Output Validation (Phase 1)
  ↓
ExtractionResult / Structured Analysis JSON

ML produces structured contract JSON. It NEVER writes to PostgreSQL or Neo4j,
mints zero database UUIDs, generates zero case_ids, and performs no guilt prediction.
"""

from typing import Any, Optional

from ml.config import MLConfig, default_config
from ml.extraction import extract_entities
from ml.leads import generate_leads
from ml.ocr import extract_text_from_image
from ml.patterns import (
    detect_circular_transactions,
    detect_location_time_overlaps,
    detect_rapid_transfers,
)
from ml.preprocessing import is_scanned_file, load_document, normalize_text
from ml.relationships import extract_relationships
from ml.resolution import propose_resolutions
from ml.structured import (
    CDRRecord,
    TransactionRecord,
    parse_cdr,
    parse_cdrs,
    parse_transaction,
    parse_transactions,
)
from ml.validation import (
    validate_extraction_result,
    validate_lead,
    validate_pattern,
    validate_resolution_proposal,
)
from shared.schemas.enums import EntityType
from shared.schemas.models import (
    EntityMention,
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)


def process_document(
    *args: Any,
    document_id: Optional[str] = None,
    text: Optional[str | bytes] = None,
    config: Optional[MLConfig] = None,
    return_full_analysis: bool = False,
    **kwargs: Any,
) -> ExtractionResult | dict[str, Any]:
    """Main entry point for document analysis and intelligence orchestration in CrimeLens ML.

    Supports:
    - process_document(document_id, text, ...)
    - process_document(document_bytes, filename, document_id) [backend adapter convention]
    - process_document(document_id, text, return_full_analysis=True) [full intelligence bundle]

    Args:
        *args: Positional arguments matching standard or backend convention.
        document_id: Staging document identifier (e.g., 'doc_001').
        text: Raw document text string, plain text file path, image file path, or image bytes.
        config: Optional ML configuration instance.
        return_full_analysis: If True, returns full dictionary containing ExtractionResult,
            entities, relationships, resolution_proposals, patterns, and leads.
            If False (default), returns validated ExtractionResult envelope.
        **kwargs: Additional structured records, transactions, CDRs, patterns, or test hooks.

    Returns:
        ExtractionResult | dict[str, Any]: Validated Pydantic envelope or full analysis dictionary.

    Raises:
        ValueError: If document_id is empty or invalid.
        TypeError: If text is neither a string nor bytes.
        FileNotFoundError: If an image or document path does not exist.
        OCRError: If an OCR engine or image validation error occurs.
    """
    # 1. Resolve calling conventions
    if len(args) == 3:
        # Backend adapter convention: (document_bytes, filename, document_id)
        doc_content, filename, doc_id = args
        document_id = str(doc_id)
        if isinstance(doc_content, bytes):
            if not is_scanned_file(str(filename)):
                try:
                    text = doc_content.decode("utf-8")
                except UnicodeDecodeError:
                    text = doc_content.decode("latin-1")
            else:
                text = doc_content
        else:
            text = doc_content
    elif len(args) == 2:
        first, second = args
        if first is None or first == "":
            document_id = first
            text = second
        elif isinstance(first, str) and (
            first.startswith("doc_")
            or len(first) == 36
            or not isinstance(second, str)
            or len(first) < len(second)
        ):
            document_id = str(first)
            text = second
        else:
            text = first
            document_id = str(second)
    elif len(args) == 1:
        if document_id is None:
            document_id = str(args[0])
        else:
            text = args[0]

    if document_id is None or not str(document_id).strip():
        raise ValueError("document_id must not be empty")

    doc_id_str = str(document_id).strip()

    if text is None:
        text = ""

    cfg = config or default_config
    ocr_runner = kwargs.get("ocr_engine_runner")
    ner_runner = kwargs.get("ner_runner")

    # 2. Document Ingestion & Preprocessing: Plain text vs. Scanned/Image via Phase 3 OCR
    if isinstance(text, bytes):
        raw_text = extract_text_from_image(text, lang=cfg.default_ocr_language, engine_runner=ocr_runner)
    elif isinstance(text, str):
        if is_scanned_file(text):
            raw_text = extract_text_from_image(text, lang=cfg.default_ocr_language, engine_runner=ocr_runner)
        else:
            raw_text = load_document(text)
    else:
        raise TypeError("text must be a string or bytes")

    # Flow OCR or loaded text through text normalizer (Phase 2)
    clean_text = normalize_text(raw_text)

    # 3. Entity Mention Extraction (Phase 4)
    entities: list[EntityMention] = []
    if clean_text:
        entities = extract_entities(
            clean_text,
            document_id=doc_id_str,
            min_confidence=cfg.min_entity_confidence,
            ner_runner=ner_runner,
        )

    # 4. Structured Records Ingestion (Phase 7)
    structured_records = kwargs.get("structured_records") or []
    transactions_input = kwargs.get("transactions") or []
    cdrs_input = kwargs.get("cdrs") or []

    all_structured: list[Any] = list(structured_records)
    parsed_transactions: list[TransactionRecord] = []
    parsed_cdrs: list[CDRRecord] = []

    # Parse explicit transactions
    if transactions_input:
        for t in transactions_input:
            try:
                parsed_t = parse_transaction(t)
                parsed_transactions.append(parsed_t)
                all_structured.append(parsed_t)
            except Exception:
                continue

    # Parse explicit CDRs
    if cdrs_input:
        for c in cdrs_input:
            try:
                parsed_c = parse_cdr(c)
                parsed_cdrs.append(parsed_c)
                all_structured.append(parsed_c)
            except Exception:
                continue

    # Parse generic structured_records list into typed records if present
    for r in structured_records:
        if isinstance(r, TransactionRecord):
            if r not in parsed_transactions:
                parsed_transactions.append(r)
        elif isinstance(r, CDRRecord):
            if r not in parsed_cdrs:
                parsed_cdrs.append(r)
        elif isinstance(r, dict):
            if "sender" in r and "recipient" in r:
                try:
                    parsed_tx = parse_transaction(r)
                    if parsed_tx not in parsed_transactions:
                        parsed_transactions.append(parsed_tx)
                except Exception:
                    pass
            elif "caller" in r and "callee" in r:
                try:
                    parsed_cdr = parse_cdr(r)
                    if parsed_cdr not in parsed_cdrs:
                        parsed_cdrs.append(parsed_cdr)
                except Exception:
                    pass

    # Ensure staging EntityMentions exist for structured participants to enable relationship linkage
    existing_entities_by_name = {e.name.strip().lower(): e for e in entities}
    mention_counter = len(entities) + 1

    for tx in parsed_transactions:
        s_name = tx.sender.strip()
        r_name = tx.recipient.strip()
        if s_name.lower() not in existing_entities_by_name:
            m = EntityMention(
                id=f"mention_{mention_counter:03d}",
                type=EntityType.BANK_ACCOUNT,
                name=s_name,
                confidence=1.0,
            )
            entities.append(m)
            existing_entities_by_name[s_name.lower()] = m
            mention_counter += 1
        if r_name.lower() not in existing_entities_by_name:
            m = EntityMention(
                id=f"mention_{mention_counter:03d}",
                type=EntityType.BANK_ACCOUNT,
                name=r_name,
                confidence=1.0,
            )
            entities.append(m)
            existing_entities_by_name[r_name.lower()] = m
            mention_counter += 1

    for cdr in parsed_cdrs:
        c_name = cdr.caller.strip()
        ce_name = cdr.callee.strip()
        if c_name.lower() not in existing_entities_by_name:
            m = EntityMention(
                id=f"mention_{mention_counter:03d}",
                type=EntityType.PHONE,
                name=c_name,
                confidence=1.0,
            )
            entities.append(m)
            existing_entities_by_name[c_name.lower()] = m
            mention_counter += 1
        if ce_name.lower() not in existing_entities_by_name:
            m = EntityMention(
                id=f"mention_{mention_counter:03d}",
                type=EntityType.PHONE,
                name=ce_name,
                confidence=1.0,
            )
            entities.append(m)
            existing_entities_by_name[ce_name.lower()] = m
            mention_counter += 1

    # 5. Relationship Extraction (Phase 5)
    relationships: list[Relationship] = extract_relationships(
        clean_text,
        entities=entities,
        document_id=doc_id_str,
        structured_records=all_structured if all_structured else None,
        min_confidence=cfg.min_relationship_confidence,
    )

    # 6. Entity Resolution Proposals (Phase 6)
    resolution_proposals: list[ResolutionProposal] = []
    if len(entities) >= 2:
        resolution_proposals = propose_resolutions(
            entities,
            relationships=relationships,
            min_confidence=cfg.min_resolution_confidence,
        )
        for prop in resolution_proposals:
            validate_resolution_proposal(prop)

    # 7. Suspicious Pattern Detection (Phase 8)
    patterns: list[Pattern] = []
    if kwargs.get("patterns"):
        for p in kwargs["patterns"]:
            patterns.append(validate_pattern(p))

    # Detect circular transactions (<= 30 days)
    if len(parsed_transactions) >= 3:
        circ_patterns = detect_circular_transactions(parsed_transactions)
        patterns.extend(circ_patterns)

    # Detect rapid transfer chains (<= 48 hours)
    if len(parsed_transactions) >= 2:
        rapid_patterns = detect_rapid_transfers(parsed_transactions)
        patterns.extend(rapid_patterns)

    # Detect spatio-temporal co-presence (<= 2 hours)
    spatio_temporal_records = list(parsed_cdrs) + list(parsed_transactions)
    for r in all_structured:
        if isinstance(r, dict) and r.get("location") and (r.get("timestamp") or r.get("time")):
            if r not in spatio_temporal_records:
                spatio_temporal_records.append(r)

    if len(spatio_temporal_records) >= 2:
        overlap_patterns = detect_location_time_overlaps(spatio_temporal_records)
        patterns.extend(overlap_patterns)

    # Validate patterns
    for p in patterns:
        validate_pattern(p)

    # 8. Investigative Lead Generation (Phase 9)
    leads: list[Lead] = []
    if kwargs.get("leads"):
        for ld in kwargs["leads"]:
            leads.append(validate_lead(ld))
    elif patterns or relationships:
        leads = generate_leads(patterns=patterns, relationships=relationships)
        for ld in leads:
            validate_lead(ld)

    # 9. Envelope Construction & Validation (Phase 1 & Phase 10)
    extraction_result = ExtractionResult(
        document_id=doc_id_str,
        entities=entities,
        relationships=relationships,
    )
    validate_extraction_result(extraction_result)

    # 10. Result Dispatch
    should_return_analysis = (
        return_full_analysis
        or kwargs.get("return_analysis", False)
        or kwargs.get("return_intelligence", False)
    )

    if should_return_analysis:
        return {
            "document_id": doc_id_str,
            "extraction_result": extraction_result,
            "entities": entities,
            "relationships": relationships,
            "resolution_proposals": resolution_proposals,
            "patterns": patterns,
            "leads": leads,
            "structured_records": all_structured,
        }

    return extraction_result

