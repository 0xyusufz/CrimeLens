"""Named Entity Recognition (NER) module for CrimeLens.

Extracts:
- PERSON
- ORGANIZATION
- LOCATION
- EVENT

Implements lightweight deterministic pattern-driven NER matching the project's
synthetic data, with pluggable runner support for future NLP model integration.
Does NOT perform entity resolution or database operations.
"""

import re
from typing import Callable, Optional

from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention

# PERSON patterns
# Matches labeled names, e.g. "Person: Rahul Kumar", "Suspects listed: Rahul Kumar"
PERSON_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:PERSON|Person|Suspect|Complainant|Accused|Officer|Witness|Victim)s?(?:\s+(?:listed|named|identified))?[\s:=-]+"
    r"([A-Z\u0900-\u097F][a-z\u0900-\u097F.'-]*(?:\s+[A-Z\u0900-\u097F][a-z\u0900-\u097F.'-]*){0,3})"
)
PERSON_TITLE_PATTERN = re.compile(
    r"\b(?:Mr\.|Mrs\.|Ms\.|Shri|Smt\.|Dr\.|Insp\.|Inspector|Sub-Inspector|SI|Constable)\s+"
    r"([A-Z\u0900-\u097F][a-z\u0900-\u097F.'-]*(?:\s+[A-Z\u0900-\u097F][a-z\u0900-\u097F.'-]*){1,3})\b"
)
PERSON_CONTEXT_PATTERN = re.compile(
    r"(?i)\b(?:called|met|contacted)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b"
)
# Standalone capitalized multi-word names (e.g. "Rahul Kumar", "Rahul K.", "Amit Kumar")
CAPITALIZED_NAME_PATTERN = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z](?:[a-z]+|\.?)){1,2})(?=$|[\s,;:])"
)

# Non-person words/phrases to reject from generic capitalized name pattern
NON_PERSON_TOKENS = {
    "first information", "case report", "police station", "cyber cell",
    "incident report", "investigation summary", "call record", "case file",
    "meeting on", "city park", "central station", "mumbai central",
    "registered employer", "abc logistics", "january", "february", "march",
    "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday", "listed", "suspects listed",
}

# ORGANIZATION patterns
ORG_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:ORGANIZATION|Organization|Org|Company|Agency|Department)[\s:=-]+"
    r"([A-Za-z0-9\u0900-\u097F][A-Za-z0-9\u0900-\u097F\s.&'-]{2,50})"
)
ORG_SUFFIX_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&.\s]{1,40}\s+(?:Pvt\s+Ltd|Ltd|LLC|LLP|Inc|Corp|Corporation|Bank|Logistics|Industries|Enterprises))\b"
)
ORG_UNIT_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z\s]{2,30}\s+(?:Police Station|Cyber Cell|Department|Branch))\b"
)

# LOCATION patterns
LOC_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:LOCATION|Location|Place|City|State|Address)[\s:=-]+"
    r"([A-Za-z\u0900-\u097F][A-Za-z0-9\u0900-\u097F\s,.-]{2,40})"
)
KNOWN_LOCATIONS = {
    "Bhubaneswar", "Cuttack", "Mumbai", "Delhi", "Bangalore", "Bengaluru",
    "Kolkata", "Hyderabad", "Chennai", "Odisha", "Maharashtra", "Karnataka",
    "City Park", "Central Station", "Sector 5",
}

# EVENT patterns
EVENT_LABEL_PATTERN = re.compile(
    r"(?i)\b(?:EVENT|Event|Incident)[\s:=-]+"
    r"([A-Za-z0-9\u0900-\u097F][A-Za-z0-9\u0900-\u097F\s,.-]{3,60})"
)
EVENT_PHRASE_PATTERN = re.compile(
    r"\b((?:Meeting|Transaction|Call|Seizure operation|Raid)\s+(?:on\s+\d{4}-\d{2}-\d{2}|at\s+[A-Za-z\s]+))\b"
)

