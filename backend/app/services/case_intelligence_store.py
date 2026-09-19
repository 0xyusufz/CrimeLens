"""Case Network Intelligence Persistence & Cache Manager.

Ensures that AI network analyses (Gemini/Groq) are persisted to disk and cached
against the exact topological fingerprint of the case network (entities,
relationships, and registered documents).

If the case network has not changed:
- Subsequent queries return the saved analysis instantly without burning API tokens or inducing lag.
If the network changes (new entity, relationship updated, new document added) or user requests force refresh:
- A new analysis is computed, saved, and supersedes the old report.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import upload_dir
from app.models.case import Case
from app.models.document import Document
from app.models.entity import Entity, EntityCaseLink
from app.models.relationship import RelationshipStaging
from app.services.gemini_provider import gemini_engine

logger = logging.getLogger("crimelens.intelligence_store")


def _get_store_dir() -> Path:
    """Returns directory where case intelligence reports are saved."""
    base = upload_dir().parent / "intelligence_reports"
    base.mkdir(parents=True, exist_ok=True)
    return base


def compute_case_network_fingerprint(
    session: Session,
    case_id: uuid.UUID,
    mode: str = "full",
    selected_node_ids: Optional[list[str]] = None,
    hops: int = 2,
) -> tuple[str, dict[str, int]]:
    """Calculates a deterministic cryptographic fingerprint of the case network.

    If any entity, relationship, or document changes, the fingerprint changes.
    """
    # 1. Entities in case
    entities_stmt = (
        select(Entity)
        .join(EntityCaseLink, EntityCaseLink.entity_id == Entity.id)
        .where(EntityCaseLink.case_id == case_id)
    )
    all_entities = list(session.scalars(entities_stmt).all())
    sorted_entities = sorted(all_entities, key=lambda e: str(e.id))
    ent_tokens = [f"{e.id}:{e.canonical_name}:{e.type.value if hasattr(e.type, 'value') else e.type}" for e in sorted_entities]

    # 2. Relationships in case
    rels_stmt = select(RelationshipStaging).where(RelationshipStaging.case_id == case_id)
    all_rels = list(session.scalars(rels_stmt).all())
    sorted_rels = sorted(all_rels, key=lambda r: str(r.id))
    rel_tokens = [f"{r.id}:{r.source_entity_id}:{r.target_entity_id}:{r.status.value if hasattr(r.status, 'value') else r.status}" for r in sorted_rels]

    # 3. Documents in case
    docs_stmt = select(Document).where(Document.case_id == case_id)
    all_docs = list(session.scalars(docs_stmt).all())
    sorted_docs = sorted(all_docs, key=lambda d: str(d.id))
    doc_tokens = [f"{d.id}:{d.filename}" for d in sorted_docs]

    # Mode-specific context
    mode_token = f"mode={mode}"
    if mode in ("node", "selected") and selected_node_ids:
        sorted_nodes = sorted(str(n) for n in selected_node_ids)
        mode_token += f"|nodes={','.join(sorted_nodes)}|hops={hops}"

    raw_signature = (
        f"{mode_token}#"
        f"ENT({len(ent_tokens)}):{';'.join(ent_tokens)}#"
        f"REL({len(rel_tokens)}):{';'.join(rel_tokens)}#"
        f"DOC({len(doc_tokens)}):{';'.join(doc_tokens)}"
    )

    fingerprint = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:24]
    stats = {
        "entities_count": len(all_entities),
        "relationships_count": len(all_rels),
        "documents_count": len(all_docs),
    }
    return fingerprint, stats


def _get_report_file_path(case_id: uuid.UUID, mode: str, target_node_id: Optional[str] = None) -> Path:
    case_dir = _get_store_dir() / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    if mode in ("node", "selected") and target_node_id:
        safe_id = "".join(c for c in str(target_node_id) if c.isalnum() or c in ("-", "_"))
        filename = f"report_node_{safe_id}.json"
    else:
        filename = "report_full.json"
    return case_dir / filename


def get_saved_report(
    case_id: uuid.UUID,
    mode: str = "full",
    target_node_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Loads a previously saved report for this case if it exists."""
    report_file = _get_report_file_path(case_id, mode, target_node_id)
    if not report_file.exists():
        return None
    try:
        data = json.loads(report_file.read_text(encoding="utf-8"))
        return data
    except Exception as ex:
        logger.warning(f"Failed to read saved report {report_file}: {ex}")
        return None


