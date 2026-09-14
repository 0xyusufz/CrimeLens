# CrimeLens ML: Phase 1 — Model-Agnostic AI & Multimodal Foundation

This document establishes the architecture, boundaries, contracts, and security rules for the CrimeLens AI and Multimodal Reasoning layer (`ml/ai/`).

---

## 1. Executive Summary & Integration Boundary

The CrimeLens AI foundation establishes a vendor-neutral, isolated abstraction for integrating future reasoning models (LLMs) and multimodal vision models without modifying or destabilizing the existing deterministic ML pipeline or the Person A backend contract.

```
Existing Document / Image / PDF / Structured Record
                      │
                      ▼
             ml.pipeline.process_document(...)
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
Existing Deterministic ML     Future AI / Multimodal Layer (`ml/ai/`)
(Regex, Rules, Parsers,        (Isolated Provider Abstraction,
Patterns, Leads, Handoff)      Untrusted Candidate Proposals)
        ▲                           │
        └─────────────┬─────────────┘
                      │ (Validation & Structuring)
                      ▼
             ExtractionResult (Shared Schema)
                      │
                      ▼
           Person A FastAPI Backend
    POST /api/documents/{document_id}/process
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
      PostgreSQL 16          Neo4j 5
     (Source of Truth)    (Derived Graph)
```

### Immutable Project Contracts
- **Existing Backend Endpoint:** `POST /api/documents/{document_id}/process`
- **Existing ML Entry Point:** `ml.pipeline.process_document(...)`
- **Phase 1 New HTTP Endpoints:** **NONE** (Zero new endpoints)
- **Backend Files Modified:** **NONE** (Zero backend changes)
- **Database Changes:** **NONE** (Zero PostgreSQL migrations or queries)
- **Neo4j Changes:** **NONE** (Zero graph mutations)
- **Shared Schema Changes:** **NONE** (`shared/schemas/` remains untouched)

---

## 2. Core Architectural Principles

1. **AI Proposes; CrimeLens ML Validates and Structures**:
   External models are strictly **UNTRUSTED**. Models may hallucinate, output unsupported types, or invent relationships. Model outputs are parsed, sanitized, validated, and normalized before any data can enter the CrimeLens pipeline.
2. **Vendor-Neutral Provider Abstraction**:
   No hard-coding or locking to Gemini, OpenAI, Claude, or any specific vendor. The provider interface (`ReasoningModelProvider`) is completely decoupled and swappable via configuration.
3. **Strict Isolation & Zero Database Access**:
   The AI layer has zero direct connection to PostgreSQL, Neo4j, or FastAPI. It does not mint persistent database UUIDs, does not generate `case_id`, and does not perform persistent storage.
4. **Non-Negotiable Secret Protection**:
   API keys and tokens are never committed, logged, serialized, or exposed in exception messages or reprs. Redaction masks all credentials (`***REDACTED***`).
5. **Deterministic Default**:
   If AI is disabled (`ai_enabled: False`), the existing deterministic ML pipeline operates unchanged without network or external model dependencies.

---

## 3. Package Structure (`ml/ai/`)

```
ml/ai/
├── __init__.py            # Re-exports types, providers, client, and factory
├── errors.py              # Normalized AI error hierarchy with secret redaction
├── types.py               # MultimodalInput and ModelResponse representations
├── providers/
│   ├── __init__.py        # Re-exports provider abstractions
│   ├── base.py            # Vendor-neutral ReasoningModelProvider (ABC)
│   └── mock.py            # Deterministic, offline MockReasoningProvider
└── client/
    ├── __init__.py        # Re-exports AIClient
    └── client.py          # AIClient with bounded timeouts, retries, and isolation
```

---

## 4. Component Details

### 4.1 Multimodal Input Representation (`ml.ai.types.MultimodalInput`)
Supports multimodal ingestion across four categories:
- `InputType.TEXT`: Plain text, transcripts, FIR text.
- `InputType.IMAGE`: Scanned documents, scene photos, seized memos (`bytes`, MIME type).
- `InputType.PDF`: Multi-page PDFs (`bytes`, MIME type, pre-extracted text).
- `InputType.STRUCTURED`: Tabular records, CDRs, banking transactions (serialized JSON, record counts).

