"""Precision-first candidate classification before graph-ready entity mentions.

The public schema intentionally has no ROLE enum.  Roles and generic phrases
therefore remain internal classification output instead of being forced into a
PERSON node.  This prevents phrases such as ``English lecturer`` or ``the
driver`` from polluting a case graph.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention


ROLE_TERMS = frozenset(
    {
        "accused", "associate", "brother", "complainant", "constable", "doctor",
        "driver", "employee", "english lecturer", "lecturer", "manager", "officer",
        "professor", "teacher", "victim", "witness", "worker",
    }
)
_ROLE_PATTERN = re.compile(
    r"\b(?:an?|the)\s+((?:[a-z]+\s+){0,2}(?:lecturer|teacher|professor|driver|manager|doctor|employee|worker))\b",
    re.IGNORECASE,
)
_LOCATION_SUFFIXES = frozenset(
    {
        "airport", "bridge", "chowk", "district", "highway", "market", "nagar",
        "police station", "ps", "railway station", "road", "state", "station",
        "street", "terminal", "town", "village"
    }
)
_ORGANIZATION_TERMS = frozenset(
    {
        "academy", "agency", "bank", "board", "branch", "bureau", "cell",
        "center", "centre", "clinic", "college", "commission", "company",
        "corps", "corporation", "counsel", "court", "department", "division",
        "firm", "forensic", "foundation", "hospital", "institute", "laboratory",
        "lab", "limited", "llc", "ltd", "police", "pvt", "school", "science",
        "service", "society", "syndicate", "transport", "trust", "university"
    }
)

LEGAL_BOILERPLATE_TERMS = frozenset(
    {
        "additional district", "advocate", "advocate of", "appellant", "bail",
        "bail application", "case", "case no", "case number", "charge sheet",
        "crpc", "evidence act", "high court", "identification", "investigating",
        "ipc", "judgement copy", "law", "legal provisions", "log line",
        "order sheet", "panchnama", "party", "prosecution", "respondent",
        "sessions court", "standing counsel", "statements", "statute",
        "superintendent", "witness statement"
    }
)

_VERB_OR_FRAGMENT_PATTERN = re.compile(
    r"\b(?:was\s+\w+|acted\s+as|built\s+an?|it\s+must|more\s+suspicion|though\s+\w+|referred\s+to|seen\s+at)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CandidateDecision:
    text: str
    proposed_type: str
    accepted: bool
    reason: str
    attached_to: str | None = None


def _normal_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def _internal_roles(text: str, accepted_mentions: list[EntityMention]) -> list[CandidateDecision]:
    decisions: list[CandidateDecision] = []
    person_names = [mention.name for mention in accepted_mentions if mention.type == EntityType.PERSON]
    for match in _ROLE_PATTERN.finditer(text):
        role = _normal_name(match.group(1))
        prefix = text[max(0, match.start() - 100):match.start()]
        attached_to = None
        for name in person_names:
            if name.casefold() in prefix.casefold():
                attached_to = name
                break
        decisions.append(
            CandidateDecision(
                text=role,
                proposed_type="ROLE",
                accepted=False,
                reason="role_attribute_not_graph_node",
                attached_to=attached_to,
            )
        )
    return decisions


def classify_entity_candidates(
    candidates: Iterable[EntityMention],
    *,
    text: str,
    min_confidence: float,
) -> tuple[list[EntityMention], list[CandidateDecision]]:
    """Accept graph-worthy mentions and retain rejected reasoning internally."""
    candidate_list = list(candidates)
    typed_names = {(candidate.type, _normal_name(candidate.name)) for candidate in candidate_list}
    location_names = {
        _normal_name(candidate.name)
        for candidate in candidate_list
        if candidate.type == EntityType.LOCATION
    }
    accepted: list[EntityMention] = []
    decisions: list[CandidateDecision] = []

    for candidate in candidate_list:
        normalized = _normal_name(candidate.name)
        words = normalized.replace(".", "").split()
        if candidate.confidence < min_confidence:
            decisions.append(CandidateDecision(candidate.name, candidate.type.value, False, "below_confidence_threshold"))
            continue

        # Reject legal boilerplate, case labels, and verb fragments
        if (
            normalized in LEGAL_BOILERPLATE_TERMS
            or any(term == normalized for term in LEGAL_BOILERPLATE_TERMS)
            or _VERB_OR_FRAGMENT_PATTERN.search(normalized)
        ):
            decisions.append(CandidateDecision(candidate.name, "LEGAL_BOILERPLATE", False, "legal_or_procedural_boilerplate"))
            continue

        if candidate.type == EntityType.PERSON:
            if normalized in ROLE_TERMS or any(term == normalized for term in ROLE_TERMS):
                decisions.append(CandidateDecision(candidate.name, "ROLE", False, "generic_role_not_person"))
                continue

            # Reclassify to ORGANIZATION if candidate contains institutional terms (e.g. State Forensic Science, Crime Branch)
            if any(term in words for term in _ORGANIZATION_TERMS) or (EntityType.ORGANIZATION, normalized) in typed_names:
                candidate = candidate.model_copy(update={"type": EntityType.ORGANIZATION})
                decisions.append(CandidateDecision(candidate.name, "ORGANIZATION", True, "reclassified_organization_not_person"))
                accepted.append(candidate)
                continue

            final_token = words[-1] if words else ""
            if final_token in _LOCATION_SUFFIXES or (EntityType.LOCATION, normalized) in typed_names:
                candidate = candidate.model_copy(update={"type": EntityType.LOCATION})
                decisions.append(CandidateDecision(candidate.name, "LOCATION", True, "reclassified_location_not_person"))
                accepted.append(candidate)
                continue

            # A one-token name is retained as a low-confidence mention for
            # corroboration, but it is never elevated by this classifier.
            if len(words) == 1 and candidate.confidence > 0.65:
                candidate = candidate.model_copy(update={"confidence": 0.65})
                decisions.append(CandidateDecision(candidate.name, "PERSON", True, "weak_single_token_identity"))
            else:
                decisions.append(CandidateDecision(candidate.name, "PERSON", True, "identity_candidate"))
        elif candidate.type == EntityType.LOCATION and any(
            longer.startswith(normalized + " ")
            for longer in location_names
            if longer != normalized
        ):
            decisions.append(
                CandidateDecision(
                    candidate.name,
                    "LOCATION",
                    False,
                    "less_specific_location_covered_by_specific_mention",
                )
            )
            continue
        else:
            decisions.append(CandidateDecision(candidate.name, candidate.type.value, True, "typed_identifier_or_context"))
        accepted.append(candidate)

    decisions.extend(_internal_roles(text, accepted))
    return accepted, decisions


__all__ = ["CandidateDecision", "ROLE_TERMS", "classify_entity_candidates"]
