"""Regex-based entity extraction (PHONE, BANK_ACCOUNT, VEHICLE) (Foundation stub)."""

from shared.schemas.models import EntityMention


def extract_regex_entities(text: str, document_id: str) -> list[EntityMention]:
    """Extract pattern-based entities (PHONE, BANK_ACCOUNT, VEHICLE) from text.

    To be implemented in future entity extraction phase.
    """
    return []
