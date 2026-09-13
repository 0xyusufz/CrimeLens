"""Rule-based relationship extraction (Foundation stub)."""

from shared.schemas.models import EntityMention, Relationship


def extract_relationships(
    text: str,
    entities: list[EntityMention],
    document_id: str,
) -> list[Relationship]:
    """Extract relationships between entities from context text.

    To be implemented in future relationship extraction phase.
    """
    return []
