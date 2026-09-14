# ML & Intelligence Pipeline (Person B)

The `ml/` layer produces structured JSON intelligence from unstructured investigation documents (e.g., FIRs, transcripts, seizure memos).

## Architectural Boundary & Principles

```
Unstructured Input (Text / Documents)
                  ↓
          ML Pipeline (`ml/`)
                  ↓
       Structured Contract JSON
                  ↓
FastAPI Schema Validation (`backend/` - Person A)
                  ↓
 PostgreSQL (Canonical Records / Source of Truth)
                  ↓
       Neo4j (Derived Knowledge Graph)
```

1. **Structured JSON Output Only**: ML produces schema-compliant Pydantic models (`ExtractionResult`, `ResolutionProposal`, `Pattern`, `Lead`).
2. **No Direct Database Access**: Never connect to PostgreSQL or Neo4j from `ml/`. ML contains zero database-writing or query code.
3. **No Competing HTTP APIs**: ML exposes a clean Python module interface (`process_document(...)`) for backend invocation. ML does not define separate FastAPI or HTTP endpoints.
4. **No Identity Minting**:
   - `id` on `EntityMention` (`mention_001`) is a document-level staging ID.
   - `canonical_entity_id` on `ResolutionProposal` is an ML grouping proposal only.
   - Canonical entity UUIDs and case membership (`case_id`) are minted exclusively by the backend in PostgreSQL.
5. **Frozen Semantics**:
   - Evidence statuses: `CONFIRMED`, `INFERRED`, `PREDICTED`. (No `DETECTED` status; never coerce inferred to confirmed).
   - Leads: use `priority` (`LOW`, `MEDIUM`, `HIGH`) and investigative workflow `status`. No severity in leads, and no person-level criminal risk/guilt scoring.
   - Exact identifier matching (phone, bank account) may propose resolution; name-only fuzzy matching must never auto-merge.

## Package Architecture & Future Module Responsibilities

- **`ml/pipeline.py`**: Main entry interface coordinating document analysis (`process_document(...)`).
- **`ml/config.py`**: Lightweight ML parameters (confidence thresholds, max token lengths). Contains no database credentials.
- **`ml/preprocessing/`** (Phase 2):
  - `document_loader.py`: Ingestion and reading of raw text and document files; flags scanned/image documents for Phase 3 OCR.
  - `text_normalizer.py`: Whitespace cleaning, CRLF->LF normalization, and Unicode NFC normalization while strictly preserving numbers, dates, amounts, phone/vehicle/account identifiers, and evidence phrasing.
  - *Boundary*: Preprocessing does NOT perform OCR, entity extraction, or summarization. It receives text from document loader or raw text from Phase 3 OCR.
- **`ml/ocr/`** (Phase 3):
  - `tesseract.py`: Validates image bytes/files (PNG, JPEG, TIFF, BMP) and executes local Tesseract CLI; provides `extract_text_from_image(...)` and `extract_ocr_result(...)` with structured metadata.
  - *Boundary*: OCR only extracts raw text from images and forwards it to Phase 2 `normalize_text`. It does NOT perform entity extraction, relationship extraction, or database writes.
- **`ml/extraction/`** (Phase 4):
  - `regex.py`: Deterministic rule/regex extraction for structured identifiers (`PHONE`, `BANK_ACCOUNT`, `VEHICLE`).
  - `ner.py`: Named entity recognition for contextual mentions (`PERSON`, `ORGANIZATION`, `LOCATION`, `EVENT`).
  - `entity_extractor.py`: Coordinates regex and NER extraction, normalizes formatting, deduplicates safe overlapping candidates, and assigns unique document-level staging IDs (`mention_001`, `mention_002`, ...).
  - *Boundary*: Entity extraction extracts mentions into schema-compliant `EntityMention` objects. It does NOT create relationships (Phase 5) or resolve/merge entities across mentions (Phase 6).
