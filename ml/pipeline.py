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

from ml.ai.providers.groq_provider import groq_extractor
from ml.config import MLConfig, default_config
from ml.extraction import classify_entity_candidates, extract_entities
from ml.ingestion import DocumentKind, ingest_document
from ml.leads import generate_leads
from ml.ocr import (
    apply_ocr_confidence_to_entities,
    apply_ocr_confidence_to_relationships,
    extract_tesseract_blocks,
    extract_text_from_image,
)
from ml.patterns import (
    detect_circular_transactions,
    detect_location_time_overlaps,
    detect_rapid_transfers,
)
from ml.preprocessing import normalize_text
from ml.relationships import (
    consolidate_relationship_evidence,
    extract_relationships,
    generate_relationship_candidates,
)
from ml.resolution import detect_contradictions, propose_case_memory_links, propose_resolutions
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
from ml.intelligence import (
    apply_graph_quality_firewall,
    analyze_orphans,
    assess_sos,
    integrate_ai_candidates,
    understand_document,
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
    resolved_filename: str | None = None
    if len(args) == 3:
        # Backend adapter convention: (document_bytes, filename, document_id)
        doc_content, filename, doc_id = args
        resolved_filename = str(filename)
        document_id = str(doc_id)
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
    input_filename: str | None = resolved_filename

    # 2. Evidence ingestion: hash/type/native-text extraction before OCR.
    ingested = ingest_document(doc_id_str, text, filename=input_filename)
    input_filename = ingested.filename or input_filename
    ocr_blocks: list[dict[str, Any]] = []
    processing_warnings: list[str] = []
    if ingested.needs_ocr and ingested.kind == DocumentKind.IMAGE:
        layout_runner = kwargs.get("ocr_blocks_runner")
        if callable(layout_runner):
            raw_blocks = layout_runner(ingested.raw_bytes or b"", cfg.default_ocr_language)
            ocr_blocks = [
                item.as_dict() if hasattr(item, "as_dict") else dict(item)
                for item in raw_blocks
            ]
            raw_text = "\n".join(str(block.get("text") or "") for block in ocr_blocks)
        elif kwargs.get("use_layout_ocr", False) and ocr_runner is None:
            ocr_blocks = [
                block.as_dict()
                for block in extract_tesseract_blocks(
                    ingested.raw_bytes or b"",
                    lang=cfg.default_ocr_language,
                )
            ]
            raw_text = "\n".join(str(block.get("text") or "") for block in ocr_blocks)
        else:
            raw_text = extract_text_from_image(
                ingested.raw_bytes or b"",
                lang=cfg.default_ocr_language,
                engine_runner=ocr_runner,
            )
            ocr_blocks.append(
                {
                    "page": 1,
                    "line_id": 1,
                    "text": raw_text,
                    "confidence": kwargs.get("ocr_confidence", 0.75),
                    "bbox": None,
                }
            )
    elif ingested.needs_ocr and ingested.kind == DocumentKind.PDF:
        pdf_ocr_runner = kwargs.get("pdf_ocr_runner")
        if callable(pdf_ocr_runner):
            pdf_output = pdf_ocr_runner(ingested.raw_bytes or b"", input_filename or "document.pdf")
            if isinstance(pdf_output, dict):
                raw_text = str(pdf_output.get("text") or "")
                ocr_blocks = list(pdf_output.get("blocks") or [])
            else:
                raw_text = str(pdf_output or "")
        else:
            raw_text = ""
            processing_warnings.append("scanned_pdf_requires_pdf_ocr_runner")
    else:
        raw_text = ingested.text

    # Flow OCR or loaded text through text normalizer (Phase 2)
    clean_text = normalize_text(raw_text)

    # 3. Document understanding metadata is internal and additive.
    understanding = understand_document(
        clean_text,
        doc_id_str,
        filename=input_filename,
        source_kind="ocr" if ingested.needs_ocr else "native_text",
        ocr_confidence=kwargs.get("ocr_confidence"),
        ocr_blocks=ocr_blocks,
        source_pages=[
            {
                "page": page.page_number,
                "text": normalize_text(page.text),
                "confidence": page.confidence,
            }
            for page in ingested.pages
            if page.text
        ],
    )
    gemini_understanding: dict[str, Any] = {}

    # 4. Entity Mention Extraction (Phase 4)
    entities: list[EntityMention] = []
    ai_relationships: list[Relationship] = []
    candidate_relationships: list[Relationship] = []
    ai_telemetry: dict[str, int] = {}
    entity_candidate_decisions: list[Any] = []

    if clean_text:
        entities, entity_candidate_decisions = extract_entities(
            clean_text,
            document_id=doc_id_str,
            min_confidence=cfg.min_entity_confidence,
            ner_runner=ner_runner,
            return_decisions=True,
        )
        if ocr_blocks:
            entities = apply_ocr_confidence_to_entities(entities, ocr_blocks)

        provider = kwargs.get("document_understanding_runner") or kwargs.get("ai_candidate_runner")
        if provider is None and kwargs.get("enable_groq", True) and groq_extractor.is_available():
            provider = groq_extractor
        if provider is not None:
            try:
                if hasattr(provider, "read"):
                    raw_provider_output = provider.read(
                        {
                            "document_id": doc_id_str,
                            "filename": input_filename,
                            "file_kind": ingested.kind.value,
                            "document_bytes": ingested.raw_bytes,
                            "text": clean_text,
                            "pages": [
                                {"page": page.page_number, "text": page.text}
                                for page in ingested.pages
                            ],
                            "ocr_blocks": ocr_blocks,
                        }
                    )
                    gemini_understanding = raw_provider_output if isinstance(raw_provider_output, dict) else {}
                else:
                    raw_provider_output = (
                        provider.extract(clean_text, doc_id_str)
                        if hasattr(provider, "extract")
                        else provider(clean_text, doc_id_str)
                    )
                entities, ai_relationships, ai_telemetry = integrate_ai_candidates(
                    entities,
                    raw_provider_output,
                    document_id=doc_id_str,
                    source_text=clean_text,
                    min_confidence=cfg.min_entity_confidence,
                    relationship_id_prefix="rel_document_ai",
                )
                entities, provider_decisions = classify_entity_candidates(
                    entities,
                    text=clean_text,
                    min_confidence=cfg.min_entity_confidence,
                )
                entity_candidate_decisions.extend(provider_decisions)
            except Exception:
                ai_telemetry = {"provider_error": 1}
        else:
            ai_telemetry = {}

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

    # Merge Groq-extracted network relationships into active relationships
    relationships.extend(ai_relationships)
    candidate_relationships.extend(ai_relationships)

    # Groq is restricted to closed-world relationship reasoning over accepted
    # mentions and evidence blocks.  It cannot add free-form entities.
    relationship_telemetry: dict[str, int] = {}
    relationship_reasoner = kwargs.get("relationship_reasoner")
    if relationship_reasoner is None and kwargs.get("enable_groq", False):
        try:
            from ml.relationships.groq_reasoner import GroqRelationshipReasoner

            candidate_reasoner = GroqRelationshipReasoner()
            relationship_reasoner = candidate_reasoner if candidate_reasoner.is_available() else None
        except Exception:
            relationship_reasoner = None
    if relationship_reasoner is not None and clean_text and entities:
        evidence_context = [
            {
                "id": block.block_id,
                "text": block.text,
                "page": block.page_number,
                "line_id": block.line_id,
            }
            for block in understanding.blocks
        ]
        raw_candidates, relationship_telemetry = generate_relationship_candidates(
            relationship_reasoner,
            entities=entities,
            evidence_blocks=evidence_context,
        )
        _, reasoned_relationships, candidate_telemetry = integrate_ai_candidates(
            entities,
            {"relationships": raw_candidates},
            document_id=doc_id_str,
            source_text=clean_text,
            min_confidence=cfg.min_relationship_confidence,
            relationship_id_prefix="rel_groq_candidate",
        )
        candidate_relationships.extend(reasoned_relationships)
        relationship_telemetry.update(
            {f"candidate_{key}": value for key, value in candidate_telemetry.items()}
        )

    # 6. Graph quality firewall: endpoint vocabulary, provenance, grounding,
    # duplicate consolidation, and contradiction telemetry.
    relationships, quality_report = apply_graph_quality_firewall(
        relationships,
        entities,
        source_text=clean_text,
        structured_records=all_structured,
        min_confidence=cfg.min_relationship_confidence,
    )
    if ocr_blocks:
        relationships = apply_ocr_confidence_to_relationships(relationships, entities)
    candidate_relationships, candidate_quality_report = apply_graph_quality_firewall(
        candidate_relationships,
        entities,
        source_text=clean_text,
        structured_records=all_structured,
        min_confidence=cfg.min_relationship_confidence,
    )

    # 7. Entity Resolution Proposals (Phase 6)
    resolution_proposals: list[ResolutionProposal] = []
    if len(entities) >= 2:
        resolution_proposals = propose_resolutions(
            entities,
            relationships=relationships,
            min_confidence=cfg.min_resolution_confidence,
        )
        for prop in resolution_proposals:
            validate_resolution_proposal(prop)
    case_memory_proposals = propose_case_memory_links(
        entities,
        kwargs.get("case_memory"),
    )
    contradictions = detect_contradictions(relationships, entities)

    # 8. Suspicious Pattern Detection (Phase 8)
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

    # 9. Investigative Lead Generation (Phase 9)
    leads: list[Lead] = []
    if kwargs.get("leads"):
        for ld in kwargs["leads"]:
            leads.append(validate_lead(ld))
    elif patterns or relationships:
        leads = generate_leads(patterns=patterns, relationships=relationships)
        for ld in leads:
            validate_lead(ld)

    # 10. Envelope Construction & Validation (Phase 1 & Phase 10)
    extraction_result = ExtractionResult(
        document_id=doc_id_str,
        entities=entities,
        relationships=relationships,
    )
    validate_extraction_result(extraction_result)

    # 11. Result Dispatch
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
            "document_understanding": {
                "document_type": understanding.document_type,
                "source_kind": understanding.source_kind,
                "file_kind": ingested.kind.value,
                "sha256": ingested.sha256,
                "block_count": understanding.block_count,
                "blocks": [
                    {
                        "id": block.block_id,
                        "page": block.page_number,
                        "line_id": block.line_id,
                        "bbox": block.bbox,
                        "confidence": block.confidence,
                        "start_char": block.start_char,
                        "end_char": block.end_char,
                    }
                    for block in understanding.blocks
                ],
            },
            "quality_report": quality_report.as_dict(),
            "candidate_quality_report": candidate_quality_report.as_dict(),
            "candidate_relationships": candidate_relationships,
            "orphan_analysis": [
                {
                    "mention_id": orphan.mention_id,
                    "name": orphan.name,
                    "entity_type": orphan.entity_type,
                    "accepted_degree": orphan.accepted_degree,
                    "candidate_degree": orphan.candidate_degree,
                    "reason": orphan.reason,
                }
                for orphan in analyze_orphans(entities, relationships, candidate_relationships)
            ],
            "relationship_evidence_groups": [
                {
                    "source_entity_id": group.source_entity_id,
                    "relationship": group.relationship,
                    "target_entity_id": group.target_entity_id,
                    "relationship_ids": list(group.relationship_ids),
                    "evidence_sources": list(group.evidence_sources),
                    "independent_source_count": group.independent_source_count,
                    "calibrated_confidence": group.calibrated_confidence,
                    "strongest_status": group.strongest_status,
                }
                for group in consolidate_relationship_evidence(relationships)
            ],
            "sos": assess_sos(patterns=patterns, relationships=relationships).as_dict(),
            "ai_telemetry": ai_telemetry,
            "gemini_document_understanding": gemini_understanding,
            "relationship_reasoning_telemetry": relationship_telemetry,
            "case_memory_proposals": [
                {
                    "mention_id": proposal.mention_id,
                    "canonical_entity_id": proposal.canonical_entity_id,
                    "confidence": proposal.confidence,
                    "signals": [signal.value for signal in proposal.signals],
                    "requires_review": proposal.requires_review,
                }
                for proposal in case_memory_proposals
            ],
            "contradictions": [
                {
                    "entity_id": contradiction.entity_id,
                    "relationship": contradiction.relationship.value,
                    "conflicting_targets": list(contradiction.conflicting_targets),
                    "relationship_ids": list(contradiction.relationship_ids),
                    "reason": contradiction.reason,
                }
                for contradiction in contradictions
            ],
            "entity_candidate_decisions": [
                {
                    "text": decision.text,
                    "proposed_type": decision.proposed_type,
                    "accepted": decision.accepted,
                    "reason": decision.reason,
                    "attached_to": decision.attached_to,
                }
                for decision in entity_candidate_decisions
            ],
            "processing_warnings": processing_warnings,
        }

    return extraction_result

