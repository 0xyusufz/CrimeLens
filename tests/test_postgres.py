"""PostgreSQL connectivity and users/cases/case_members smoke tests.

Uses the CrimeLens Docker database (host port from .env, expected 5433).
Does not print credentials. Cleans up test rows.
"""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal, engine
from app.models import (
    Case,
    CaseMember,
    CaseStatus,
    Document,
    Entity,
    EntityCaseLink,
    EntityMention,
    EntityType,
    RecordType,
    RelationshipStaging,
    RelationshipStatus,
    RelationshipType,
    StructuredRecord,
    User,
    UserRole,
)


class PostgresFoundationTests(unittest.TestCase):
    def test_select_1(self):
        with engine.connect() as conn:
            value = conn.execute(text("SELECT 1")).scalar()
        self.assertEqual(value, 1)

    def test_core_tables_exist(self):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertTrue(
            {
                "users",
                "cases",
                "case_members",
                "documents",
                "structured_records",
                "entities",
                "entity_mentions",
                "entity_case_links",
                "relationships_staging",
                "audit_logs",
                "evidence_blocks",
            }.issubset(tables)
        )

    def test_insert_read_delete(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        user = User(
            name="Connectivity Tester",
            email=f"pg-test-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        case = None
        member = None
        try:
            session.add(user)
            session.flush()

            case = Case(
                case_number=f"TEST-{suffix}",
                title="Connectivity test case",
                description="Temporary row; deleted by test.",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add(case)
            session.flush()

            member = CaseMember(
                case_id=case.id,
                user_id=user.id,
                assigned_role="INVESTIGATOR",
            )
            session.add(member)
            session.flush()

            loaded_user = session.get(User, user.id)
            loaded_case = session.get(Case, case.id)
            loaded_member = session.get(CaseMember, member.id)
            self.assertIsNotNone(loaded_user)
            self.assertEqual(loaded_user.email, user.email)
            self.assertIsNotNone(loaded_case)
            self.assertEqual(loaded_case.created_by, user.id)
            self.assertIsNotNone(loaded_member)

            session.delete(member)
            session.delete(case)
            session.delete(user)
            session.commit()

            self.assertIsNone(session.get(User, user.id))
            self.assertIsNone(session.get(Case, case.id))
            self.assertIsNone(session.get(CaseMember, member.id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_documents_and_structured_records_insert_read_delete(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        user = User(
            name="Document Tester",
            email=f"doc-test-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        try:
            session.add(user)
            session.flush()

            case = Case(
                case_number=f"DOC-{suffix}",
                title="Document layer test case",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add(case)
            session.flush()

            document = Document(
                case_id=case.id,
                filename="cdr_and_txn.csv",
                sha256_hash="0" * 64,
                uploaded_by=user.id,
            )
            session.add(document)
            session.flush()

            cdr = StructuredRecord(
                case_id=case.id,
                document_id=document.id,
                record_type=RecordType.CDR,
                raw_json={
                    "caller": "9876543210",
                    "receiver": "9123456789",
                    "duration": 120,
                    "location": "Bhubaneswar",
                },
            )
            txn = StructuredRecord(
                case_id=case.id,
                document_id=document.id,
                record_type=RecordType.TRANSACTION,
                raw_json={
                    "sender_account": "ACC001",
                    "receiver_account": "ACC002",
                    "amount": 45000,
                    "location": "Bhubaneswar",
                },
            )
            session.add_all([cdr, txn])
            session.flush()

            loaded_doc = session.get(Document, document.id)
            loaded_cdr = session.get(StructuredRecord, cdr.id)
            loaded_txn = session.get(StructuredRecord, txn.id)
            self.assertIsNotNone(loaded_doc)
            self.assertEqual(loaded_doc.case_id, case.id)
            self.assertEqual(loaded_doc.uploaded_by, user.id)
            self.assertEqual(loaded_cdr.record_type, RecordType.CDR)
            self.assertEqual(loaded_cdr.raw_json["caller"], "9876543210")
            self.assertEqual(loaded_txn.record_type, RecordType.TRANSACTION)
            self.assertEqual(loaded_txn.raw_json["amount"], 45000)

            session.delete(txn)
            session.delete(cdr)
            session.delete(document)
            session.delete(case)
            session.delete(user)
            session.commit()

            self.assertIsNone(session.get(Document, document.id))
            self.assertIsNone(session.get(StructuredRecord, cdr.id))
            self.assertIsNone(session.get(StructuredRecord, txn.id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_entities_mentions_and_case_links(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        user = User(
            name="Entity Tester",
            email=f"ent-test-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        try:
            session.add(user)
            session.flush()

            case_a = Case(
                case_number=f"ENT-A-{suffix}",
                title="Entity layer case A",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            case_b = Case(
                case_number=f"ENT-B-{suffix}",
                title="Entity layer case B",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add_all([case_a, case_b])
            session.flush()

            document = Document(
                case_id=case_a.id,
                filename="fir_001.txt",
                sha256_hash="1" * 64,
                uploaded_by=user.id,
            )
            session.add(document)
            session.flush()

            person = Entity(type=EntityType.PERSON, canonical_name="Rahul Sharma")
            phone = Entity(type=EntityType.PHONE, canonical_name="9876543210")
            session.add_all([person, phone])
            session.flush()
            self.assertIsInstance(person.id, uuid.UUID)
            self.assertNotEqual(str(person.id), "mention_001")

            linked_mention = EntityMention(
                document_id=document.id,
                entity_id=person.id,
                mention_id="mention_001",
                entity_type=EntityType.PERSON,
                name="Rahul Sharma",
                confidence=0.96,
                evidence_snippet="Rahul Sharma called Amit Kumar.",
            )
            unresolved_mention = EntityMention(
                document_id=document.id,
                entity_id=None,
                mention_id="mention_002",
                entity_type=EntityType.PERSON,
                name="Amit Kumar",
                confidence=0.94,
                evidence_snippet=None,
            )
            phone_mention = EntityMention(
                document_id=document.id,
                entity_id=phone.id,
                mention_id="mention_003",
                entity_type=EntityType.PHONE,
                name="9876543210",
                confidence=0.99,
            )
            session.add_all([linked_mention, unresolved_mention, phone_mention])
            session.flush()

            loaded_linked = session.get(EntityMention, linked_mention.id)
            loaded_unresolved = session.get(EntityMention, unresolved_mention.id)
            self.assertEqual(loaded_linked.entity_id, person.id)
            self.assertEqual(loaded_linked.mention_id, "mention_001")
            self.assertIsNone(loaded_unresolved.entity_id)

            link_a = EntityCaseLink(entity_id=person.id, case_id=case_a.id)
            link_b = EntityCaseLink(entity_id=person.id, case_id=case_b.id)
            session.add_all([link_a, link_b])
            session.flush()
            links = (
                session.query(EntityCaseLink)
                .filter(EntityCaseLink.entity_id == person.id)
                .all()
            )
            self.assertEqual({link.case_id for link in links}, {case_a.id, case_b.id})

            with self.assertRaises(IntegrityError):
                with session.begin_nested():
                    session.add(EntityCaseLink(entity_id=person.id, case_id=case_a.id))
                    session.flush()

            session.delete(unresolved_mention)
            session.delete(phone_mention)
            session.delete(linked_mention)
            session.delete(link_a)
            session.delete(link_b)
            session.delete(person)
            session.delete(phone)
            session.delete(document)
            session.delete(case_a)
            session.delete(case_b)
            session.delete(user)
            session.commit()

            self.assertIsNone(session.get(Entity, person.id))
            self.assertIsNone(session.get(EntityMention, linked_mention.id))
            self.assertIsNone(session.get(EntityCaseLink, link_a.id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_relationships_staging(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        extracted_at = datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc)
        user = User(
            name="Rel Tester",
            email=f"rel-test-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        try:
            session.add(user)
            session.flush()

            case = Case(
                case_number=f"REL-{suffix}",
                title="Relationship staging test",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add(case)
            session.flush()

            document = Document(
                case_id=case.id,
                filename="fir_rel.txt",
                sha256_hash="2" * 64,
                uploaded_by=user.id,
            )
            session.add(document)
            session.flush()

            cdr = StructuredRecord(
                case_id=case.id,
                document_id=document.id,
                record_type=RecordType.CDR,
                raw_json={"caller": "9876543210", "receiver": "9123456789", "duration": 120},
            )
            txn = StructuredRecord(
                case_id=case.id,
                document_id=document.id,
                record_type=RecordType.TRANSACTION,
                raw_json={"sender_account": "ACC001", "receiver_account": "ACC002", "amount": 45000},
            )
            session.add_all([cdr, txn])
            session.flush()

            source = Entity(type=EntityType.PERSON, canonical_name="Rahul Sharma")
            target = Entity(type=EntityType.PERSON, canonical_name="Amit Kumar")
            session.add_all([source, target])
            session.flush()

            called = RelationshipStaging(
                source_occurrence_id="rel_001",
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=RelationshipType.CALLED,
                confidence=0.98,
                status=RelationshipStatus.CONFIRMED,
                source_document_id=document.id,
                source_record_id=None,
                evidence_snippet="Rahul called Amit Kumar.",
                extracted_at=extracted_at,
                case_id=case.id,
            )
            sent = RelationshipStaging(
                source_occurrence_id="rel_txn_001",
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=RelationshipType.SENT_MONEY_TO,
                confidence=1.0,
                status=RelationshipStatus.INFERRED,
                source_document_id=None,
                source_record_id=txn.id,
                evidence_snippet=None,
                extracted_at=extracted_at,
                case_id=case.id,
            )
            predicted = RelationshipStaging(
                source_occurrence_id="rel_002",
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=RelationshipType.CALLED,
                confidence=0.82,
                status=RelationshipStatus.PREDICTED,
                source_document_id=document.id,
                evidence_snippet="Possible additional call.",
                extracted_at=extracted_at,
                case_id=case.id,
            )
            session.add_all([called, sent, predicted])
            session.flush()

            loaded_called = session.get(RelationshipStaging, called.id)
            loaded_sent = session.get(RelationshipStaging, sent.id)
            self.assertEqual(loaded_called.status, RelationshipStatus.CONFIRMED)
            self.assertEqual(loaded_called.source_document_id, document.id)
            self.assertIsNone(loaded_called.source_record_id)
            self.assertEqual(loaded_sent.status, RelationshipStatus.INFERRED)
            self.assertEqual(loaded_sent.source_record_id, txn.id)
            self.assertEqual(predicted.status, RelationshipStatus.PREDICTED)
            self.assertNotEqual(loaded_called.status, RelationshipStatus.INFERRED)

            same_entities = (
                session.query(RelationshipStaging)
                .filter(
                    RelationshipStaging.source_entity_id == source.id,
                    RelationshipStaging.target_entity_id == target.id,
                    RelationshipStaging.relationship_type == RelationshipType.CALLED,
                )
                .all()
            )
            self.assertEqual(len(same_entities), 2)

            with self.assertRaises(IntegrityError):
                with session.begin_nested():
                    session.add(
                        RelationshipStaging(
                            source_occurrence_id="rel_001",
                            source_entity_id=source.id,
                            target_entity_id=target.id,
                            relationship_type=RelationshipType.CALLED,
                            confidence=0.5,
                            status=RelationshipStatus.CONFIRMED,
                            source_document_id=document.id,
                            extracted_at=extracted_at,
                            case_id=case.id,
                        )
                    )
                    session.flush()

            with self.assertRaises(IntegrityError):
                with session.begin_nested():
                    session.add(
                        RelationshipStaging(
                            source_occurrence_id="rel_bad_conf",
                            source_entity_id=source.id,
                            target_entity_id=target.id,
                            relationship_type=RelationshipType.CALLED,
                            confidence=95,
                            status=RelationshipStatus.CONFIRMED,
                            source_document_id=document.id,
                            extracted_at=extracted_at,
                            case_id=case.id,
                        )
                    )
                    session.flush()

            with self.assertRaises(IntegrityError):
                with session.begin_nested():
                    session.add(
                        RelationshipStaging(
                            source_occurrence_id="rel_no_prov",
                            source_entity_id=source.id,
                            target_entity_id=target.id,
                            relationship_type=RelationshipType.CALLED,
                            confidence=0.5,
                            status=RelationshipStatus.CONFIRMED,
                            source_document_id=None,
                            source_record_id=None,
                            extracted_at=extracted_at,
                            case_id=case.id,
                        )
                    )
                    session.flush()

            unresolved_source = RelationshipStaging(
                source_occurrence_id="rel_unresolved_source",
                source_entity_id=None,
                target_entity_id=target.id,
                relationship_type=RelationshipType.CALLED,
                confidence=0.70,
                status=RelationshipStatus.INFERRED,
                source_document_id=document.id,
                extracted_at=extracted_at,
                case_id=case.id,
            )
            unresolved_target = RelationshipStaging(
                source_occurrence_id="rel_unresolved_target",
                source_entity_id=source.id,
                target_entity_id=None,
                relationship_type=RelationshipType.CALLED,
                confidence=0.71,
                status=RelationshipStatus.INFERRED,
                source_document_id=document.id,
                extracted_at=extracted_at,
                case_id=case.id,
            )
            session.add_all([unresolved_source, unresolved_target])
            session.flush()
            self.assertIsNone(session.get(RelationshipStaging, unresolved_source.id).source_entity_id)
            self.assertIsNone(session.get(RelationshipStaging, unresolved_target.id).target_entity_id)

            session.delete(unresolved_source)
            session.delete(unresolved_target)
            session.delete(called)
            session.delete(sent)
            session.delete(predicted)
            session.delete(source)
            session.delete(target)
            session.delete(txn)
            session.delete(cdr)
            session.delete(document)
            session.delete(case)
            session.delete(user)
            session.commit()

            self.assertIsNone(session.get(RelationshipStaging, called.id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
