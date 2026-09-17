"""
MVP deterministic pattern detector for CrimeLens.

Architecture note: This module is placed in the ml/ package so it is
discovered by app.ml.adapter's _PERSON_B_PATTERN_CANDIDATES auto-discovery.
It reads StructuredRecord data from PostgreSQL via a fresh SessionLocal.

Idempotency contract
--------------------
Every emitted pattern/lead carries a deterministic `id` (the fingerprint)
built from:
    SHA256( case_id | pattern_type | sorted_entity_names | sorted_evidence_ids )

This fingerprint is used by app.services.insights._upsert_output as the
`source_id`, which is covered by the DB unique constraint
    uq_intelligence_outputs_case_kind_source (case_id, kind, source_id).

Running detection twice on the same data must produce the same fingerprint
→ the second call is an UPDATE (no new row). No in-memory-only deduplication.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.document import Document, StructuredRecord
from app.models.enums import RecordType


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_time(t_str: str) -> datetime:
    if t_str.endswith("Z"):
        t_str = t_str[:-1] + "+00:00"
    return datetime.fromisoformat(t_str)


def _fingerprint(case_id: str, pattern_type: str, entities: list[str], evidence_ids: list[str]) -> str:
    """Deterministic 16-char hex ID scoped to (case, type, entities, evidence)."""
    stable = "|".join([
        case_id,
        pattern_type,
        ",".join(sorted(entities)),
        ",".join(sorted(evidence_ids)),
    ])
    return hashlib.sha256(stable.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# detector
# ---------------------------------------------------------------------------

def detect_patterns(document_bytes: bytes, filename: str, document_id: str) -> dict:
    """
    Deterministic pattern detector.
    Called by app.ml.adapter.collect_person_b_intelligence.

    Returns {"patterns": [...], "leads": [...]}.
    Every id is a deterministic fingerprint; running twice on the same data
    returns identical ids so the DB upsert is idempotent.
    """
    patterns: list[dict] = []
    leads: list[dict] = []

    db = SessionLocal()
    try:
        doc = db.get(Document, uuid.UUID(document_id))
        if not doc:
            return {"patterns": patterns, "leads": leads}

        case_id = str(doc.case_id)

        records = (
            db.query(StructuredRecord)
            .filter(StructuredRecord.case_id == doc.case_id)
            .all()
        )

        txs: list[dict] = []
        locs: list[dict] = []

        for r in records:
            payload = r.raw_json
            if r.record_type == RecordType.TRANSACTION:
                if "source" in payload and "target" in payload and "timestamp" in payload:
                    txs.append({
                        "id": str(r.id),
                        "source": payload["source"],
                        "target": payload["target"],
                        "time": _parse_time(payload["timestamp"]),
                    })
            elif r.record_type == RecordType.CDR:
                if "entity" in payload and "location" in payload and "timestamp" in payload:
                    locs.append({
                        "id": str(r.id),
                        "entity": payload["entity"],
                        "location": payload["location"],
                        "time": _parse_time(payload["timestamp"]),
                    })

        txs.sort(key=lambda x: x["time"])
        locs.sort(key=lambda x: x["time"])

        # ------------------------------------------------------------------
        # A. CIRCULAR_TRANSACTION  A -> B -> C -> A within 30 days
        #
        # Logical dedup key: frozenset of entity names in the cycle.
        # There is at most one canonical circular pattern per entity-triple.
        # We pick the EARLIEST evidence set (chronologically first t1).
        # ------------------------------------------------------------------
        seen_circular: set[frozenset] = set()

        for i, t1 in enumerate(txs):
            for j in range(i + 1, len(txs)):
                t2 = txs[j]
                if t1["target"] != t2["source"]:
                    continue
                if (t2["time"] - t1["time"]).days > 30:
                    continue
                for k in range(j + 1, len(txs)):
                    t3 = txs[k]
                    if t2["target"] != t3["source"] or t3["target"] != t1["source"]:
                        continue
                    if (t3["time"] - t1["time"]).days > 30:
                        continue

                    entity_key = frozenset([t1["source"], t1["target"], t2["target"]])
                    if entity_key in seen_circular:
                        continue  # already captured this logical cycle
                    seen_circular.add(entity_key)

                    entities = [t1["source"], t1["target"], t2["target"]]
                    ev_ids = [t1["id"], t2["id"], t3["id"]]
                    fp = _fingerprint(case_id, "CIRCULAR_TRANSACTION", entities, ev_ids)

                    patterns.append({
                        "id": fp,
                        "type": "CIRCULAR_TRANSACTION",
                        "status": "INFERRED",
                        "severity": "HIGH",
                        "entities": entities,
                        "explanation": (
                            f"Circular transaction detected: "
                            f"{entities[0]} \u2192 {entities[1]} \u2192 {entities[2]} "
                            f"\u2192 {entities[0]} within 30 days."
                        ),
                        "evidence_ids": ev_ids,
                    })
                    lead_fp = _fingerprint(case_id, "CIRCULAR_TRANSACTION_LEAD", entities, ev_ids)
                    leads.append({
                        "id": lead_fp,
                        "type": "FINANCIAL_NETWORK",
                        "status": "PREDICTED",
                        "priority": "HIGH",
                        "title": f"Circular transaction network: {entities[0]} \u2192 {entities[1]} \u2192 {entities[2]}",
                        "explanation": "Potential circular transaction network indicating obfuscation.",
                        "entity_ids": entities,
                        "evidence_ids": ev_ids,
                    })

        # ------------------------------------------------------------------
        # B. RAPID_TRANSFER_CHAIN  A -> B -> C within 48 hours
        #
        # Logical dedup key: (source, relay, destination) entity triple.
        # ------------------------------------------------------------------
        seen_rapid: set[tuple] = set()

        for i, t1 in enumerate(txs):
            for j in range(i + 1, len(txs)):
                t2 = txs[j]
                if t1["target"] != t2["source"] or t2["target"] == t1["source"]:
                    continue
                delta_h = (t2["time"] - t1["time"]).total_seconds() / 3600.0
                if not (0 <= delta_h <= 48):
                    continue

                entity_key = (t1["source"], t1["target"], t2["target"])
                if entity_key in seen_rapid:
                    continue
                seen_rapid.add(entity_key)

                entities = list(entity_key)
                ev_ids = [t1["id"], t2["id"]]
                fp = _fingerprint(case_id, "RAPID_TRANSFER_CHAIN", entities, ev_ids)

                patterns.append({
                    "id": fp,
                    "type": "RAPID_TRANSFER_CHAIN",
                    "status": "INFERRED",
                    "severity": "MEDIUM",
                    "entities": entities,
                    "explanation": (
                        f"Rapid transfer chain detected: "
                        f"{entities[0]} \u2192 {entities[1]} \u2192 {entities[2]} within 48 hours."
                    ),
                    "evidence_ids": ev_ids,
                })

        # ------------------------------------------------------------------
        # C. LOCATION_TIME_OVERLAP  Two entities at same location within 2h
        #
        # Logical dedup key: frozenset of entity names at the location.
        # ------------------------------------------------------------------
        seen_loc: set[frozenset] = set()

        for i, l1 in enumerate(locs):
            for j in range(i + 1, len(locs)):
                l2 = locs[j]
                if l1["location"] != l2["location"] or l1["entity"] == l2["entity"]:
                    continue
                delta_h = abs((l2["time"] - l1["time"]).total_seconds()) / 3600.0
                if delta_h > 2.0:
                    continue

                entity_key = frozenset([l1["entity"], l2["entity"]])
                if entity_key in seen_loc:
                    continue
                seen_loc.add(entity_key)

                entities = [l1["entity"], l2["entity"]]
                ev_ids = [l1["id"], l2["id"]]
                fp = _fingerprint(case_id, "LOCATION_TIME_OVERLAP", entities, ev_ids)

                patterns.append({
                    "id": fp,
                    "type": "LOCATION_TIME_OVERLAP",
                    "status": "INFERRED",
                    "severity": "MEDIUM",
                    "entities": entities,
                    "explanation": (
                        f"Entities {entities[0]} and {entities[1]} overlapped "
                        f"at location {l1['location']} within a 2-hour window."
                    ),
                    "evidence_ids": ev_ids,
                })
                lead_fp = _fingerprint(case_id, "LOCATION_TIME_OVERLAP_LEAD", entities, ev_ids)
                leads.append({
                    "id": lead_fp,
                    "type": "LOCATION_TIME_OVERLAP",
                    "status": "PREDICTED",
                    "priority": "MEDIUM",
                    "title": f"Location overlap: {entities[0]} and {entities[1]} at {l1['location']}",
                    "explanation": "Possible physical meeting between subjects based on location overlap.",
                    "entity_ids": entities,
                    "evidence_ids": ev_ids,
                })

    finally:
        db.close()

    return {"patterns": patterns, "leads": leads}


def process_document(document_bytes: bytes, filename: str, document_id: str) -> dict:
    """Delegates document extraction to ml.pipeline.process_document."""
    try:
        from ml.pipeline import process_document as pipeline_process
        res = pipeline_process(document_bytes, filename, document_id)
        if hasattr(res, "model_dump"):
            return res.model_dump(mode="json")
        return res
    except Exception:
        return {
            "document_id": document_id,
            "entities": [],
            "relationships": [],
        }
