"""Regex-based entity extraction for structured identifiers.

Extracts:
- PHONE
- BANK_ACCOUNT
- VEHICLE

Produces candidates conforming to the EntityMention contract.
Does NOT perform entity resolution or database operations.
"""

import re
from typing import Optional

from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention

# Regex patterns
PHONE_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:PHONE|Phone|Mobile|Contact|Tel)[\s:=-]+([+]?[0-9][0-9\s-]{8,15}[0-9])"
)
PHONE_STANDALONE_PATTERN = re.compile(
    r"(?:^|(?<=[\s,;:(]))([+]91[- ]?[6-9]\d{4}[- ]?\d{5}|[6-9]\d{9})(?=$|[\s,;:.)])"
)

BANK_ACCOUNT_PATTERN = re.compile(
    r"(?i)\b(?:ACCOUNT|Account|A/C|Acct|ACC)[\s:#No.-]+([0-9]{9,18})\b"
)

VEHICLE_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:VEHICLE|Vehicle|Reg No|Vehicle No)[\s:=-]+([A-Z]{2}[ -]?[0-9]{1,2}[ -]?[A-Z]{1,3}[ -]?[0-9]{4})\b"
)
VEHICLE_STANDALONE_PATTERN = re.compile(
    r"\b([A-Z]{2}[ -]?[0-9]{1,2}[ -]?[A-Z]{1,3}[ -]?[0-9]{4})\b"
)

# Known state codes in India to avoid false positive matches on arbitrary uppercase text
INDIAN_STATE_CODES = {
    "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ", "HP", "HR",
    "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL", "OD",
    "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB",
}


def normalize_phone(phone_str: str) -> str:
    """Normalize phone string to a standard readable format while preserving digits."""
    return re.sub(r"\s+", " ", phone_str.strip())


def normalize_vehicle(vehicle_str: str) -> str:
    """Normalize vehicle registration to uppercase with uniform single spaces."""
    cleaned = re.sub(r"[-]+", " ", vehicle_str.strip().upper())
    return re.sub(r"\s+", " ", cleaned)


def extract_regex_entities(text: str, document_id: str = "") -> list[EntityMention]:
    """Extract structured identifier entities (PHONE, BANK_ACCOUNT, VEHICLE) from text.

    Args:
        text: Normalized document text.
        document_id: Optional document staging ID.

    Returns:
        list[EntityMention]: Extracted candidates with temporary mention IDs.
    """
    if not text or not text.strip():
        return []

    candidates: list[EntityMention] = []
    seen_identifiers: set[tuple[str, str]] = set()

    # 1. PHONE extraction
    for match in PHONE_LABEL_PATTERN.finditer(text):
        raw_val = match.group(1).strip()
        norm_val = normalize_phone(raw_val)
        key = (EntityType.PHONE.value, norm_val)
        if key not in seen_identifiers:
            seen_identifiers.add(key)
            candidates.append(
                EntityMention(
                    id="mention_candidate",
                    type=EntityType.PHONE,
                    name=norm_val,
                    confidence=0.95,
                )
            )

    for match in PHONE_STANDALONE_PATTERN.finditer(text):
        raw_val = match.group(1).strip()
        norm_val = normalize_phone(raw_val)
        key = (EntityType.PHONE.value, norm_val)
        if key not in seen_identifiers:
            seen_identifiers.add(key)
            candidates.append(
                EntityMention(
                    id="mention_candidate",
                    type=EntityType.PHONE,
                    name=norm_val,
                    confidence=0.90,
                )
            )

    # 2. BANK_ACCOUNT extraction
    for match in BANK_ACCOUNT_PATTERN.finditer(text):
        raw_val = match.group(1).strip()
        key = (EntityType.BANK_ACCOUNT.value, raw_val)
        if key not in seen_identifiers:
            seen_identifiers.add(key)
            candidates.append(
                EntityMention(
                    id="mention_candidate",
                    type=EntityType.BANK_ACCOUNT,
                    name=raw_val,
                    confidence=0.95,
                )
            )

    # 3. VEHICLE extraction
    for match in VEHICLE_LABEL_PATTERN.finditer(text):
        raw_val = match.group(1).strip()
        norm_val = normalize_vehicle(raw_val)
        key = (EntityType.VEHICLE.value, norm_val)
        if key not in seen_identifiers:
            seen_identifiers.add(key)
            candidates.append(
                EntityMention(
                    id="mention_candidate",
                    type=EntityType.VEHICLE,
                    name=norm_val,
                    confidence=0.95,
                )
            )

    for match in VEHICLE_STANDALONE_PATTERN.finditer(text):
        raw_val = match.group(1).strip()
        prefix = raw_val[:2].upper()
        if prefix in INDIAN_STATE_CODES:
            norm_val = normalize_vehicle(raw_val)
            key = (EntityType.VEHICLE.value, norm_val)
            if key not in seen_identifiers:
                seen_identifiers.add(key)
                candidates.append(
                    EntityMention(
                        id="mention_candidate",
                        type=EntityType.VEHICLE,
                        name=norm_val,
                        confidence=0.90,
                    )
                )

    return candidates