Factory constructors:
- `MultimodalInput.from_text(text, filename=..., metadata=...)`
- `MultimodalInput.from_image(data, mime_type=..., filename=..., metadata=...)`
- `MultimodalInput.from_pdf(data, filename=..., extracted_text=..., metadata=...)`
- `MultimodalInput.from_structured(records, filename=..., metadata=...)`
- `MultimodalInput.from_bytes(data, input_type, mime_type=..., filename=..., metadata=...)`

### 4.2 Normalized Model Response (`ml.ai.types.ModelResponse`)
Encapsulates candidate intelligence without bypassing schema contracts:
- `provider_name: str`
- `model_name: str`
- `raw_content: Optional[str]`
- `structured_payload: dict[str, Any]`
- `usage_tokens: Optional[dict[str, int]]`
- `latency_ms: float`
- `metadata: dict[str, Any]`

Candidate getters:
- `get_candidate_entities() -> list[dict]`
- `get_candidate_relationships() -> list[dict]`
- `get_candidate_patterns() -> list[dict]`
- `get_candidate_leads() -> list[dict]`

### 4.3 Provider Abstraction (`ml.ai.providers.ReasoningModelProvider`)
Abstract base class defining the provider boundary:
```python
class ReasoningModelProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    def is_available(self) -> bool: ...

    @abstractmethod
    def analyze(self, input_data: MultimodalInput, *, context: Optional[dict] = None) -> ModelResponse: ...

    def health_check(self) -> bool: ...
```

### 4.4 Deterministic Mock Provider (`ml.ai.providers.MockReasoningProvider`)
- **Zero Network**: Operates 100% offline without API keys or vendor SDKs.
- **Deterministic**: Produces identical hash-based candidate outputs for identical inputs.
- **Error Simulation**: Configurable flags (`simulate_timeout`, `simulate_rate_limit`, `simulate_auth_failure`, `simulate_unavailable`, `simulate_malformed`, `simulate_execution_error`) allow testing all failure edge cases.

### 4.5 Client Boundary (`ml.ai.client.AIClient`)
- **Bounded Timeout**: Configurable max execution duration (`timeout_seconds`, default 30.0s).
- **Bounded Retry**: Retries only transient failures (`AITimeoutError`, `AIRateLimitError`) up to `max_retries` (default 2). Never retries non-transient errors (`AIAuthenticationError`, `AIUnsupportedInputError`, `AIConfigurationError`).
- **Context Sanitization**: Automatically strips keys containing `token`, `password`, `key`, `secret`, `session`, `db` before forwarding context to providers.
- **Payload Size Guards**: Verifies input byte size against `max_input_bytes` (default 25 MB) prior to remote dispatch.

### 4.6 Normalized Error Hierarchy (`ml.ai.errors.AIError`)
All errors scrub API keys and sensitive tokens before formatting:
- `AIProviderUnavailableError`: Provider offline or unregistered.
- `AIConfigurationError`: Missing or invalid configuration.
- `AIAuthenticationError`: Credentials rejected (401/403).
- `AITimeoutError`: Request exceeded bounded timeout.
- `AIRateLimitError`: Quota or rate limit exceeded (429).
- `AIMalformedResponseError`: Invalid or unparseable response JSON.
- `AIUnsupportedInputError`: Empty, malformed, or oversized payload.
- `AIExecutionError`: Unexpected third-party runtime failure.

---

## 5. Configuration & Environment Variables

All AI configuration is encapsulated in `ml.config.MLConfig`:
```python
@dataclass(frozen=True)
class MLConfig:
    # Existing ML parameters
    min_entity_confidence: float = 0.5
    min_relationship_confidence: float = 0.5
    min_resolution_confidence: float = 0.7
    max_document_length_chars: int = 1_000_000
    default_ocr_language: str = "eng"

    # AI / Multimodal reasoning parameters (Phase 1)
    ai_enabled: bool = False
    ai_provider: str = "mock"
    ai_model: str = "mock-reasoner-v1"
    ai_api_key: Optional[str] = None
    ai_timeout_seconds: float = 30.0
    ai_max_retries: int = 2
    ai_max_input_bytes: int = 25_000_000
```

`MLConfig.__repr__` automatically masks `ai_api_key` as `"***REDACTED***"`.