- **`ml/relationships/`** (Phase 5):
  - `rule_extractor.py`: Evidence-backed relationship extraction between extracted `EntityMention`s, emitting structured `shared.schemas.Relationship` instances.
  - *Supported Vocabulary*: Exclusively the 8 frozen relationship types (`CALLED`, `SENT_MONEY_TO`, `OWNS_VEHICLE`, `USED_VEHICLE`, `WORKS_FOR`, `LOCATED_AT`, `ASSOCIATED_WITH`, `PART_OF_EVENT`).
  - *Directionality & Evidence*: Strict direction enforcement (e.g. sender -> SENT_MONEY_TO -> recipient; caller -> CALLED -> callee) with non-fabricated evidence snippets sourced directly from the document or structured record.
  - *Negation & Co-occurrence*: Co-occurrence alone never generates a relationship; basic negation is conservatively respected.
  - *Extraction vs Resolution Distinction*: Phase 5 identifies relationships between document mentions using staging mention IDs (`mention_001` -> `mention_002`). It does NOT perform cross-document entity resolution, canonical UUID generation, or graph edge writing in Neo4j.
  - *Backend Handoff*: Staged `Relationship` records are packaged in `ExtractionResult.relationships` and validated by FastAPI/Pydantic schemas before persistence by Person A.
- **`ml/resolution/`** (Phase 6):
  - `resolver.py`: Compares extracted `EntityMention` instances and emits structured `shared.schemas.ResolutionProposal` objects.
  - *Core Principle*: **ML proposes. Backend/database decides canonical persistence.** ML assigns grouping keys (`entity_001`, `entity_002`), never canonical database UUIDs or `case_id`.
  - *Exact Strong Identifiers*: Exact normalized phone (`phone_match`), bank account (`account_match`), and vehicle registration (`vehicle_match`) produce high-confidence proposals (>= 0.90).
  - *Multi-Signal Matching*: Combining name similarity with verified auxiliary identifiers (phone, account) strengthens proposal confidence to 0.98.
  - *Fuzzy Name Policy*: Name-only fuzzy matching (`Rahul Kumar` vs `Rahul K.`) produces conservative review suggestions (confidence=0.60) and **NEVER** automatically merges entities.
  - *Conflicting Identifiers*: Conflicting strong identifiers (e.g. same name but conflicting phones) suppress resolution proposals.
  - *Type Safety*: Cross-type matching is strictly disallowed (e.g. PERSON ↔ BANK_ACCOUNT never resolve).
- **`ml/structured/`** (Phase 7):
  - `cdr.py`: Validates and normalizes Call Detail Records (`CDRRecord`), preserving `caller`, `callee`, `call_time`, `duration`, `location`, and `cell_id`. Enforces caller -> CALLED -> callee direction.
  - `transactions.py`: Validates and normalizes financial records (`TransactionRecord`), preserving `sender`, `recipient`, `amount` (unrounded), `currency` (unconverted), `transaction_time`, and `location`. Enforces sender -> SENT_MONEY_TO -> recipient direction.
  - *Pattern-Readiness*: Phase 7 prepares and preserves structured records for downstream analysis. **Phase 7 prepares structured data; Phase 8 detects patterns.** Zero `Pattern` or `Lead` objects are emitted in Phase 7.
  - *Relationship Integration*: Provides clean adapters (`cdr_to_relationship`, `transaction_to_relationship`) directly compatible with Phase 5 relationship extraction.
  - *Backend Boundary*: Structured record handling remains internal to ML; no database writes, no canonical UUIDs, and no API changes.
- **`ml/patterns/`** (Phase 8):
  - `circular_transaction.py`: Detects 3-node directed cyclic money flow (`CIRCULAR_TRANSACTION`: A → B → C → A) where A, B, and C are distinct nodes and `latest_time - earliest_time <= 30 days` (fixed MVP demo threshold). Deduplicates cycles under canonical rotation.
  - `rapid_transfer.py`: Detects rapid pass-through / layering chains (`RAPID_TRANSFER_CHAIN`: A → B → C) where A, B, and C are distinct nodes, $t_1 \le t_2$, and $t_2 - t_1 \le 48\text{ hours}$ (fixed MVP demo threshold). Rejects two-node back-and-forth loops and single transaction reuse.
  - `location_time_overlap.py`: Detects spatio-temporal co-presence (`LOCATION_TIME_OVERLAP`) across distinct entities at the same normalized location within $|t_1 - t_2| \le 2\text{ hours}$ (fixed MVP demo threshold). Safely rejects records with missing location, missing timestamp, or identical entities.
  - *Pattern Schema Contract*: Emits `shared.schemas.Pattern` instances with `status=RelationshipStatus.INFERRED` (NEVER `DETECTED`, never coerced to `CONFIRMED`) and `severity` (`HIGH` for financial flow, `MEDIUM` for spatio-temporal overlap). Note that `Pattern` has `extra="forbid"` and no confidence field.
