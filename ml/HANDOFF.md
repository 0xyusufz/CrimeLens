# ML HANDOFF — CrimeLens Intelligence Pipeline

**Phase 13 — Final Person B Handoff**  
**Status: READY FOR INTEGRATION**  
**Last verified:** 2026-09-14  
**Test result:** 545 passed, 1 skipped (OCR env), 0 failed

---

## 1. ML OWNER

**Person B** owns everything inside `ml/`.

Person A (backend) owns `backend/`, `shared/schemas/`, `tests/` (root), and `evidence_ledger/`.

---

## 2. ML ROOT

```
ml/
```

Person B has **never modified** any file outside `ml/`.

---

## 3. ENTRY POINT

```
Module:   ml.pipeline
Function: process_document(...)
```

Person A's backend adapter (`backend/app/ml/adapter.py`) already discovers this via:

```python
_PERSON_B_CANDIDATES = (
    ("ml.process",   "process_document"),
    ("ml.pipeline",  "process_document"),   # resolved here
    ("ml.extract",   "process_document"),
)
```

The function is live and importable.

---

## 4. INPUT CONTRACT

`process_document` accepts **three calling conventions**:

### Convention A — Backend adapter convention (preferred for Person A)
```python
process_document(document_bytes: bytes, filename: str, document_id: str)
```
- `document_bytes`: raw document bytes (UTF-8 text or image bytes)
- `filename`: original filename used to detect image/scanned files
- `document_id`: string UUID assigned by Person A's backend

### Convention B — Named keyword (used by ML tests)
```python
process_document(document_id="doc_001", text="raw text content")
```

### Convention C — Full intelligence bundle
```python
process_document(document_id="doc_001", text="...",
                 transactions=[...],
                 cdrs=[...],
                 return_full_analysis=True)
```

### Supplemental structured inputs (kwargs)

| kwarg | type | description |
|---|---|---|
| `transactions` | `list[dict]` | Financial transaction records |
| `cdrs` | `list[dict]` | Call Detail Records |
| `return_full_analysis` | `bool` | Returns full dict if True |

### Transaction dict schema
```python
{
  "sender":           str,   # required
  "recipient":        str,   # required
  "amount":           float, # required
  "currency":         str,   # required
  "transaction_time": str,   # required — ISO 8601
  "record_id":        str,   # optional but recommended
  "location":         str,   # optional
}
```

### CDR dict schema
```python
{
  "caller":    str,  # required
  "callee":    str,  # required
  "call_time": str,  # required — ISO 8601
  "duration":  int,  # optional — seconds
  "location":  str,  # optional
  "record_id": str,  # optional but recommended
}
```

---

## 5. OUTPUT CONTRACT

### Default return (Convention A & B)
```python
ExtractionResult           # shared.schemas.models.ExtractionResult
    document_id: str       # echoes the input document_id
    entities: list[EntityMention]
    relationships: list[Relationship]
```

### Full analysis return (return_full_analysis=True)
```python
{
  "document_id":          str,
  "extraction_result":    ExtractionResult,
  "entities":             list[EntityMention],
  "relationships":        list[Relationship],
  "resolution_proposals": list[ResolutionProposal],
  "patterns":             list[Pattern],
  "leads":                list[Lead],
  "structured_records":   list[TransactionRecord | CDRRecord],
}
```

### EntityMention
```python
{
  "id":         "mention_001",   # ML staging ID — NOT a DB UUID
  "type":       "PERSON"|"PHONE"|"BANK_ACCOUNT"|"VEHICLE"|"ORGANIZATION"|"LOCATION"|"EVENT",
  "name":       str,
  "confidence": float            # 0.0 to 1.0
}
```

### Relationship
```python
{
  "id":                 "rel_001",
  "source_entity_id":  "mention_001",
  "relationship":       RelationshipType,
  "target_entity_id":  "mention_002",
  "confidence":         float,
  "status":             "INFERRED"|"PREDICTED",  # NEVER "DETECTED"
  "source_document_id": str | None,
  "source_record_id":   str | None,
  "evidence_snippet":   str,
  "extracted_at":       datetime
}
```

### ResolutionProposal
```python
{
  "canonical_entity_id": "entity_001",  # ML grouping key — NOT a DB UUID
  "mention_id":          "mention_002",
  "confidence":           float,
  "signals":             list[ResolutionSignal]
}
```

### Pattern
```python
{
  "id":           "pattern_001",
  "type":         "CIRCULAR_TRANSACTION"|"RAPID_TRANSFER_CHAIN"|"LOCATION_TIME_OVERLAP",
  "severity":     "LOW"|"MEDIUM"|"HIGH",
  "status":       "INFERRED",       # always INFERRED, never DETECTED
  "entities":     list[str],
  "explanation":  str,
  "evidence_ids": list[str]         # source record_id values
}
```