Expected runtime environment variables (documented for reference, not committed to `.env`):
- `CRIMELENS_AI_ENABLED`: `"true"` | `"false"` (default: `"false"`)
- `CRIMELENS_AI_PROVIDER`: `"mock"` | `"gemini"` | `"openai"` (default: `"mock"`)
- `CRIMELENS_AI_MODEL`: Model identifier string (default: `"mock-reasoner-v1"`)
- `CRIMELENS_AI_API_KEY`: Model provider secret (server-side only, never passed to frontend)
- `CRIMELENS_AI_TIMEOUT`: Seconds (default: `30.0`)
- `CRIMELENS_AI_MAX_RETRIES`: Integer count (default: `2`)

---

## 6. Verification & Test Coverage

- Phase 1 Test Suite: `ml/tests/test_ai_foundation.py` (28 unit tests)
- Phase 2 Test Suite: `ml/tests/test_document_understanding.py` (22 unit tests)
- Phase 3 Test Suite: `ml/tests/test_ai_extraction.py` (15 unit tests)
- Phase 4 Test Suite: `ml/tests/test_ai_reasoning.py` (16 unit tests)
- Phase 5 Test Suite: `ml/tests/test_ai_evidence.py` (14 unit tests)
- Total ML test suite: **466 passed, 1 skipped** (Tesseract OCR skipped when binary is absent).
- All 13 contract tests in `tests/test_ml_contract.py` pass 100%.

---

## 7. Phase 2 — Multimodal Document Understanding

Phase 2 builds a format-agnostic, multimodal document-understanding layer on top of Phase 1:

### 7.1 Input Routing (`ml.ai.router.DocumentRouter`)
Classifies inputs into distinct modalities:
- `DocumentModality.TEXT`: Raw strings, `.txt`, `.md`.
- `DocumentModality.IMAGE`: Image bytes, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`. Flags `is_scanned=True, requires_ocr=True`.
- `DocumentModality.PDF`: Native PDF (with text streams) vs. Scanned PDF (requires OCR).
- `DocumentModality.STRUCTURED`: JSON or CSV records routed to deterministic parsers.

### 7.2 Format-Agnostic Understanding Model (`ml.ai.document_understanding.DocumentUnderstanding`)
- **Pagination**: `DocumentPage` preserves page numbers and page-level slices without collapsing text.
- **Sections**: `DocumentSection` identifies semantic categories (`HEADING`, `METADATA`, `NARRATIVE`, `STATEMENT`, `INCIDENT_DESCRIPTION`, `FINANCIAL_RECORD`, `COMMUNICATION_RECORD`, `SEIZURE_RECORD`, `TABLE`).
- **Tables**: `DocumentTable` extracts headers and rows from tabular data.
- **Classification**: Infers document category (`POLICE_REPORT`, `FINANCIAL_STATEMENT`, `CALL_DETAIL_RECORD`, `WITNESS_STATEMENT`, `SEIZURE_MEMO`, `LEGAL_NOTICE`, `GENERIC_DOCUMENT`) without assuming a fixed FIR format.
- **Safety**: Never invents missing data; never generates guilt, criminal scores, or accusations.

### 7.3 Integration & Frozen Contracts
- **HTTP Endpoints Added in Phase 2:** **NONE**
- **Existing Backend Processing Endpoint:** `POST /api/documents/{document_id}/process`
- **Existing ML Entry Point:** `ml.pipeline.process_document(...)`
- **Backend Files Modified:** **NONE**
- **Shared Schemas Modified:** **NONE**
- **Database Modified:** **NONE**
- **Neo4j Modified:** **NONE**

---

## 8. Phase 3 — AI-Assisted Entity & Information Extraction

Phase 3 introduces AI-assisted candidate entity and information extraction on top of Phase 1 (AI provider foundation) and Phase 2 (Multimodal Document Understanding):

### 8.1 Architecture & Untrusted Candidate Principle
AI output is strictly treated as **UNTRUSTED CANDIDATE INTELLIGENCE**. It is never directly persisted or promoted to final intelligence without going through deterministic validation, normalization, and reconciliation.

```
Document Understanding (Phase 2)
              │
              ├──────────────────────────────────┐
              ▼                                  ▼
Deterministic Extraction               AI Candidate Extractor
(Regex & Rule NER)                     (`AIEntityExtractor`)
              │                                  │
              │                                  ▼
              │                        Hallucination Defense
              │                        - Source Grounding Check
              │                        - 7-Entity Taxonomy Enforced
              │                        - Bounded Confidence (0 <= c <= 1)
              │                        - Evidence Snippet & Page Preservation
              │                                  │
              └────────────────┬─────────────────┘
                               ▼
                    Candidate Reconciliation
                     (`EntityReconciler`)
                               │
                               ▼
                     Canonical Normalization
                               │
                               ▼
                   Staging EntityMention List
                  (mention_001, mention_002, ...)
                               │
                               ▼
             Subsequent Pipeline Stages (Validation)
