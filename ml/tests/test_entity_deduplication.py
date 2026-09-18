"""Unit tests for entity deduplication, alias resolution, and false-merge prevention."""

from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ml.resolution.resolver import (
    extract_alias_names,
    normalize_org,
    normalize_person_name,
    is_name_fuzzy_match,
    compare_mentions,
)
from shared.schemas.enums import EntityType, ResolutionSignal
from shared.schemas.models import EntityMention
from app.services.processing import are_entities_equivalent


class TestEntityDeduplication(unittest.TestCase):
    def test_alias_extraction(self):
        """Test extraction of alias components from names."""
        parts1 = extract_alias_names("Sanju @ Sanjib Sahu")
        self.assertEqual(parts1, ["Sanju", "Sanjib Sahu"])

        parts2 = extract_alias_names("Punjilal Meher alias Punji")
        self.assertEqual(parts2, ["Punjilal Meher", "Punji"])

        parts3 = extract_alias_names("Sanjib Sahu a.k.a. Sanju")
        self.assertEqual(parts3, ["Sanjib Sahu", "Sanju"])

        parts4 = extract_alias_names("Punjilal Meher")
        self.assertEqual(parts4, ["Punjilal Meher"])

    def test_title_stripping(self):
        """Test that titles and honorifics are normalized."""
        self.assertEqual(normalize_person_name("Dr. Punjilal Meher"), "punjilal meher")
        self.assertEqual(normalize_person_name("Prof. Punjilal Meher"), "punjilal meher")
        self.assertEqual(normalize_person_name("Shri Punjilal Meher"), "punjilal meher")
        self.assertEqual(normalize_person_name("Inspector S.K. Sahu"), "s.k. sahu")

    def test_org_ps_normalization(self):
        """Test that PS is standardized to Police Station."""
        self.assertEqual(normalize_org("Patnagarh PS"), "patnagarh police station")
        self.assertEqual(normalize_org("Patnagarh P.S."), "patnagarh police station")
        self.assertEqual(normalize_org("Patnagarh Police Station"), "patnagarh police station")

    def test_exact_name_same_person(self):
        """Exact same name across documents must match."""
        is_match, name = are_entities_equivalent(
            EntityType.PERSON, "Punjilal Meher",
            EntityType.PERSON, "Punjilal Meher",
        )
        self.assertTrue(is_match)
        self.assertEqual(name, "Punjilal Meher")

    def test_title_variation_equivalence(self):
        """Dr. Punjilal Meher and Punjilal Meher must match."""
        is_match, name = are_entities_equivalent(
            EntityType.PERSON, "Dr. Punjilal Meher",
            EntityType.PERSON, "Punjilal Meher",
        )
        self.assertTrue(is_match)
        self.assertEqual(name, "Punjilal Meher")

    def test_alias_equivalence(self):
        """Sanju @ Sanjib Sahu and Sanjib Sahu must match."""
        is_match, name = are_entities_equivalent(
            EntityType.PERSON, "Sanju @ Sanjib Sahu",
            EntityType.PERSON, "Sanjib Sahu",
        )
        self.assertTrue(is_match)

    def test_single_name_to_unique_full_name(self):
        """Punjilal must match Punjilal Meher when only one Punjilal exists in case."""
        is_match, name = are_entities_equivalent(
            EntityType.PERSON, "Punjilal",
            EntityType.PERSON, "Punjilal Meher",
            existing_case_persons=["Punjilal Meher", "Soumya Sekhar Sahu", "Sanjib Sahu"],
        )
        self.assertTrue(is_match)
        self.assertEqual(name, "Punjilal Meher")

    def test_ambiguous_single_name_does_not_merge(self):
        """Punjilal must NOT merge if two people have first name Punjilal."""
        is_match, _ = are_entities_equivalent(
            EntityType.PERSON, "Punjilal",
            EntityType.PERSON, "Punjilal Meher",
            existing_case_persons=["Punjilal Meher", "Punjilal Sahu"],
        )
        self.assertFalse(is_match)

    def test_different_first_names_never_merge(self):
        """Soumya Sekhar Sahu and Sanjib Sahu have the same surname but different first names. NEVER MERGE!"""
        is_match, _ = are_entities_equivalent(
            EntityType.PERSON, "Soumya Sekhar Sahu",
            EntityType.PERSON, "Sanjib Sahu",
        )
        self.assertFalse(is_match)

        # Also check resolver.compare_mentions directly
        mA = EntityMention(id="m1", type=EntityType.PERSON, name="Soumya Sekhar Sahu", confidence=0.9)
        mB = EntityMention(id="m2", type=EntityType.PERSON, name="Sanjib Sahu", confidence=0.9)
        res = compare_mentions(mA, mB)
        self.assertIsNone(res)

    def test_org_abbreviation_equivalence(self):
        """Patnagarh PS and Patnagarh Police Station must match."""
        is_match, name = are_entities_equivalent(
            EntityType.ORGANIZATION, "Patnagarh PS",
            EntityType.ORGANIZATION, "Patnagarh Police Station",
        )
        self.assertTrue(is_match)

    def test_type_safety_no_merge(self):
        """Different entity types must never match."""
        is_match, _ = are_entities_equivalent(
            EntityType.PERSON, "Patnagarh",
            EntityType.LOCATION, "Patnagarh",
        )
        self.assertFalse(is_match)


if __name__ == "__main__":
    unittest.main()