### Lead
```python
{
  "id":             "lead_001",
  "type":           LeadType,
  "priority":       "LOW"|"MEDIUM"|"HIGH",
  "status":         "REVIEW_REQUIRED",   # always; never DETECTED
  "title":          str,
  "explanation":    str,
  "entity_ids":     list[str],
  "evidence_ids":   list[str],
  "priority_score": float | None         # 0.0-1.0; NOT a criminal risk score
}
```

NOTE: Lead has no `severity` field and no `confidence` field.

---

## 6. PROCESSING FLOW

```
Input (document bytes / text / structured records)
  |
  v
Phase 2 — Preprocessing (ml/preprocessing/)
  |   normalize_text(), load_document()
  |
  v
Phase 3 — OCR (ml/ocr/)   [skipped for plain text; active for image/PDF]
  |   extract_text_from_image() via Tesseract
  |
  v
Phase 4 — Entity Extraction (ml/extraction/)
  |   extract_entities() -> list[EntityMention]
  |   Regex + deterministic NER patterns
  |
  v
Phase 7 — Structured Ingestion (ml/structured/)
  |   parse_transaction(), parse_cdr()
  |   Auto-creates EntityMention stubs for structured participants
  |
  v
Phase 5 — Relationship Extraction (ml/relationships/)
  |   extract_relationships() -> list[Relationship]
  |
  v
Phase 6 — Entity Resolution Proposals (ml/resolution/)
  |   propose_resolutions() -> list[ResolutionProposal]
  |   Strong-signal only; name-only fuzzy never auto-merges
  |
  v
Phase 8 — Pattern Detection (ml/patterns/)
  |   detect_circular_transactions()   [30-day window]
  |   detect_rapid_transfers()         [48-hour window]
  |   detect_location_time_overlaps()  [2-hour window]
  |
  v
Phase 9 — Lead Generation (ml/leads/)
  |   generate_leads() -> list[Lead]
  |
  v
Phase 11 — Contract Validation (ml/validation/)
  |   validate_extraction_result(), validate_pattern(), validate_lead(), etc.
  |
  v
ExtractionResult  (+full dict if return_full_analysis=True)
```

---

## 7. IDENTIFIER SEMANTICS

| Identifier | Owner | Example | Meaning |
|---|---|---|---|
| `mention_001` | ML (Person B) | entity.id | Staging mention ID for one document occurrence |
| `rel_001` | ML (Person B) | relationship.id | Staging relationship occurrence ID |
| `entity_001` | ML (Person B) | resolution_proposal.canonical_entity_id | ML grouping key — NOT a DB UUID |
| `pattern_001` | ML (Person B) | pattern.id | Staging pattern ID |
| `lead_001` | ML (Person B) | lead.id | Staging lead ID |
| PostgreSQL UUID | Backend (Person A) | document.id in DB | Canonical database identity |
| Neo4j internal ID | Backend (Person A) | graph node identity | Never generated by ML |
| `case_id` | Backend (Person A) | FK on document/entity | Never generated by ML |

ML IDs are NOT database UUIDs. They are staging-only references valid for one pipeline run.
Person A must map ML mention IDs to canonical PostgreSQL UUIDs during persistence.

---

## 8. BACKEND INTEGRATION BOUNDARY

ML ends at structured JSON output. Person A's backend does:

```
1. Receive document via FastAPI endpoint         [Person A owns]
2. Assign document_id (PostgreSQL UUID)          [Person A owns]
3. Call process_document(bytes, filename, str(document_id))   [ML boundary]
4. Receive ExtractionResult                      [ML delivers]
5. Persist entities -> PostgreSQL                [Person A owns]
6. Persist relationships -> PostgreSQL           [Person A owns]
7. Write Neo4j graph from persisted UUIDs        [Person A owns]
8. Store resolution proposals for review         [Person A owns]
9. Store patterns as intelligence signals        [Person A owns]
10. Store leads for investigator queue           [Person A owns]
```

Person A's `backend/app/ml/adapter.py` (`run_document_processor`) already
implements this call boundary correctly.

---

## 9. DATABASE BOUNDARY

```
ML  ->  NO PostgreSQL access
ML  ->  NO Neo4j access
ML  ->  NO Redis / Kafka / any external store

ML produces structured JSON only.
All persistence is Person A's responsibility.
```

---

## 10. TEST COMMAND

```bash
# From project root (CrimeLens/):
python -m pytest ml/tests/ -v
```

---

## 11. TEST STATUS (verified 2026-09-14)

