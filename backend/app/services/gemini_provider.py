"""Gemini Case Network Intelligence & Copilot Engine.

Supplies Gemini (gemini-3.6-flash) with full access to the case's structured
entity and relationship tables so Gemini can inspect connections, explain network
topologies, and act as an interactive Copilot for investigators.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.entity import Entity, EntityCaseLink
from app.models.relationship import RelationshipStaging

load_dotenv()

logger = logging.getLogger("crimelens.gemini")

GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]


class GeminiIntelligenceEngine:
    """Provides case graph reasoning, network analysis, and interactive copilot with multi-tier fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_keys = [k for k in [api_key, os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_BACKUP")] if k]
        self.model = GEMINI_MODELS[0]

    def _generate_with_fallback(self, prompt_or_contents: str) -> str:
        # 1. Try Gemini across available keys and models
        for k in self.api_keys:
            client = genai.Client(api_key=k)
            for m in GEMINI_MODELS:
                try:
                    res = client.models.generate_content(
                        model=m,
                        contents=prompt_or_contents,
                    )
                    if res and res.text:
                        self.model = m
                        return res.text
                except Exception as ex:
                    # If 429 quota or 404, try next model or key
                    logger.warning(f"Gemini model {m} failed: {ex}. Trying next fallback...")
                    continue

        # 2. Resilient fallback to Groq if Gemini free tier quota is exhausted
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                g_client = Groq(api_key=groq_key)
                g_res = g_client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "user", "content": prompt_or_contents}],
                    max_completion_tokens=2048,
                    temperature=0.3,
                    reasoning_effort="medium",
                )
                if g_res.choices and g_res.choices[0].message:
                    self.model = "groq/openai/gpt-oss-20b (fallback)"
                    return g_res.choices[0].message.content or ""
            except Exception as g_err:
                logger.error(f"Groq fallback failed: {g_err}")

        return "Intelligence synthesis currently unavailable due to rate limits. Please retry in a few moments."

    def is_available(self) -> bool:
        return bool(self.api_keys) or bool(os.getenv("GROQ_API_KEY"))

    def build_case_tables(
        self,
        session: Session,
        case_id: uuid.UUID,
        filter_entity_ids: Optional[set[uuid.UUID]] = None,
        filter_rel_ids: Optional[set[uuid.UUID]] = None,
    ) -> dict[str, Any]:
        """Constructs markdown tables of entities and relationships for a case (optionally filtered)."""
        # 1. Fetch Entities
        entities_stmt = (
            select(Entity)
            .join(EntityCaseLink, EntityCaseLink.entity_id == Entity.id)
            .where(EntityCaseLink.case_id == case_id)
            .order_by(Entity.type, Entity.canonical_name)
        )
        all_entities = list(session.scalars(entities_stmt).all())
        if filter_entity_ids is not None:
            entities = [e for e in all_entities if e.id in filter_entity_ids]
        else:
            entities = all_entities
        entity_map = {e.id: e for e in all_entities}

        # 2. Fetch Relationships
        rels_stmt = (
            select(RelationshipStaging)
            .where(RelationshipStaging.case_id == case_id)
            .order_by(RelationshipStaging.confidence.desc())
        )
        all_rels = list(session.scalars(rels_stmt).all())
        if filter_rel_ids is not None:
            rels = [r for r in all_rels if r.id in filter_rel_ids]
        elif filter_entity_ids is not None:
            rels = [
                r for r in all_rels
                if r.source_entity_id in filter_entity_ids and r.target_entity_id in filter_entity_ids
            ]
        else:
            rels = all_rels

        # Markdown Table: Entities
        ent_rows = ["| Entity Name | Type | Entity ID |", "|---|---|---|"]
        for e in entities:
            ent_rows.append(f"| {e.canonical_name} | {e.type.value if hasattr(e.type, 'value') else e.type} | {e.id} |")
        entities_table_md = "\n".join(ent_rows) if entities else "_No entities recorded yet._"

        # Markdown Table: Relationships
        rel_rows = [
            "| Source Entity | Relationship | Target Entity | Status | Confidence | Evidence Snippet |",
            "|---|---|---|---|---|---|",
        ]
        for r in rels:
            src_name = entity_map[r.source_entity_id].canonical_name if r.source_entity_id in entity_map else "Unknown"
            tgt_name = entity_map[r.target_entity_id].canonical_name if r.target_entity_id in entity_map else "Unknown"
            rel_type = r.relationship_type.value if hasattr(r.relationship_type, "value") else str(r.relationship_type)
            status = r.status.value if hasattr(r.status, "value") else str(r.status)
            ev = (r.evidence_snippet or "").replace("\n", " ").strip()
            rel_rows.append(f"| {src_name} | {rel_type} | {tgt_name} | {status} | {r.confidence:.2f} | {ev} |")
        rels_table_md = "\n".join(rel_rows) if rels else "_No relationships extracted yet._"

        return {
            "entities_count": len(entities),
            "relationships_count": len(rels),
            "entities": entities,
            "relationships": rels,
            "entities_table_md": entities_table_md,
            "relationships_table_md": rels_table_md,
        }

    def generate_network_brief(self, session: Session, case_id: uuid.UUID) -> str:
        """Uses Gemini to analyze the case network tables and produce an executive intelligence brief."""
        if not self.is_available():
            return "Gemini API key is not configured."

        case = session.get(Case, case_id)
        case_title = case.title if case else f"Case {case_id}"

        tables = self.build_case_tables(session, case_id)
        if tables["entities_count"] == 0 and tables["relationships_count"] == 0:
            return "No entities or relationships have been extracted for this case yet. Upload documents to initiate extraction."

        prompt = f"""You are a Lead Criminal Intelligence Analyst using CrimeLens.
Analyze the following Case Network Tables for case '{case_title}'.

{tables['entities_table_md']}

{tables['relationships_table_md']}

Provide a thorough, grounded intelligence analysis structured into:
1. **Executive Network Summary**: Who are the primary hubs, key actors, and organizations?
2. **Connection Chains & Money/Communication Flows**: Detailed explanation of who is connected to whom and how funds or calls flowed.
3. **High-Risk Vulnerabilities / Anomaly Observations**: Shell company usage, indirect contacts, rapid movements.
4. **Actionable Investigative Leads**: What specific entities or relationships should investigators subpoena or examine next?

Cite specific evidence snippets from the relationship table when making claims. Be objective, precise, and professional.
"""

        return self._generate_with_fallback(prompt)

    def analyze_network(
        self,
        session: Session,
        case_id: uuid.UUID,
        selected_node_ids: Optional[list[str]] = None,
        mode: str = "full",
        hops: int = 2,
    ) -> dict[str, Any]:
        """Performs deep graph reasoning over selected nodes (1/2-hop) or full case network."""
        if not self.is_available():
            return {
                "mode": mode,
                "case_summary": "Intelligence engine is currently offline or unconfigured.",
                "key_entities": [],
                "important_relationships": [],
                "potential_persons_of_interest": [],
                "investigative_leads": [],
                "supporting_evidence": [],
                "contradictions_or_anomalies": [],
                "confidence_score": 0.0,
                "dossier_markdown": "### Intelligence Engine Offline\nPlease ensure GEMINI_API_KEY or GROQ_API_KEY is configured in backend environment.",
                "model": "offline",
            }

        case = session.get(Case, case_id)
        case_title = case.title if case else f"Case {case_id}"

        # 1. Determine subgraph boundary
        target_uuid_set: set[uuid.UUID] = set()
        if selected_node_ids and mode in ("node", "selected"):
            for nid in selected_node_ids:
                try:
                    target_uuid_set.add(uuid.UUID(str(nid)))
                except (ValueError, TypeError):
                    continue

        # If node mode requested with valid nodes, expand 1-hop & 2-hop
        filter_entity_ids: Optional[set[uuid.UUID]] = None
        filter_rel_ids: Optional[set[uuid.UUID]] = None

        if target_uuid_set:
            # Fetch all rels to traverse hops
            all_rels_stmt = select(RelationshipStaging).where(RelationshipStaging.case_id == case_id)
            all_rels = list(session.scalars(all_rels_stmt).all())

            # 1-hop expansion
            hop1_entities = set(target_uuid_set)
            included_rels: set[RelationshipStaging] = set()
            for r in all_rels:
                if r.source_entity_id in target_uuid_set or r.target_entity_id in target_uuid_set:
                    hop1_entities.add(r.source_entity_id)
                    hop1_entities.add(r.target_entity_id)
                    included_rels.add(r)

            # 2-hop expansion if requested
            if hops >= 2:
                hop2_entities = set(hop1_entities)
                for r in all_rels:
                    if r.source_entity_id in hop1_entities or r.target_entity_id in hop1_entities:
                        hop2_entities.add(r.source_entity_id)
                        hop2_entities.add(r.target_entity_id)
                        included_rels.add(r)
                filter_entity_ids = hop2_entities
            else:
                filter_entity_ids = hop1_entities

            filter_rel_ids = {r.id for r in included_rels}

        tables = self.build_case_tables(
            session,
            case_id,
            filter_entity_ids=filter_entity_ids,
            filter_rel_ids=filter_rel_ids,
        )

        scope_desc = (
            f"Focused {hops}-Hop Neighborhood of selected entities: {len(target_uuid_set)} entity/entities"
            if target_uuid_set
            else "Complete Multi-Document Case Network"
        )

        prompt = f"""You are a Senior Criminal Intelligence Reasoning Engine for CrimeLens.
Analyze the following investigative graph tables for Case: '{case_title}'.
Analysis Scope: {scope_desc}

### EXTRACTED CASE ENTITIES ({tables['entities_count']} Total in Scope)
{tables['entities_table_md']}

### EXTRACTED CASE RELATIONSHIPS ({tables['relationships_count']} Total in Scope)
{tables['relationships_table_md']}

CRITICAL INSTRUCTIONS:
1. SEPARATION OF KNOWLEDGE:
   - Internal Domain Knowledge: Use your understanding of criminal methodology, money laundering layers, front companies, CDR frequency patterns, and smuggling networks to interpret motives and structures.
   - Case-Specific Evidence: Base ALL factual claims, connections, names, and transactions STRICTLY on the tables above.
   - ZERO HALLUCINATION: Never fabricate people, banks, dates, or relationships not grounded in the table evidence.
2. OUTPUT FORMAT:
   You MUST return a valid JSON object wrapped inside a ```json ... ``` codeblock.
   JSON schema:
   {{
     "case_summary": "Concise summary of network structure and primary illicit activity",
     "key_entities": [
       {{ "name": "...", "type": "...", "role": "...", "risk_level": "LOW|MEDIUM|HIGH|CRITICAL" }}
     ],
     "important_relationships": [
       {{ "source": "...", "target": "...", "type": "...", "significance": "...", "evidence_snippet": "..." }}
     ],
     "potential_persons_of_interest": [
       {{ "name": "...", "reason": "...", "threat_level": "LOW|MEDIUM|HIGH|CRITICAL", "evidence": "..." }}
     ],
     "investigative_leads": [
       "Actionable lead 1 with specific target and justification",
       "Actionable lead 2 with subpoena or surveillance recommendation"
     ],
     "supporting_evidence": [
       {{ "claim": "...", "quote": "..." }}
     ],
     "contradictions_or_anomalies": [
       "Identified contradiction, timeline conflict, or anomaly"
     ],
     "confidence_score": 0.88,
     "dossier_markdown": "Full GitHub-flavored Markdown intelligence dossier for investigators with sections: Executive Summary, Network Hubs & Roles, Flow of Transactions/Calls, Identified Threat Entities, and Prioritized Action Steps."
   }}
"""

        raw_output = self._generate_with_fallback(prompt)

        # Parse output JSON
        parsed: dict[str, Any] = {}
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_output)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
            except Exception:
                parsed = {}

        if not parsed:
            # Try raw json load
            try:
                parsed = json.loads(raw_output)
            except Exception:
                parsed = {}

        # If JSON parsing failed, salvage into valid schema
        if not parsed:
            parsed = {
                "case_summary": f"Automated analysis for {case_title}",
                "key_entities": [],
                "important_relationships": [],
                "potential_persons_of_interest": [],
                "investigative_leads": ["Review highlighted entity connections in case graph."],
                "supporting_evidence": [],
                "contradictions_or_anomalies": [],
                "confidence_score": 0.75,
                "dossier_markdown": raw_output,
            }

        parsed["mode"] = "node" if target_uuid_set else "full"
        parsed["model"] = self.model
        parsed["in_scope_entities"] = tables["entities_count"]
        parsed["in_scope_relationships"] = tables["relationships_count"]

        return parsed

    def chat_copilot(
        self,
        session: Session,
        case_id: uuid.UUID,
        question: str,
        chat_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Interactive investigator Copilot query against the case tables and relationships."""
        if not self.is_available():
            return "Gemini API key is not configured."

        case = session.get(Case, case_id)
        case_title = case.title if case else f"Case {case_id}"

        tables = self.build_case_tables(session, case_id)

        system_instruction = f"""You are CrimeLens AI Copilot, a senior intelligence analyst assistant.
You have direct, real-time access to the case's verified Entity and Relationship Tables below:

### CASE ENTITIES ({tables['entities_count']} Total)
{tables['entities_table_md']}

### CASE RELATIONSHIPS ({tables['relationships_count']} Total)
{tables['relationships_table_md']}

RULES:
- Always base your answers strictly on the entities and relationships present in the tables above.
- When explaining connections, cite the exact relationship type, confidence, and verbatim evidence snippets.
- If asked about a person, vehicle, phone, or transaction, look up their exact connections across the table.
- If an entity is not connected to another in the table, explicitly state that no direct link is recorded in the evidence.
- Maintain an investigative, clear, and objective tone.
"""

        formatted_contents = []
        formatted_contents.append(f"SYSTEM CONTEXT:\n{system_instruction}\n")

        if chat_history:
            for msg in chat_history[-6:]:  # Keep recent turns
                role = msg.get("role", "user")
                text = msg.get("content", "")
                formatted_contents.append(f"{role.upper()}: {text}")

        formatted_contents.append(f"USER: {question}")

        return self._generate_with_fallback("\n\n".join(formatted_contents))


# Singleton instance
gemini_engine = GeminiIntelligenceEngine()