- **`ml/leads/`** (Phase 9):
  - `lead_generator.py`: Generates deterministic, explainable investigative leads (`Lead`) from Phase 8 pattern outputs and evidence. Maps `CIRCULAR_TRANSACTION` and `RAPID_TRANSFER_CHAIN` to `HIGH` priority leads, and `LOCATION_TIME_OVERLAP` to `MEDIUM` priority leads.
  - *Schema Adherence*: Emits `shared.schemas.Lead` instances with `priority` (`HIGH`, `MEDIUM`, `LOW`) and `status=LeadStatus.REVIEW_REQUIRED`. Strictly adheres to `extra="forbid"`: Lead contains NO `severity` field and NO `confidence` field.
  - *Investigative Safety*: Leads are objective, explainable recommendations for investigator review. ML never generates person-level criminal risk scores, guilt determinations, or automated accusations.
  - *Traceability & Boundary*: Preserves ML staging entity keys and source evidence record IDs without generating canonical PostgreSQL UUIDs or `case_id`. ML does not persist leads to databases.
- **`ml/validation/`** (Phase 11):
  - `output_validator.py`: Public validation interface for all contract models (`validate_extraction_result`, `validate_entity_mention`, `validate_relationship`, `validate_resolution_proposal`, `validate_pattern`, `validate_lead`) strictly enforcing the frozen Pydantic contracts in `shared.schemas`.
- **`ml/fixtures/`**: Test datasets, mock inputs, and sample payloads.
- **`ml/tests/`**: Unit and integration test suites for Person B modules (238 tests across Phases 1–11).

## Pipeline Invocation (Phase 10 Integration)

The primary entry point for intelligence orchestration is `ml.pipeline.process_document`:

```python
from ml.pipeline import process_document

# 1. Standard document analysis (returns ExtractionResult)
result = process_document("doc_001", "Vikram Sharma (+919876543210) called Amit Kumar in Mumbai.")
print(result.document_id)
print(result.entities)
print(result.relationships)

# 2. Combined document + structured records analysis (returns full intelligence bundle)
analysis = process_document(
    "doc_002",
    "FIR incident report text...",
    transactions=[...],
    cdrs=[...],
    return_full_analysis=True,
)
print(analysis["extraction_result"])     # Validated ExtractionResult
print(analysis["resolution_proposals"])  # Validated ResolutionProposal list
print(analysis["patterns"])              # Validated Pattern list
print(analysis["leads"])                 # Validated Lead list
```

## Schema Validation & Contract Testing (Phase 11)

All ML outputs are validated against the immutable frozen schemas in `shared.schemas/`:
1. **Frozen Schemas**: `shared/schemas/` is the single source of truth. Models reject extra fields (`extra="forbid"`), and enums are frozen (`DETECTED` is disallowed; Lead priority is strictly `LOW`/`MEDIUM`/`HIGH`).
2. **JSON Round-Trip Fidelity**: Every ML model supports lossless round-trip serialization:
   ```python
   # Pydantic v2 model -> JSON -> dict -> Contract Model
   json_str = result.model_dump_json()
   parsed_dict = json.loads(json_str)
   revalidated = ExtractionResult.model_validate(parsed_dict)
   ```
3. **No Database UUIDs / Case IDs**: Staging IDs (`mention_xxx`, `rel_xxx`) and proposal IDs (`canonical_xxx`) are preserved. Zero PostgreSQL UUIDs or `case_id`s are minted in `ml/`.

## AI & Multimodal Foundation & Pipeline Integration (Phases 1–9)