| Suite | Phase | Tests | Passed | Skipped | Failed |
|---|---|---|---|---|---|
| test_foundation.py | 1 | 11 | 11 | 0 | 0 |
| test_preprocessing.py | 2 | 16 | 16 | 0 | 0 |
| test_ocr.py | 3 | 12 | 11 | 1* | 0 |
| test_extraction.py | 4 | 18 | 18 | 0 | 0 |
| test_relationships.py | 5 | 25 | 25 | 0 | 0 |
| test_resolution.py | 6 | 27 | 27 | 0 | 0 |
| test_structured.py | 7 | 46 | 46 | 0 | 0 |
| test_patterns.py | 8 | 40 | 40 | 0 | 0 |
| test_leads.py | 9 | 30 | 30 | 0 | 0 |
| test_pipeline.py | 10 | 23 | 23 | 0 | 0 |
| test_contract_validation.py | 11 | 72 | 72 | 0 | 0 |
| test_synthetic_evaluation.py | 12 | 134 | 133 | 1* | 0 |
| **TOTAL** | **1-12** | **372** | **371** | **1** | **0** |

* OCR skip: pytesseract not installed in this dev environment.
  The OCR module (ml/ocr/tesseract.py) is fully implemented.
  Install tesseract + pytesseract to activate OCR tests.

---

## 12. KNOWN LIMITATIONS

| # | Limitation | Classification | Impact |
|---|---|---|---|
| 1 | pytesseract not installed in dev environment | Environment | OCR test skipped; code complete |
| 2 | Regex NER does not capture all phone formats from raw text | Scope | Structured CDR ingestion captures phones from records |
| 3 | Location NER matches keyword patterns, not arbitrary text | Scope | CDR/transaction location fields used for overlap detection |
| 4 | Pattern thresholds (30d/48h/2h) are fixed MVP rules | Design | Not criminality thresholds; for investigative triage only |
| 5 | Resolution requires min confidence 0.70 | Design | Name-only fuzzy matching intentionally suppressed |

---

## 13. PATTERN THRESHOLDS (frozen MVP values)

| Pattern | Threshold | Semantics |
|---|---|---|
| CIRCULAR_TRANSACTION | 30 days | max(ts) - min(ts) <= 30 days in 3-node cycle |
| RAPID_TRANSFER_CHAIN | 48 hours | t2 - t1 <= 48 hours, t2 >= t1 in chain |
| LOCATION_TIME_OVERLAP | 2 hours | abs(t1 - t2) <= 2 hours, same normalized location |

These are deterministic investigation-support thresholds.
They are NOT criminal probability scores.

---

## 14. NO ML API

Person B has NOT created any HTTP endpoint.
No /ml/process, /ml/predict, /api/ml, /predict, /extract.
No Flask, FastAPI, or Uvicorn process inside ml/.
Integration is a Python-level import, not a network call.

---

## 15. NEXT ACTION FOR PERSON A

Person A's backend/app/ml/adapter.py already has run_document_processor().

To complete integration:
1. Ensure ml/ is on Python path (project root in PYTHONPATH).
2. load_person_b_process_document() auto-discovers ml.pipeline.process_document.
3. Pass (document_bytes, filename, str(document.id)) — Convention A.
4. run_document_processor() validates ExtractionResult and verifies document_id.
5. Persist the validated result using Person A's PostgreSQL schema.

No changes to ml/ are required.

---

## 16. AI FOUNDATION, PIPELINE INTEGRATION, VALIDATION FIREWALL & FAILURE HANDLING (PHASES 1–8)

- **Phase 1**: Model-agnostic AI provider foundation (`ml/ai/providers/`, `ml/ai/client/`, `ml/ai/types.py`, `ml/ai/errors.py`). Isolated client with bounded retries, bounded timeouts, and automated credential redaction.
- **Phase 2**: Multimodal document understanding (`ml/ai/router.py`, `ml/ai/document_understanding.py`). Format-agnostic representation preserving pagination (`DocumentPage`), sections (`DocumentSection`), and tables (`DocumentTable`).
- **Phase 3**: AI-assisted entity and information extraction (`ml/ai/extraction.py`). Candidates grounded in source text, validated against 7 frozen entity categories, and reconciled via `EntityReconciler`.
- **Phase 4**: AI context and relationship reasoning (`ml/ai/reasoning.py`). Contextual multi-entity reasoning with evidence validation, direction preservation, rejection of unsupported relationships, and reconciliation via `RelationshipReconciler`.
- **Phase 5**: AI evidence and provenance (`ml/ai/evidence.py`). Evidence grounding engine verifying snippets and page bounds, rejecting semantic alterations, and tracking multimodal provenance chains without chain-of-thought storage.
- **Phase 6**: Existing ML + AI Pipeline Integration (`ml/ai/pipeline_integration.py`, `ml/pipeline.py`). Single coordinated orchestration (`AIPipelineCoordinator`) integrating multimodal understanding, entity candidate reconciliation, relationship reasoning, and provenance attachment into `process_document(...)`.
- **Phase 7**: Validation, Safety & Contract Compatibility (`ml/validation/safety_firewall.py`, `ml/ai/response_parser.py`):
  - **Validation Firewall**: `SafetyFirewall` validates every AI candidate before reconciliation; enforces frozen entity taxonomy (7 types) and relationship taxonomy (8 types); rejects invalid statuses, invalid confidences, and fabricated page/snippet references.
  - **AI Trust Model**: AI output is ALWAYS untrusted input. The validation layer is authoritative over AI output.
  - **Evidence Grounding**: Candidate mentions and relationships must be grounded in source text; tolerates legitimate OCR whitespace/spacing; rejects fabricated snippets and out-of-bounds pages.
  - **Entity ID Safety**: AI is strictly forbidden from minting canonical database UUIDs; enforces staging IDs (`mention_xxx`).
  - **Merge Safety**: Rejects name-only auto-merging; respects resolver's strong identifier policy.
  - **Structured Facts Authority**: Structured CDR and transaction fields (amounts, currencies, durations, timestamps) are immutable and cannot be altered by AI conjecture.
  - **Anti-Criminality & Anti-Guilt Firewall**: Rejects direct assertions of guilt, criminality, or predictive policing scores.
  - **Chain-of-Thought Firewall**: Internal model thoughts and reasoning blocks are stripped by `AIResponseParser` and never persisted or exposed.
  - **Prompt Injection Defense**: Document instructions are treated strictly as passive data, never system commands.
  - **Output Schema & Serialization**: Guarantees final `ExtractionResult` conforms to frozen Pydantic contracts and is cleanly JSON-serializable.
