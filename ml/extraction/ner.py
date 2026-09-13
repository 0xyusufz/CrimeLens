"""Named entity recognition interface (Foundation stub)."""

from shared.schemas.models import EntityMention


def extract_named_entities(text: str, document_id: str) -> list[EntityMention]:
    """Extract named entities (PERSON, LOCATION, ORGANIZATION) from text.

    To be implemented in future entity extraction phase.
    """
    return []