See [`ml/AI_FOUNDATION.md`](file:///c:/Users/MDFAIZAANRAZAKHAN/Downloads/CrimeLens/ml/AI_FOUNDATION.md) for full architectural specifications.
- **`ml/tests/test_final_integration_verification.py`** (Phase 9): Final integration verification suite verifying adapter discovery across candidate tuples (`ml.process`, `ml.pipeline`, `ml.extract`), 3 calling conventions, real end-to-end synthetic investigation orchestration, cold-start zero-credential import, and strict isolation from databases.
- **`ml/tests/test_failure_handling.py`** (Phase 8): Comprehensive failure handling, edge case, regression, and reliability test suite verifying provider failure isolation (503, 500, timeouts, rate limits, non-retryable 401s), malformed payload resilience, 10 required end-to-end operational scenarios, document boundaries (empty, minimal, multi-page, large text, mixed input), multi-threaded state safety, and secret sanitization.
- **`ml/validation/safety_firewall.py`** (Phase 7): Authoritative `SafetyFirewall` enforcing layered candidate validation, source grounding, status/confidence bounds, entity ID safety (staging IDs only, no database UUID minting), and structured rejection reason taxonomy (`ValidationRejectionReason`).
- **`ml/ai/response_parser.py`** (Phase 7): Safe `AIResponseParser` parsing untrusted model outputs, stripping chain-of-thought blocks (`<thought>`, `<reasoning>`, `thought`, `reasoning_content`), and extracting clean candidate payloads.
- **`ml/ai/pipeline_integration.py`** (Phase 6 & 7): `AIPipelineCoordinator` and `AITraceabilityMetrics` integrating AI document understanding, candidate extraction, and relationship reasoning directly into `process_document(...)` with strict failure isolation, deterministic fallbacks, structured facts protection, and safety firewall enforcement.
- **`ml/ai/evidence.py`** (Phase 5): `EvidenceGroundingEngine` validating and grounding candidate snippets against actual document text/pages, and `ProvenanceTracker` preserving verifiable multi-modal provenance chains without chain-of-thought storage.
- **`ml/ai/reasoning.py`** (Phase 4): `AIRelationshipReasoner` proposing contextual candidate relationships across multi-entity, cross-sentence, and cross-page context, validated by strict schema and evidence grounding, and `RelationshipReconciler` unifying deterministic edges with AI proposals.
- **`ml/ai/extraction.py`** (Phase 3): `AIEntityExtractor` proposing candidate mentions from document understanding context, guarded by hallucination defense and 7-entity taxonomy check, and `EntityReconciler` unifying deterministic mentions with AI candidates.
- **`ml/ai/router.py`** (Phase 2): `DocumentRouter` classifying inputs across modalities (`TEXT`, `IMAGE`, `PDF`, `STRUCTURED`).
- **`ml/ai/document_understanding.py`** (Phase 2): Format-agnostic `DocumentUnderstandingEngine` preserving pagination (`DocumentPage`), sections (`DocumentSection`), and tables (`DocumentTable`).
- **`ml/ai/types.py`** (Phase 1): Typed `MultimodalInput` (TEXT, IMAGE, PDF, STRUCTURED) and normalized `ModelResponse`.
- **`ml/ai/providers/base.py`** (Phase 1): Vendor-neutral `ReasoningModelProvider` abstract contract.
- **`ml/ai/providers/mock.py`** (Phase 1): Deterministic offline `MockReasoningProvider` with error simulations.
- **`ml/ai/client/client.py`** (Phase 1): Isolated `AIClient` enforcing bounded timeouts, bounded retries, context sanitization, and error tracking.
- **`ml/ai/errors.py`** (Phase 1): Normalized `AIError` hierarchy with automated credential/secret redaction.

## Running Tests

```bash
# Run full ML test suite (555 passed, 1 skipped)
python -m pytest ml/tests/

# Run Phase 9 Final Integration Verification suite (10 tests)
python -m unittest ml/tests/test_final_integration_verification.py

# Run Phase 8 Testing & Failure Handling suite (25 tests)
python -m unittest ml/tests/test_failure_handling.py

# Run Phase 7 Safety Firewall & Contract Compatibility suite (36 tests)
python -m unittest ml/tests/test_safety_firewall.py

# Run Phase 6 Pipeline Integration suite (18 tests)
python -m unittest ml/tests/test_pipeline_integration.py

# Run Phase 5 AI Evidence & Provenance suite (14 tests)
python -m unittest ml/tests/test_ai_evidence.py

# Run Phase 4 AI Context & Relationship Reasoning suite (16 tests)
python -m unittest ml/tests/test_ai_reasoning.py

# Run Phase 3 AI-Assisted Extraction suite (15 tests)
python -m unittest ml/tests/test_ai_extraction.py

# Run Phase 2 Multimodal Document Understanding suite (22 tests)
python -m unittest ml/tests/test_document_understanding.py

# Run Phase 1 AI foundation suite (28 tests)
python -m unittest ml/tests/test_ai_foundation.py

# Run shared schema contract validation (Person A contract test)
python -m unittest tests/test_ml_contract.py
```