```

### 8.2 Supported Entity Taxonomy
Restricted exclusively to CrimeLens's 7 frozen entity categories (`shared/schemas/enums.py`):
- `PERSON`
- `ORGANIZATION`
- `PHONE`
- `BANK_ACCOUNT`
- `VEHICLE`
- `LOCATION`
- `EVENT`

Unsupported types (e.g. `CRIMINAL`, `SUSPECT`, `GANG_MEMBER`, `THREAT_LEVEL`, `RISK_SCORE`) are strictly rejected.

### 8.3 Hallucination Defense & Source Grounding
- **Grounding Verification**: Candidates proposed by AI must have direct token or normalized presence in the underlying document context. Ungrounded entities are dropped.
- **Evidence Snippets**: Real text snippets surrounding the mention are captured directly from the document. No fake evidence is synthesized.
- **Page Context**: Page numbers are preserved or mapped to the respective `DocumentPage`.

### 8.4 Deterministic + AI Reconciliation (`EntityReconciler`)
- **Consensus Reinforcement**: When both deterministic rules and AI identify the same entity, the mention is deduplicated and confidence is reinforced.
- **Non-Destructive Overwrites**: Distinct entities found by deterministic extraction are never overwritten by AI candidates.
- **Contextual Discovery**: Valid contextual mentions discovered by AI that deterministic rules missed are incorporated as schema-compliant `EntityMention` objects.
- **Safe ID Generation**: Sequential staging IDs (`mention_001`, `mention_002`, ...) are assigned. Zero database UUIDs or case IDs are minted.

### 8.5 Frozen Backend Contracts (Phase 3)
- **HTTP Endpoints Added:** **NONE** (Zero new endpoints)
- **Existing Backend Endpoint:** `POST /api/documents/{document_id}/process` (UNCHANGED)
- **Existing ML Entry Point:** `ml.pipeline.process_document(...)` (COMPATIBLE)
- **Backend Modifications:** **NONE**
- **Shared Schemas Modifications:** **NONE**
- **Database Modifications:** **NONE**
- **Neo4j Modifications:** **NONE**

---

## 9. Phase 4 — AI Context & Relationship Reasoning

Phase 4 adds contextual relationship reasoning on top of multimodal document understanding (Phase 2), extracted entity mentions (Phase 3), deterministic relationship extraction, and structured records:

### 9.1 Conceptual Pipeline & Boundary
AI reasoning proposes candidate relationships across already-extracted entities based on multi-sentence, cross-page, and tabular context. It never bypasses deterministic validation or mints database IDs.

```
Document Understanding (Phase 2) + Extracted Entities (Phase 3)
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
Deterministic Rule Extraction       AI Contextual Reasoner
 (Intra-sentence triggers)          (`AIRelationshipReasoner`)
               │                             │
               │                             ▼
               │                    Firewall & Validation
               │                    - 8 Frozen Relationship Types
               │                    - Entity Reference Verification
               │                    - Directionality Preservation
               │                    - Real Evidence Grounding Check
               │                    - Page Boundary Verification
               │                             │
               └──────────────┬──────────────┘
                              ▼
                 Relationship Reconciler
                (`RelationshipReconciler`)
                              │
                              ▼
                   Unified Relationship List
                   (rel_001, rel_002, ...)
                              │
                              ▼
               Resolution, Patterns, Leads, Validation
