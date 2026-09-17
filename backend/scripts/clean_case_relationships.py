"""Clean up junk entities, pronouns, legal citations, and merge duplicates in a case."""

import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.relationship import RelationshipStaging
from app.graph.projection import project_case_graph

JUNK_NAMES = {
    "who", "by", "whom", "whose", "which", "what", "that", "this", "these", "those",
    "he", "she", "it", "they", "them", "him", "her", "his", "their", "theirs", "its",
    "4y", "11thwards", "the sting", "sound of furniture's rustle", "childhood's daughter",
    "public nompario", "and mita/baba",
    # Legal precedent citations (Supreme Court cases cited in court order)
    "pedda narayana", "kodali purnachandra rao", "kishwar jahan",
}


def clean_case(case_id_str: str = "d548fa6c-9f01-4c1b-96a6-0d9c227d20fe"):
    case_id = uuid.UUID(case_id_str)
    with SessionLocal() as db:
        print(f"Cleaning case {case_id}...")

        # 1. Delete relationships connected to junk entities
        links = db.query(EntityCaseLink).filter(EntityCaseLink.case_id == case_id).all()
        entity_ids = [l.entity_id for l in links]
        entities = db.query(Entity).filter(Entity.id.in_(entity_ids)).all() if entity_ids else []

        junk_entity_ids = set()
        for e in entities:
            norm = e.canonical_name.strip().lower()
            if norm in JUNK_NAMES or norm.startswith("vs.") or norm.startswith("state of") or len(norm) <= 1:
                junk_entity_ids.add(e.id)
                print(f"  Flagged junk entity: [{e.type.value}] '{e.canonical_name}' ({e.id})")

        if junk_entity_ids:
            deleted_rels = db.query(RelationshipStaging).filter(
                RelationshipStaging.case_id == case_id,
                (RelationshipStaging.source_entity_id.in_(junk_entity_ids) | RelationshipStaging.target_entity_id.in_(junk_entity_ids))
            ).delete(synchronize_session=False)
            print(f"  Deleted {deleted_rels} junk relationships.")

            # Delete mentions and links
            db.query(EntityMention).filter(EntityMention.entity_id.in_(junk_entity_ids)).delete(synchronize_session=False)
            db.query(EntityCaseLink).filter(EntityCaseLink.case_id == case_id, EntityCaseLink.entity_id.in_(junk_entity_ids)).delete(synchronize_session=False)
            print(f"  Deleted {len(junk_entity_ids)} junk entity case links.")

        # 2. Merge Duplicate Entities (Sushant Singh -> Sushant Singh Rajput)
        ssr = db.query(Entity).filter(Entity.canonical_name == "Sushant Singh Rajput").first()
        ss = db.query(Entity).filter(Entity.canonical_name == "Sushant Singh").first()
        if ssr and ss and ssr.id != ss.id:
            print(f"  Merging 'Sushant Singh' ({ss.id}) -> 'Sushant Singh Rajput' ({ssr.id})...")
            # Point relationships to ssr
            db.query(RelationshipStaging).filter(RelationshipStaging.case_id == case_id, RelationshipStaging.source_entity_id == ss.id).update(
                {"source_entity_id": ssr.id}, synchronize_session=False
            )
            db.query(RelationshipStaging).filter(RelationshipStaging.case_id == case_id, RelationshipStaging.target_entity_id == ss.id).update(
                {"target_entity_id": ssr.id}, synchronize_session=False
            )
            # Remove duplicate self-loops if any
            db.query(RelationshipStaging).filter(RelationshipStaging.case_id == case_id, RelationshipStaging.source_entity_id == ssr.id, RelationshipStaging.target_entity_id == ssr.id).delete(synchronize_session=False)
            db.query(EntityCaseLink).filter(EntityCaseLink.case_id == case_id, EntityCaseLink.entity_id == ss.id).delete(synchronize_session=False)
            print("  Sushant Singh merged successfully.")

        # 3. Merge Duplicate Entities (CBI -> Central Bureau of Investigation (CBI))
        cbi_full = db.query(Entity).filter(Entity.canonical_name.ilike("%Central Bureau of Investigation%")).first()
        cbi_short = db.query(Entity).filter(Entity.canonical_name == "CBI").first()
        if cbi_full and cbi_short and cbi_full.id != cbi_short.id:
            print(f"  Merging 'CBI' ({cbi_short.id}) -> '{cbi_full.canonical_name}' ({cbi_full.id})...")
            db.query(RelationshipStaging).filter(RelationshipStaging.case_id == case_id, RelationshipStaging.source_entity_id == cbi_short.id).update(
                {"source_entity_id": cbi_full.id}, synchronize_session=False
            )
            db.query(RelationshipStaging).filter(RelationshipStaging.case_id == case_id, RelationshipStaging.target_entity_id == cbi_short.id).update(
                {"target_entity_id": cbi_full.id}, synchronize_session=False
            )
            db.query(RelationshipStaging).filter(RelationshipStaging.case_id == case_id, RelationshipStaging.source_entity_id == cbi_full.id, RelationshipStaging.target_entity_id == cbi_full.id).delete(synchronize_session=False)
            db.query(EntityCaseLink).filter(EntityCaseLink.case_id == case_id, EntityCaseLink.entity_id == cbi_short.id).delete(synchronize_session=False)
            print("  CBI merged successfully.")

        db.commit()
        print("  Database changes committed.")

        # 4. Project clean graph to Neo4j
        try:
            from app.graph.driver import get_driver
            neo_driver = get_driver()
            with neo_driver.session() as s:
                # Remove all existing relationships for this case so updated endpoints don't violate relationship_id constraint
                s.run("MATCH ()-[r {case_id: $case_id}]->() DELETE r", case_id=str(case_id))
                # Remove orphaned nodes that might have been junk
                s.run("MATCH (n) WHERE NOT (n)--() AND NOT n:Case AND NOT n:Document DELETE n")
            res = project_case_graph(case_id, db, driver=neo_driver)
            print(f"  Neo4j graph projected successfully: {res}")
        except Exception as e:
            print(f"  Neo4j projection notice: {e}")

        print("=== CASE CLEANUP COMPLETE ===")


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "d548fa6c-9f01-4c1b-96a6-0d9c227d20fe"
    clean_case(cid)
