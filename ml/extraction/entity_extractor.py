"""Unified entity extraction coordinator (Foundation stub)."""

from shared.schemas.models import EntityMention
from ml.extraction.ner import extract_named_entities
from ml.extraction.regex import extract_regex_entities


def extract_entities(text: str, document_id: str) -> list[EntityMention]:
    """Coordinate NER and regex extraction pipelines.

    To be expanded in future entity extraction phase.
    """
    mentions: list[EntityMention] = []
    mentions.extend(extract_named_entities(text, document_id))
    mentions.extend(extract_regex_entities(text, document_id))
    return mentions
