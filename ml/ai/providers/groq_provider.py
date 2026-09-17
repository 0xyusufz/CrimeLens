"""Groq AI Network and Entity Extraction Provider.

Uses Groq with model 'openai/gpt-oss-20b' and reasoning_effort='medium'
to extract high-precision entities and complex network relationships directly
from document text.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from groq import Groq

from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship

load_dotenv()

logger = logging.getLogger("crimelens.ml.groq")

VALID_ENTITY_TYPES = {e.value for e in EntityType}
VALID_RELATIONSHIP_TYPES = {r.value for r in RelationshipType}

SYSTEM_PROMPT = """You are a specialized Law Enforcement and Criminal Intelligence extraction engine.
Your task is to analyze evidence text and extract:
1. High-precision Entities (PERSON, ORGANIZATION, LOCATION, PHONE, BANK_ACCOUNT, VEHICLE, EVENT)
2. Network Connections / Relationships between them (who is connected to whom, why, and the exact evidence snippet)

Allowed Entity Types:
- PERSON: Names of individuals only (e.g. Md. Faizaan Raza Khan, Rajesh Kumar, Smt. Sunita Devi, Punjilal Meher).
  NEVER extract organizations, laboratories, courts, or legal terms as PERSON.
- ORGANIZATION: Companies, forensic laboratories (e.g. State Forensic Science Laboratory), police stations/branches, courts, hospitals, gangs, transport firms.
- LOCATION: Cities, districts, streets, landmarks, addresses (e.g. Gandhi Chowk, Jharsuguda, Patnagarh).
- PHONE: Contact numbers with context (e.g. +919876543210).
- BANK_ACCOUNT: Bank account numbers, UPI IDs, wallets.
- VEHICLE: Vehicle registration numbers, plate numbers (e.g. OD-02-AB-1234).
- EVENT: Specific crime occurrences, meetings, incidents (e.g. Murder of Soumya Sekhar Sahu).

Allowed Relationship Types:
- CALLED: Phone communications, messages, calls
- SENT_MONEY_TO: Fund transfers, payments, wire transfers
- OWNS_VEHICLE: Registered owner of vehicle
- USED_VEHICLE: Observed driving or traveling in vehicle
- WORKS_FOR: Employment or official subordinate relationship
- LOCATED_AT: Residing, operating, or spotted at location
- ASSOCIATED_WITH: Document-supported contacts, accomplices, or family ties
- PART_OF_EVENT: Participant, victim, or perpetrator in an event

CRITICAL NEGATIVE GUARDRAILS & QUALITY RULES:
1. DO NOT extract legal/procedural boilerplate as entities (e.g. "Bail", "Case No", "Evidence Act", "Standing Counsel", "Charge Sheet", "Log Line", "Statements", "Party", "Appellate", "Advocate").
2. DO NOT extract sentence fragments or verbs as entities (e.g. "Reema was referred", "built an improvised", "it must show", "more suspicion").
3. NEVER classify institutions or laboratories like "State Forensic Science", "Crime Branch", "Orissa High Court", or "SCB Medical College" as PERSON. They are ORGANIZATION.
4. NEVER invent relationship semantics. If text says "spoke to" or "called", use CALLED or ASSOCIATED_WITH; do NOT manufacture "gang member" or "criminal associate" unless explicitly stated.
5. Co-occurrence alone is NOT a relationship. Do not connect two entities just because they appear on the same page.
6. Every relationship MUST cite an exact verbatim snippet from the text proving the connection.

