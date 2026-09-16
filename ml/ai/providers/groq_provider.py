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
1. All Entities (PERSON, ORGANIZATION, LOCATION, PHONE, BANK_ACCOUNT, VEHICLE, EVENT)
2. Network Connections / Relationships between them (who is connected to whom, why, and the exact evidence snippet)

Allowed Entity Types:
- PERSON: Names of individuals (suspects, victims, associates, witnesses)
- PHONE: Phone numbers, mobile numbers
- BANK_ACCOUNT: Bank account numbers, UPI IDs, wallets
- VEHICLE: Vehicle plate numbers, model details
- ORGANIZATION: Companies, gangs, shell firms, departments
- LOCATION: Addresses, hideouts, cities, bank branches
- EVENT: Murders, robberies, meetings, raids, cyberattacks

Allowed Relationship Types:
- CALLED: Phone communications, messages, calls
- SENT_MONEY_TO: Fund transfers, hawala, bribes, wire transfers
- OWNS_VEHICLE: Registered owner of car/bike/truck
- USED_VEHICLE: Observed driving or traveling in vehicle
- WORKS_FOR: Employment or subordinate relationship
- LOCATED_AT: Residing, operating, or spotted at location
- ASSOCIATED_WITH: Conspirators, partners, accomplices, family ties
- PART_OF_EVENT: Participant, perpetrator, or victim of crime event

CRITICAL INSTRUCTIONS:
- You must output ONLY valid JSON in the exact format shown below.
- Do not include conversational markdown, greetings, or explanations outside the JSON.
- Every relationship MUST cite an exact verbatim snippet from the text proving the connection.
- Normalize entity names cleanly (e.g., 'Rajesh Kumar', '+919876543210', 'ICICI982134').

OUTPUT JSON FORMAT:
{
  "entities": [
    {"name": "Rajesh Kumar", "type": "PERSON", "confidence": 0.95},
    {"name": "Apex Shell Corp", "type": "ORGANIZATION", "confidence": 0.92}
  ],
  "relationships": [
    {
      "source": "Rajesh Kumar",
      "target": "Apex Shell Corp",
      "type": "WORKS_FOR",
      "evidence": "Rajesh Kumar served as dummy director for Apex Shell Corp",
      "confidence": 0.9
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
        max_completion_tokens: int = 8192,
        reasoning_effort: str = "medium",
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

        # Split text into chunks if it exceeds 24,000 characters (~5,000-6,000 tokens)
        chunk_size = 22000
        overlap = 2000
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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_completion_tokens=self.max_completion_tokens,
            reasoning_effort=self.reasoning_effort,
        )

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
        except Exception as e:
            logger.warning(f"Failed to parse Groq extraction JSON: {e}. Output snippet: {raw_output[:200]}")
            return [], []


# Global singleton instance
groq_extractor = GroqNetworkExtractor()