- **Phase 8**: Testing & Failure Handling (`ml/tests/test_failure_handling.py`):
  - **Provider Failure Isolation**: Comprehensive coverage of 503, 500, timeouts, and rate limits with verified fallback to deterministic extraction. Verified non-retryable 401 authentication errors that fail immediately without wasting retry cycles.
  - **Malformed Payload Resilience**: Corrupt JSON strings, non-dict payloads, unexpected nested types, and reasoning block extraction resilience.
  - **10 Required Operational Scenarios**: Full coverage of all 10 scenarios mandated in Section 61 (deterministic normal, valid AI, malformed AI, provider timeout, hallucinated evidence, duplicate relationship reconciliation, conflicting transaction value, prompt injection, multi-page document provenance, AI disabled parity).
  - **Document Boundary Edge Cases**: Empty string documents (`text=""`) produce valid empty `ExtractionResult` without crashing; minimal single-sentence text, large multi-paragraph text, and mixed inputs (text + transactions + CDRs) processed safely.
  - **Thread-Safe & Concurrency Safety**: Verified concurrent multi-threaded calls to `process_document()` produce completely isolated, uncorrupted results with zero shared mutable state.
  - **Deterministic Reproducibility**: Identical inputs with mock yield identical results.
  - **Security & Secret Sanitization**: Zero API keys or secrets leak into output models, metrics, or error logs.
- **Failure Safety**: If the external AI provider is disabled, times out, rate limits, or errors, CrimeLens ML gracefully falls back to deterministic extraction and rules.
- **Strict Boundary**: Zero database queries, zero Neo4j mutations, zero UUID generation. All relationships and mentions remain in ML staging format (`mention_xxx`, `rel_xxx`) for Person A backend persistence.

---

## HANDOFF CHECKLIST

- [x] ML entry point identified: ml.pipeline.process_document
- [x] Input contract documented: 3 calling conventions
- [x] Output contract documented: ExtractionResult + full dict
- [x] Schema validated: all 6 model types pass model_validate
- [x] JSON serialization verified: json.dumps + re-validation round-trip
- [x] Synthetic smoke test passed: 15/15 end-to-end tests pass
- [x] Full ML tests passed: 545/546 (1 OCR env skip, 0 failures)
- [x] Phase 8 failure handling suite passed: 25/25 tests in test_failure_handling.py
- [x] Phase 7 safety firewall suite passed: 36/36 tests in test_safety_firewall.py
- [x] Phase 6 integration suite passed: 18/18 tests in test_pipeline_integration.py
- [x] Backend contract tests passed: 13/13 in tests/test_ml_contract.py
- [x] Pattern output verified: CIRCULAR / RAPID / OVERLAP confirmed
- [x] Lead output verified: REVIEW_REQUIRED, no severity, no criminal score
- [x] Evidence traceability verified: evidence_ids map to source record_id values
- [x] ID semantics documented: mention_xxx / rel_xxx are staging-only
- [x] case_id ownership documented: Backend (Person A) only
- [x] DB UUID ownership documented: Backend (Person A) only
- [x] No ML database access: confirmed
- [x] No ML API introduced: confirmed
- [x] Backend boundary documented: ML ends at structured JSON
- [x] Known limitations documented: 5 items
- [x] No commit/push: awaiting user decision
