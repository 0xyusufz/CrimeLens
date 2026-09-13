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
- **`ml/patterns/`**:
  - `circular_transaction.py`: Detects cyclic money flow (`CIRCULAR_TRANSACTION`).
  - `rapid_transfer.py`: Detects rapid pass-through / layering chains (`RAPID_TRANSFER_CHAIN`).
  - `location_time_overlap.py`: Detects co-location within spatio-temporal windows (`LOCATION_TIME_OVERLAP`).
- **`ml/validation/`**:
  - `output_validator.py`: Validates all outgoing envelopes against the frozen schemas in `shared.schemas`.
- **`ml/fixtures/`**: Test datasets, mock inputs, and sample payloads.
- **`ml/tests/`**: Unit and integration test suites for Person B modules.

## Running Tests

```bash
# Using project backend virtualenv
.\backend\.venv\Scripts\python -m unittest discover -s ml/tests
```
