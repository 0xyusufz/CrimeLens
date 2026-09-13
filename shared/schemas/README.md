# Shared ML ↔ Backend JSON contract

Person B produces JSON. Person A FastAPI validates it with these Pydantic models, then later persists to PostgreSQL (source of truth) and projects relationship intelligence into Neo4j.

```
ML pipeline (Person B)
        ↓
  structured JSON
        ↓
FastAPI Pydantic validation (Person A)
        ↓
PostgreSQL  (canonical records / evidence)
        ↓
Neo4j       (derived graph; backend canonical UUIDs only)
```

ML never writes to PostgreSQL or Neo4j.

## Python import (Person B)

From the repo root:

```python
from shared.schemas import (
    EntityMention,
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)
```

Install Pydantic 2 (`pip install pydantic`) or use the backend venv.

## Schemas

| Schema | Python model | JSON file |
| --- | --- | --- |
| Entity mention | `EntityMention` | `entity.schema.json` |
| Relationship | `Relationship` | `relationship.schema.json` |
| Extraction envelope | `ExtractionResult` | `extraction_result.schema.json` |
| Resolution proposal | `ResolutionProposal` | `resolution.schema.json` |
| Pattern | `Pattern` | `pattern.schema.json` |
| Lead | `Lead` | `lead.schema.json` |

## Frozen ID lifecycle

| ID | Owner | Meaning |
| --- | --- | --- |
| `mention_001` (`EntityMention.id`) | ML | Staging / document-level mention. Not a canonical entity. |
| `rel_001` (`Relationship.id`) | ML | Extracted source occurrence. |
| `canonical_entity_id` on a resolution proposal | ML | Proposal / grouping key only. |
| Canonical entity UUID | Backend | Real PostgreSQL identity. Minted by Person A. |
| Neo4j `entity_id` | Backend | Same backend-issued canonical UUID. Never an ML grouping ID. Never a Neo4j internal ID. |

`case_id` is not produced by Person B. Backend derives it from `document_id`. Canonical `entities` have no single `case_id`; `entity_case_links` records case membership, including the same entity in multiple cases.

Extraction `source_entity_id` / `target_entity_id` are mention IDs.

## Entity resolution

- ML emits a `ResolutionProposal`. Backend makes the final canonicalization decision.
- Exact phone, exact bank account, or another explicitly agreed strong identifier may auto-link.
- Name-only fuzzy similarity must **never** auto-merge.

## Confidence

Always explicit, always `0.0`–`1.0`. Confidence is not truth and is not guilt.

## Frozen status semantics (do not coerce)

Relationships and patterns use the same evidence statuses:

| Status | Meaning |
| --- | --- |
| `CONFIRMED` | Direct source evidence |
| `INFERRED` | Supported by multiple signals, not a single stated fact |
| `PREDICTED` | Model/heuristic suggestion |

Never silently change or upgrade `INFERRED` or `PREDICTED` to `CONFIRMED`. There is no `DETECTED` status.

Example: `CIRCULAR_TRANSACTION` pattern uses `status=INFERRED`.

Pattern `severity` (`LOW` / `MEDIUM` / `HIGH`) is not status.

Lead uses `priority` (`LOW` / `MEDIUM` / `HIGH`), not `severity`. Lead `status` (workflow, e.g. `REVIEW_REQUIRED`) stays separate from priority. Do not introduce person-level risk scores. Optional `priority_score` is a lead priority score only.

## Patterns vs leads (persistence)

Person B detects patterns and returns `Pattern` JSON. Person A validates and persists.

Do **not** create a Pattern table at this stage. Validated pattern results are stored as intelligence / lead outputs and later exposed through the case insights API.

## Structured-record enrichment

Keep the ML relationship contract compact. Do not add these fields to ML relationship JSON:

- Transaction: `amount`, `currency`, `transaction_time` — from structured transaction records
- CDR: `call_time`, `duration` — from structured CDR records

Every relationship still needs `source_document_id` and/or `source_record_id`, plus `evidence_snippet` and `extracted_at` (ISO 8601).

Allowed MVP entity types: `PERSON`, `PHONE`, `BANK_ACCOUNT`, `VEHICLE`, `ORGANIZATION`, `LOCATION`, `EVENT`.

Allowed MVP relationship types: `CALLED`, `SENT_MONEY_TO`, `OWNS_VEHICLE`, `USED_VEHICLE`, `WORKS_FOR`, `LOCATED_AT`, `ASSOCIATED_WITH`, `PART_OF_EVENT`.
