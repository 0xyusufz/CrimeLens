"""Entity resolution proposal generator.

Emits ResolutionProposal objects with ML grouping keys (canonical_entity_id, e.g. 'entity_001')
and detected signals. ML only proposes resolution; backend/PostgreSQL decides final canonicalization
and mints database UUIDs.
Name-only fuzzy matching must NEVER automatically merge entities.
"""

from collections import defaultdict
from difflib import SequenceMatcher
import re
from typing import Any, Optional

from shared.schemas.enums import EntityType, ResolutionSignal
from shared.schemas.models import EntityMention, Relationship, ResolutionProposal


def normalize_phone(phone_str: str) -> str:
    """Normalize phone number to uniform digit format.

    Handles +91 prefix, leading 0, spaces, hyphens, and parentheses.
    """
    digits = re.sub(r"\D", "", phone_str)
    if digits.startswith("91") and len(digits) == 12:
        return digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        return digits[1:]
    return digits


def normalize_account(acc_str: str) -> str:
    """Normalize bank account identifier by stripping spaces and hyphens."""
    return re.sub(r"[\s-]", "", acc_str).strip()


def normalize_vehicle(veh_str: str) -> str:
    """Normalize vehicle registration number by stripping spaces/hyphens and uppercasing."""
    return re.sub(r"[\s-]", "", veh_str).strip().upper()