```

### 9.2 Frozen Relationship Vocabulary
Only the 8 frozen relationship types in `shared/schemas/enums.py` are accepted:
- `CALLED`
- `SENT_MONEY_TO`
- `OWNS_VEHICLE`
- `USED_VEHICLE`
- `WORKS_FOR`
- `LOCATED_AT`
- `ASSOCIATED_WITH`
- `PART_OF_EVENT`

Unsupported types (e.g. `FRIEND_OF`, `KNOWS`, `LIKELY_GUILTY`, `CRIMINAL_ASSOCIATE`) are strictly rejected.

### 9.3 Safety, Status & Evidence Grounding
- **Allowed Statuses**: Only `CONFIRMED`, `INFERRED`, `PREDICTED`. `AI_DETECTED` is disallowed.
- **Evidence Verification**: Every candidate requires an evidence snippet grounded in the source text. Snippets that do not match the text or fabricate page numbers are dropped.
- **No Self-Relationships**: Disallows self-referential edges (`mention_001 -> mention_001`).
- **Directionality**: Preserves directional relationships (e.g. sender -> recipient; caller -> callee).
- **Anti-Hallucination & Anti-Guilt**: No criminal risk scores, guilt assessments, or predictive policing outputs.

### 9.4 Reconciliation Rules (`RelationshipReconciler`)
- **Deterministic Supremacy**: Deterministic relationships are authoritative and never overwritten by AI proposals.
- **Consensus Reinforcement**: When deterministic and AI extract the same edge, evidence is preserved and confidence is reinforced without duplicate edge creation.
- **Discovery**: Valid contextual edges discovered across sections or pages are safely appended with staging IDs (`rel_001`, `rel_002`, ...).

### 9.5 Frozen Backend Contracts (Phase 4)
- **HTTP Endpoints Added:** **NONE**
- **Existing Backend Endpoint:** `POST /api/documents/{document_id}/process` (UNCHANGED)
- **Existing ML Entry Point:** `ml.pipeline.process_document(...)` (COMPATIBLE)
- **Backend Modifications:** **NONE**
- **Shared Schemas Modifications:** **NONE**
- **Database Modifications:** **NONE**
- **Neo4j Modifications:** **NONE**

---

## 10. Phase 5 — AI Evidence & Provenance

Phase 5 establishes strict evidence verification and structured provenance tracking for all candidate extractions and relationships:

### 10.1 Grounding Principle: NO EVIDENCE -> NO ACCEPTED INTELLIGENCE
The model itself is untrusted; the source document context is the sole authority. Every proposed extraction or relationship candidate must be grounded against actual source context before acceptance.

```
Document Understanding Context (Phase 2)
                 │
                 ▼
       AI Proposal (Phase 3 / 4)
                 │
                 ▼
    Evidence Grounding Engine (`EvidenceGroundingEngine`)
    - Exact and Normalized Snippet Verification (Handles OCR / CRLF harmlessly)
    - Page Boundary Verification (Rejects out-of-range pages)
    - Rejection of Semantic Alterations (e.g. "saw" -> "met")
                 │
                 ▼
     Provenance Tracker (`ProvenanceTracker`)
     - Source Type Classification (TEXT, OCR, PDF, TABLE, CDR, TRANSACTION)
     - Derivation Classification (DIRECT, CONTEXTUAL, STRUCTURED)
     - Evidence Deduplication & Enrichment
                 │
                 ▼
     Reconciliation & Output Validation
     - Unified Relationship with Provenance (p.X: snippet)
     - Zero database UUIDs or case IDs minted
```

### 10.2 Supported Provenance Modalities
- `ProvenanceSourceType`: `TEXT`, `OCR`, `IMAGE`, `PDF`, `TABLE`, `STRUCTURED_CDR`, `STRUCTURED_TRANSACTION`.
- `DerivationType`: `DIRECT` (explicit in single sentence/record), `CONTEXTUAL` (multi-sentence / cross-page inference), `STRUCTURED` (from validated transactions or CDRs).
- `VerificationState`: `VERIFIED` (grounded in source), `PARTIAL` (approximate / normalized token overlap), `UNVERIFIED` (missing in context), `INVALID` (fabricated snippet or page).

### 10.3 Immutable Separation
- **Person A Evidence Ledger**: Person A owns backend persistence, hashing, and audit storage. Phase 5 ML produces validated evidence references and never writes to PostgreSQL or Neo4j.
- **No Hidden Chain-of-Thought**: Retains concise evidence citations and high-level summaries without recording private model reasoning traces.

### 10.4 Frozen Backend Contracts (Phase 5)
- **HTTP Endpoints Added:** **NONE**
- **Existing Backend Endpoint:** `POST /api/documents/{document_id}/process` (UNCHANGED)
- **Existing ML Entry Point:** `ml.pipeline.process_document(...)` (COMPATIBLE)
- **Backend Modifications:** **NONE**
- **Shared Schemas Modifications:** **NONE**
- **Database Modifications:** **NONE**
- **Evidence Ledger Modifications:** **NONE**
- **Neo4j Modifications:** **NONE**