def save_report(
    case_id: uuid.UUID,
    mode: str,
    fingerprint: str,
    network_stats: dict[str, int],
    result: dict[str, Any],
    target_node_id: Optional[str] = None,
) -> None:
    """Atomically saves an analysis report to disk with network metadata."""
    report_file = _get_report_file_path(case_id, mode, target_node_id)
    payload = {
        "case_id": str(case_id),
        "mode": mode,
        "target_node_id": str(target_node_id) if target_node_id else None,
        "fingerprint": fingerprint,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "network_stats": network_stats,
        "analysis": result,
    }
    tmp_file = report_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_file, report_file)
    logger.info(f"Saved network intelligence report for case {case_id} (fingerprint: {fingerprint})")


def get_or_analyze_network(
    session: Session,
    case_id: uuid.UUID,
    mode: str = "full",
    selected_node_ids: Optional[list[str]] = None,
    hops: int = 2,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Retrieves the cached network analysis if network has not changed,

    otherwise triggers Gemini intelligence reasoning, caches it, and returns the result.
    """
    target_node_id = selected_node_ids[0] if (mode in ("node", "selected") and selected_node_ids) else None
    current_fp, stats = compute_case_network_fingerprint(
        session=session,
        case_id=case_id,
        mode=mode,
        selected_node_ids=selected_node_ids,
        hops=hops,
    )

    saved = get_saved_report(case_id, mode=mode, target_node_id=target_node_id)

    # If cached report exists, is valid for current network, and no force refresh requested:
    if saved and not force_refresh:
        saved_fp = saved.get("fingerprint")
        if saved_fp == current_fp and saved.get("analysis"):
            logger.info(f"Returning cached network analysis for case {case_id} (matching fingerprint: {current_fp})")
            result = dict(saved["analysis"])
            result["cached"] = True
            result["saved_at"] = saved.get("saved_at")
            result["network_stats"] = stats
            result["fingerprint"] = current_fp
            result["is_network_changed"] = False
            return result
        else:
            logger.info(f"Network changed for case {case_id} (old fp: {saved_fp}, new fp: {current_fp}). Re-running analysis.")

    # Either no report, or network changed, or force refresh requested:
    fresh_result = gemini_engine.analyze_network(
        session=session,
        case_id=case_id,
        selected_node_ids=selected_node_ids,
        mode=mode,
        hops=hops,
    )

    # Save to disk
    save_report(
        case_id=case_id,
        mode=mode,
        fingerprint=current_fp,
        network_stats=stats,
        result=fresh_result,
        target_node_id=target_node_id,
    )

    fresh_result["cached"] = False
    fresh_result["saved_at"] = datetime.now(timezone.utc).isoformat()
    fresh_result["network_stats"] = stats
    fresh_result["fingerprint"] = current_fp
    fresh_result["is_network_changed"] = False
    return fresh_result


def check_report_status(
    session: Session,
    case_id: uuid.UUID,
    mode: str = "full",
    target_node_id: Optional[str] = None,
    hops: int = 2,
) -> dict[str, Any]:
    """Inspects whether an analysis is currently saved and whether the network has changed since."""
    current_fp, stats = compute_case_network_fingerprint(
        session=session,
        case_id=case_id,
        mode=mode,
        selected_node_ids=[target_node_id] if target_node_id else None,
        hops=hops,
    )
    saved = get_saved_report(case_id, mode=mode, target_node_id=target_node_id)
    if not saved or not saved.get("analysis"):
        return {
            "has_saved_report": False,
            "is_network_changed": False,
            "saved_at": None,
            "fingerprint": current_fp,
            "network_stats": stats,
            "analysis": None,
        }

    saved_fp = saved.get("fingerprint")
    is_changed = (saved_fp != current_fp)

    return {
        "has_saved_report": True,
        "is_network_changed": is_changed,
        "saved_at": saved.get("saved_at"),
        "fingerprint": current_fp,
        "saved_fingerprint": saved_fp,
        "network_stats": stats,
        "analysis": saved.get("analysis"),
    }
