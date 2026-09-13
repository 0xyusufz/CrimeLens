"""Entity resolution proposal generator (Foundation stub).

Emits ResolutionProposal objects with ML grouping keys and detected signals.
Name-only fuzzy matching must NEVER auto-merge.
Backend makes all final canonicalization decisions and mints UUIDs.
"""

from shared.schemas.models import EntityMention, ResolutionProposal


def propose_resolutions(entities: list[EntityMention]) -> list[ResolutionProposal]:
    """Generate entity resolution proposals for backend evaluation.

    To be implemented in future entity resolution phase.
    """
    return []