def normalize_org(org_str: str) -> str:
    """Normalize organization name by stripping corporate suffixes and punctuation."""
    cleaned = re.sub(r"(?i)\b(?:pvt\s+ltd|ltd|llc|llp|inc|corp|corporation)\b", "", org_str)
    cleaned = re.sub(r"[^\w\s]", "", cleaned).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def normalize_location(loc_str: str) -> str:
    """Normalize location name by standardizing case and whitespace."""
    cleaned = re.sub(r"[^\w\s]", "", loc_str).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def normalize_person_name(name_str: str) -> str:
    """Normalize person name by removing titles/honorifics and standardizing spaces."""
    cleaned = re.sub(
        r"\b(?:Mr\.|Mrs\.|Ms\.|Shri|Smt\.|Dr\.|Insp\.|Inspector|Sub-Inspector|SI|Constable)\s+",
        "",
        name_str,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[^\w\s.]", "", cleaned).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def is_name_fuzzy_match(norm_a: str, norm_b: str) -> bool:
    """Conservative check if two normalized person names are candidate fuzzy/abbreviation matches."""
    if not norm_a or not norm_b:
        return False
    w1 = norm_a.replace(".", "").split()
    w2 = norm_b.replace(".", "").split()
    if not w1 or not w2:
        return False
    # First name must match
    if w1[0] != w2[0]:
        return False
    # Abbreviated last name (e.g. "rahul kumar" vs "rahul k")
    if len(w1) == len(w2) and len(w1) >= 2:
        if (len(w1[1]) == 1 and w2[1].startswith(w1[1])) or (len(w2[1]) == 1 and w1[1].startswith(w2[1])):
            return True
    # Substring / Prefix match for multi-word full names (e.g. "sushant singh" vs "sushant singh rajput")
    if len(w1) >= 2 and len(w2) >= 2:
        shorter, longer = (w1, w2) if len(w1) < len(w2) else (w2, w1)
        if longer[:len(shorter)] == shorter:
            return True
    # Single-word first name vs multi-word (e.g. "rahul" vs "rahul kumar")
    if len(w1) == 1 or len(w2) == 1:
        if w1[0] == w2[0]:
            return True
    # Minor spelling variation
    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    return ratio >= 0.85


def _get_entity_attributes(
    entity: EntityMention,
    context: Optional[dict[str, Any]] = None,
    relationships: Optional[list[Relationship]] = None,
    entity_map: Optional[dict[str, EntityMention]] = None,
) -> dict[str, set[str]]:
    """Extract normalized auxiliary attributes (phone, account, vehicle, org, loc) for a mention."""
    attrs: dict[str, set[str]] = {
        "phones": set(),
        "accounts": set(),
        "vehicles": set(),
        "orgs": set(),
        "locations": set(),
    }

    # 1. Attributes from context dictionary
    if context:
        ctx_data: dict[str, Any] = {}
        if entity.id in context and isinstance(context[entity.id], dict):
            ctx_data.update(context[entity.id])
        elif entity.name in context and isinstance(context[entity.name], dict):
            ctx_data.update(context[entity.name])
        mention_attrs = context.get("mention_attributes")
        if isinstance(mention_attrs, dict) and entity.id in mention_attrs:
            ctx_data.update(mention_attrs[entity.id])

        if "phone" in ctx_data:
            p = str(ctx_data["phone"]).strip()
            if p:
                attrs["phones"].add(normalize_phone(p))
        if "phones" in ctx_data and isinstance(ctx_data["phones"], (list, set)):
            for p in ctx_data["phones"]:
                attrs["phones"].add(normalize_phone(str(p)))

        if "account" in ctx_data:
            a = str(ctx_data["account"]).strip()
            if a:
                attrs["accounts"].add(normalize_account(a))
        if "accounts" in ctx_data and isinstance(ctx_data["accounts"], (list, set)):
            for a in ctx_data["accounts"]:
                attrs["accounts"].add(normalize_account(str(a)))

        if "vehicle" in ctx_data:
            v = str(ctx_data["vehicle"]).strip()
            if v:
                attrs["vehicles"].add(normalize_vehicle(v))

        if "organization" in ctx_data or "org" in ctx_data:
            o = str(ctx_data.get("organization") or ctx_data.get("org")).strip()
            if o:
                attrs["orgs"].add(normalize_org(o))

        if "location" in ctx_data:
            l = str(ctx_data["location"]).strip()
            if l:
                attrs["locations"].add(normalize_location(l))

    # 2. Attributes inferred from Phase 5 relationships
    if relationships and entity_map:
        for rel in relationships:
            other_id = None
            if rel.source_entity_id == entity.id:
                other_id = rel.target_entity_id
            elif rel.target_entity_id == entity.id:
                other_id = rel.source_entity_id

            if other_id and other_id in entity_map:
                other = entity_map[other_id]
                if other.type == EntityType.PHONE:
                    attrs["phones"].add(normalize_phone(other.name))
                elif other.type == EntityType.BANK_ACCOUNT:
                    attrs["accounts"].add(normalize_account(other.name))
                elif other.type == EntityType.VEHICLE:
                    attrs["vehicles"].add(normalize_vehicle(other.name))
                elif other.type == EntityType.ORGANIZATION:
                    attrs["orgs"].add(normalize_org(other.name))
                elif other.type == EntityType.LOCATION:
                    attrs["locations"].add(normalize_location(other.name))

    return attrs


def compare_mentions(
    mention_a: EntityMention,
    mention_b: EntityMention,
    context: Optional[dict[str, Any]] = None,
    relationships: Optional[list[Relationship]] = None,
    entity_map: Optional[dict[str, EntityMention]] = None,
    allow_fuzzy_name: bool = True,
) -> Optional[tuple[float, list[ResolutionSignal]]]:
    """Compare two entity mentions and return (confidence, signals) if they resolve, or None."""
    # 1. Type safety check: incompatible entity types never resolve
    if mention_a.type != mention_b.type:
        return None

    etype = mention_a.type

    # 2. Strong identifier matching for non-PERSON entities
    if etype == EntityType.PHONE:
        p1 = normalize_phone(mention_a.name)
        p2 = normalize_phone(mention_b.name)
        if p1 and p2 and p1 == p2:
            return (0.95, [ResolutionSignal.PHONE_MATCH])
        return None

    if etype == EntityType.BANK_ACCOUNT:
        a1 = normalize_account(mention_a.name)
        a2 = normalize_account(mention_b.name)
        if a1 and a2 and a1 == a2:
            return (0.95, [ResolutionSignal.ACCOUNT_MATCH])
        return None

    if etype == EntityType.VEHICLE:
        v1 = normalize_vehicle(mention_a.name)
        v2 = normalize_vehicle(mention_b.name)
        if v1 and v2 and v1 == v2:
            return (0.95, [ResolutionSignal.VEHICLE_MATCH])
        return None

    if etype == EntityType.ORGANIZATION:
        o1 = normalize_org(mention_a.name)
        o2 = normalize_org(mention_b.name)
        if o1 and o2:
            if o1 == o2:
                return (0.90, [ResolutionSignal.ORGANIZATION_MATCH])
            words1 = o1.split()
            words2 = o2.split()
            acronym1 = "".join(w[0] for w in words1 if w)
            acronym2 = "".join(w[0] for w in words2 if w)
            if (o1 in o2 or o2 in o1) or (len(acronym1) >= 2 and (acronym1 == o2 or acronym1 == acronym2)) or (len(acronym2) >= 2 and (acronym2 == o1)):
                return (0.88, [ResolutionSignal.ORGANIZATION_MATCH])
        return None

    if etype == EntityType.LOCATION:
        l1 = normalize_location(mention_a.name)
        l2 = normalize_location(mention_b.name)
        if l1 and l2 and l1 == l2:
            return (0.85, [ResolutionSignal.LOCATION_MATCH])
        return None

    if etype == EntityType.EVENT:
        e1 = mention_a.name.strip().lower()
        e2 = mention_b.name.strip().lower()
        if e1 and e2 and e1 == e2:
            return (0.80, [ResolutionSignal.NAME_SIMILARITY])
        return None

    # 3. PERSON matching with multi-signal and conflict handling
    if etype == EntityType.PERSON:
        attrs_a = _get_entity_attributes(mention_a, context, relationships, entity_map)
        attrs_b = _get_entity_attributes(mention_b, context, relationships, entity_map)

        # Conflict check: conflicting phone numbers prevent resolution
        if attrs_a["phones"] and attrs_b["phones"] and attrs_a["phones"].isdisjoint(attrs_b["phones"]):
            return None

        # Conflict check: conflicting bank accounts prevent resolution
        if attrs_a["accounts"] and attrs_b["accounts"] and attrs_a["accounts"].isdisjoint(attrs_b["accounts"]):
            return None

        norm_a = normalize_person_name(mention_a.name)
        norm_b = normalize_person_name(mention_b.name)

        is_exact_name = (norm_a == norm_b)
        is_fuzzy = False
        if not is_exact_name and allow_fuzzy_name:
            is_fuzzy = is_name_fuzzy_match(norm_a, norm_b)

        if not is_exact_name and not is_fuzzy:
            return None

        signals: list[ResolutionSignal] = [ResolutionSignal.NAME_SIMILARITY]

        # Auxiliary signals
        has_phone_match = bool(attrs_a["phones"] & attrs_b["phones"])
        has_account_match = bool(attrs_a["accounts"] & attrs_b["accounts"])
        has_vehicle_match = bool(attrs_a["vehicles"] & attrs_b["vehicles"])
        has_org_match = bool(attrs_a["orgs"] & attrs_b["orgs"])
        has_loc_match = bool(attrs_a["locations"] & attrs_b["locations"])

        if has_phone_match:
            signals.append(ResolutionSignal.PHONE_MATCH)
        if has_account_match:
            signals.append(ResolutionSignal.ACCOUNT_MATCH)
        if has_vehicle_match:
            signals.append(ResolutionSignal.VEHICLE_MATCH)
        if has_org_match:
            signals.append(ResolutionSignal.ORGANIZATION_MATCH)
        if has_loc_match:
            signals.append(ResolutionSignal.LOCATION_MATCH)

        # Scoring hierarchy
        if is_exact_name:
            if has_phone_match or has_account_match:
                confidence = 0.98  # Multi-signal strong match
            elif has_vehicle_match or has_org_match or has_loc_match:
                confidence = 0.92
            else:
                confidence = 0.80  # Exact name only
        else:
            # Name-only fuzzy matching: conservative review suggestion
            if has_phone_match or has_account_match:
                confidence = 0.90  # Strong identifier reinforces fuzzy name
            elif has_vehicle_match or has_org_match:
                confidence = 0.85
            else:
                confidence = 0.60  # Name-only fuzzy: review suggestion only, never auto-merge

        return (confidence, signals)

    return None


def propose_resolutions(
    entities: list[EntityMention],
    relationships: Optional[list[Relationship]] = None,
    context: Optional[dict[str, Any]] = None,
    min_confidence: float = 0.70,
    allow_fuzzy_name: bool = True,
) -> list[ResolutionProposal]:
    """Generate safe, explainable entity resolution proposals for backend evaluation.

    Args:
        entities: List of EntityMention candidates to evaluate for resolution.
        relationships: Optional Phase 5 relationships used as supporting context.
        context: Optional dictionary with auxiliary attributes or document metadata.
        min_confidence: Minimum confidence threshold to emit proposals (default 0.70).
            Note: Name-only fuzzy matching produces confidence=0.60, so it will NOT
            auto-propose unless min_confidence is lowered to <= 0.60 for review mode.
        allow_fuzzy_name: Whether to consider fuzzy name matches as candidate review proposals.

    Returns:
        list[ResolutionProposal]: Validated proposals with ML staging grouping keys
            (canonical_entity_id, e.g. 'entity_001') and supporting signals.
    """
    if not entities or len(entities) < 2:
        return []

    entity_map = {e.id: e for e in entities}

    # Group entities by EntityType
    by_type: dict[EntityType, list[EntityMention]] = defaultdict(list)
    for e in entities:
        by_type[e.type].append(e)

    # Graph adjacency: mention_id -> list of (neighbor_id, confidence, signals)
    adj: dict[str, list[tuple[str, float, list[ResolutionSignal]]]] = defaultdict(list)

    # Evaluate pairwise within each entity type
    for etype, mention_list in by_type.items():
        if len(mention_list) < 2:
            continue
        n = len(mention_list)
        for i in range(n):
            for j in range(i + 1, n):
                m_a = mention_list[i]
                m_b = mention_list[j]
                res = compare_mentions(
                    m_a,
                    m_b,
                    context=context,
                    relationships=relationships,
                    entity_map=entity_map,
                    allow_fuzzy_name=allow_fuzzy_name,
                )
                if res is not None:
                    conf, signals = res
                    if conf >= min_confidence:
                        adj[m_a.id].append((m_b.id, conf, signals))
                        adj[m_b.id].append((m_a.id, conf, signals))

    if not adj:
        return []

    # Find connected components deterministically
    visited: set[str] = set()
    components: list[list[str]] = []

    all_matched_ids = sorted(adj.keys())
    for mid in all_matched_ids:
        if mid not in visited:
            comp: list[str] = []
            queue = [mid]
            visited.add(mid)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor, _, _ in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(sorted(comp))

    # Generate proposals for each connected component
    proposals: list[ResolutionProposal] = []
    cluster_counter = 1

    for comp in components:
        if len(comp) < 2:
            continue

        canonical_id = f"entity_{cluster_counter:03d}"
        cluster_counter += 1

        for mid in comp:
            incident_confs = [c for neighbor_id, c, _ in adj[mid] if neighbor_id in comp]
            mention_conf = max(incident_confs) if incident_confs else 0.70

            mention_signals_set = set()
            for neighbor_id, _, sigs in adj[mid]:
                if neighbor_id in comp:
                    mention_signals_set.update(sigs)

            sorted_signals = sorted(list(mention_signals_set), key=lambda s: s.value)

            proposals.append(
                ResolutionProposal(
                    canonical_entity_id=canonical_id,
                    mention_id=mid,
                    confidence=round(mention_conf, 4),
                    signals=sorted_signals,
                )
            )

    return proposals
