# ML ↔ Backend contracts

Canonical schemas live in `shared/schemas/`. Schema changes require a team discussion.

Pipeline:

```
ML → JSON → FastAPI validation → PostgreSQL → Neo4j
```

## Frozen ID lifecycle

1. ML mention IDs (`mention_001`) are staging / document-level IDs.
2. ML relationship IDs identify extracted source occurrences.
3. ML `canonical_entity_id` is only a proposal / grouping key.
4. Backend mints the real canonical PostgreSQL UUID.
5. Neo4j stores that backend UUID as `entity_id`. Never ML grouping IDs. Never Neo4j internal IDs.

Person B does not emit `case_id`. Backend derives `case_id` from `document_id`. Canonical entities have no single `case_id`; `entity_case_links` is the cross-case membership table.

## Frozen resolution

- ML proposes; backend canonicalizes.
- Exact phone / exact bank account / explicitly agreed strong identifier may auto-link.
- Name-only fuzzy similarity never auto-merges.

## Frozen status

Relationships and patterns: `CONFIRMED` | `INFERRED` | `PREDICTED`. Never coerce. No `DETECTED`.

Leads: `priority` (not `severity`) plus a separate workflow `status`. No person-level risk scores.

## Frozen persistence (before SQLAlchemy)

- No Pattern table in this stage.
- Pattern JSON is validated then stored as intelligence / lead output for case insights.
- Financial and CDR numeric/time fields stay on structured records, not on the ML relationship schema.

See `shared/schemas/README.md` for field-level rules.
