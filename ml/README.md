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
  - *Boundary*: Preprocessing does NOT perform OCR, entity extraction, or summarization. In Phase 3, OCR will extract raw text from image files, which will then be passed directly into this normalizer.
- **`ml/ocr/`**:
  - `tesseract.py`: Optical character recognition interface for image/scanned inputs.
- **`ml/extraction/`**:
  - `ner.py`: Named entity recognition (`PERSON`, `LOCATION`, `ORGANIZATION`).
  - `regex.py`: Regular expression extractors (`PHONE`, `BANK_ACCOUNT`, `VEHICLE`).
  - `entity_extractor.py`: Unified entity extraction coordinator.
- **`ml/relationships/`**:
  - `rule_extractor.py`: Rule- and pattern-based relationship extraction (`CALLED`, `SENT_MONEY_TO`, etc.) with required provenance and evidence snippets.
- **`ml/resolution/`**:
  - `resolver.py`: Generates `ResolutionProposal` instances with signals (e.g., `phone_match`, `name_similarity`) for backend evaluation.
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
