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

Test Suite: `ml/tests/test_ai_foundation.py` (28 unit tests)
- Provider abstraction & subclass conformance
- Multimodal inputs (Text, Image, PDF, Structured, Bytes)
- Invalid input rejection (empty, blank whitespace, improper types)
- Normalized model response getters & isolation
- Deterministic mock provider repeatability
- Controlled failure simulations (timeout, rate limit, auth, malformed, unavailable, execution)
- AIClient bounded retry on transient errors vs immediate abort on auth failure
- Context sanitization & secret stripping
- Secret redaction regex across error messages & config repr
- Full regression compatibility with `process_document`

Total ML test suite: **399 passed, 1 skipped** (Tesseract OCR skipped when binary is absent).
All 13 contract tests in `tests/test_ml_contract.py` pass 100%.