OUTPUT JSON FORMAT:
{
  "entities": [
    {"name": "Rajesh Kumar", "type": "PERSON", "confidence": 0.95},
    {"name": "State Forensic Science Laboratory", "type": "ORGANIZATION", "confidence": 0.94}
  ],
  "relationships": [
    {
      "source": "Rajesh Kumar",
      "target": "State Forensic Science Laboratory",
      "type": "ASSOCIATED_WITH",
      "evidence": "Rajesh Kumar submitted samples to the State Forensic Science Laboratory",
      "confidence": 0.92
    }
  ]
}
"""


class GroqNetworkExtractor:
    """Extracts entity networks and relationships from text using Groq openai/gpt-oss-20b."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "openai/gpt-oss-20b",
        temperature: float = 0.2,
        max_completion_tokens: int = 2048,
        reasoning_effort: str = "low",
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Groq extraction will be unavailable.")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.reasoning_effort = reasoning_effort

    def is_available(self) -> bool:
        return self.client is not None

    def extract(
        self,
        text: str,
        document_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extracts entities and relationships from text.

        Handles text of arbitrary size (including 12k+ token files) by chunking if needed.
        Returns:
            tuple[raw_entities, raw_relationships]
        """
        if not text or not text.strip() or not self.is_available():
            return [], []

        # Split text into chunks fitting Groq 8,000 TPM limit (9000 chars ~ 2,000 tokens)
        chunk_size = 9000
        overlap = 1000
        chunks = []
        if len(text) <= chunk_size:
            chunks = [text]
        else:
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(text[start:end])
                if end == len(text):
                    break
                start = end - overlap

        all_entities: list[dict[str, Any]] = []
        all_relationships: list[dict[str, Any]] = []

        for chunk_idx, chunk in enumerate(chunks):
            try:
                chunk_entities, chunk_rels = self._call_groq_extraction(chunk, chunk_idx)
                all_entities.extend(chunk_entities)
                all_relationships.extend(chunk_rels)
            except Exception as e:
                logger.error(f"Groq extraction failed on chunk {chunk_idx}: {e}")

        # Deduplicate entities by (type, normalized_name)
        dedup_entities: dict[tuple[str, str], dict[str, Any]] = {}
        for ent in all_entities:
            name = str(ent.get("name", "")).strip()
            ent_type = str(ent.get("type", "")).strip().upper()
            if not name or ent_type not in VALID_ENTITY_TYPES:
                continue
            conf = float(ent.get("confidence", 0.9))
            key = (ent_type, name.lower())
            if key not in dedup_entities or conf > dedup_entities[key].get("confidence", 0.0):
                dedup_entities[key] = {
                    "name": name,
                    "type": ent_type,
                    "confidence": conf,
                }

        # Deduplicate relationships by (source.lower(), target.lower(), type)
        dedup_rels: dict[tuple[str, str, str], dict[str, Any]] = {}
        for rel in all_relationships:
            src = str(rel.get("source", "")).strip()
            tgt = str(rel.get("target", "")).strip()
            rel_type = str(rel.get("type", "")).strip().upper()
            ev = str(rel.get("evidence", "")).strip()
            conf = float(rel.get("confidence", 0.85))

            if not src or not tgt or rel_type not in VALID_RELATIONSHIP_TYPES:
                continue
            if src.lower() == tgt.lower():
                continue

            key = (src.lower(), tgt.lower(), rel_type)
            if key not in dedup_rels or conf > dedup_rels[key].get("confidence", 0.0):
                dedup_rels[key] = {
                    "source": src,
                    "target": tgt,
                    "type": rel_type,
                    "evidence": ev or f"Extracted connection between {src} and {tgt}.",
                    "confidence": conf,
                }

        return list(dedup_entities.values()), list(dedup_rels.values())

    def _call_groq_extraction(
        self,
        text_chunk: str,
        chunk_idx: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not self.client:
            return [], []

        prompt = f"Analyze the following evidence text carefully and extract all entities and relationships as strict JSON:\n\n---\n{text_chunk}\n---"

        tokens_to_request = min(self.max_completion_tokens, 2048)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_completion_tokens=tokens_to_request,
                reasoning_effort=self.reasoning_effort,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "413" in err_str or "request too large" in err_str or "rate_limit" in err_str:
                logger.warning(f"Groq chunk {chunk_idx} hit token limits ({e}). Retrying with 1024 tokens...")
                # Shorten chunk if needed and reduce completion tokens
                shortened_prompt = f"Analyze the following evidence text carefully and extract all entities and relationships as strict JSON:\n\n---\n{text_chunk[:5000]}\n---"
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": shortened_prompt},
                    ],
                    temperature=self.temperature,
                    max_completion_tokens=1024,
                    reasoning_effort=self.reasoning_effort,
                )
            else:
                raise e

        raw_output = ""
        if response.choices and response.choices[0].message:
            raw_output = response.choices[0].message.content or ""

        return self._parse_json_response(raw_output)

    def _parse_json_response(
        self,
        raw_output: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not raw_output:
            return [], []

        # Find JSON object enclosed in ```json or simply { ... }
        clean = raw_output.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
        if match:
            clean = match.group(1)
        else:
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1 and end > start:
                clean = clean[start : end + 1]

        try:
            data = json.loads(clean)
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            return entities, relationships
        except Exception:
            # Fallback: regex extraction of valid entity and relationship dicts in case of truncation
            entities = []
            relationships = []
            for ent_match in re.finditer(r'\{[^{}]*?"name"\s*:\s*"([^"]+)"[^{}]*?"type"\s*:\s*"([^"]+)"[^{}]*?\}', raw_output):
                try:
                    ent_data = json.loads(ent_match.group(0))
                    entities.append(ent_data)
                except Exception:
                    pass
            for rel_match in re.finditer(r'\{[^{}]*?"source"\s*:\s*"([^"]+)"[^{}]*?"target"\s*:\s*"([^"]+)"[^{}]*?\}', raw_output):
                try:
                    rel_data = json.loads(rel_match.group(0))
                    relationships.append(rel_data)
                except Exception:
                    pass
            if entities or relationships:
                logger.info(f"Salvaged {len(entities)} entities and {len(relationships)} relationships from partial Groq output.")
                return entities, relationships
            logger.warning(f"Failed to parse Groq extraction JSON. Output snippet: {raw_output[:200]}")
            return [], []


# Global singleton instance
groq_extractor = GroqNetworkExtractor()