# Common words to trim from ends of extracted names
TRIM_WORDS = {
    "was", "is", "are", "were", "and", "or", "attended", "seen", "held", "near",
    "at", "in", "to", "from", "on", "the", "a", "an", "listed", "उपस्थित", "थे",
    "था", "थी", "है", "हैं", "के", "को", "ने", "से", "पर",
}


def clean_entity_name(name: str) -> str:
    """Clean punctuation and trailing words from extracted names."""
    cleaned = name.strip(" \t\r\n.,;:=-।")
    # Take first line if multiline
    cleaned = cleaned.split("\n")[0].strip()
    words = cleaned.split()
    while words and words[-1].lower() in TRIM_WORDS:
        words.pop()
    while words and words[0].lower() in TRIM_WORDS:
        words.pop(0)
    return re.sub(r"\s+", " ", " ".join(words)).strip(" \t\r\n.,;:=-।")


def extract_named_entities(
    text: str,
    document_id: str = "",
    ner_runner: Optional[Callable[[str], list[EntityMention]]] = None,
) -> list[EntityMention]:
    """Extract named entities (PERSON, ORGANIZATION, LOCATION, EVENT) from text.

    Args:
        text: Normalized document text.
        document_id: Optional document staging ID.
        ner_runner: Optional external model hook for testing or model integration.

    Returns:
        list[EntityMention]: Extracted candidates with temporary mention IDs.
    """
    if not text or not text.strip():
        return []

    # If external pluggable NER runner provided, use it
    if ner_runner is not None:
        return ner_runner(text)

    candidates: list[EntityMention] = []
    seen: set[tuple[str, str]] = set()

    def add_candidate(etype: EntityType, raw_name: str, conf: float):
        norm_name = clean_entity_name(raw_name)
        if norm_name and len(norm_name) >= 2 and norm_name.lower() not in NON_PERSON_TOKENS:
            key = (etype.value, norm_name)
            if key not in seen:
                seen.add(key)
                candidates.append(
                    EntityMention(
                        id="mention_candidate",
                        type=etype,
                        name=norm_name,
                        confidence=conf,
                    )
                )

    # 1. PERSON extraction
    for match in PERSON_LABEL_PATTERN.finditer(text):
        add_candidate(EntityType.PERSON, match.group(1), 0.95)

    for match in PERSON_TITLE_PATTERN.finditer(text):
        add_candidate(EntityType.PERSON, match.group(1), 0.90)

    for match in PERSON_CONTEXT_PATTERN.finditer(text):
        add_candidate(EntityType.PERSON, match.group(1), 0.80)

    for match in CAPITALIZED_NAME_PATTERN.finditer(text):
        candidate_str = match.group(1).strip()
        if candidate_str.lower() not in NON_PERSON_TOKENS and not any(
            candidate_str.lower() == loc.lower() for loc in KNOWN_LOCATIONS
        ):
            add_candidate(EntityType.PERSON, candidate_str, 0.80)

    # 2. ORGANIZATION extraction
    for match in ORG_LABEL_PATTERN.finditer(text):
        add_candidate(EntityType.ORGANIZATION, match.group(1), 0.95)

    for match in ORG_SUFFIX_PATTERN.finditer(text):
        add_candidate(EntityType.ORGANIZATION, match.group(1), 0.88)

    for match in ORG_UNIT_PATTERN.finditer(text):
        add_candidate(EntityType.ORGANIZATION, match.group(1), 0.85)

    # 3. LOCATION extraction
    for match in LOC_LABEL_PATTERN.finditer(text):
        add_candidate(EntityType.LOCATION, match.group(1), 0.95)

    for loc in KNOWN_LOCATIONS:
        pattern = rf"\b{re.escape(loc)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            add_candidate(EntityType.LOCATION, loc, 0.85)

    # 4. EVENT extraction
    for match in EVENT_LABEL_PATTERN.finditer(text):
        add_candidate(EntityType.EVENT, match.group(1), 0.90)

    for match in EVENT_PHRASE_PATTERN.finditer(text):
        add_candidate(EntityType.EVENT, match.group(1), 0.80)

    return candidates
