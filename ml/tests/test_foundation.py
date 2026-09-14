"""Phase 1 ML Foundation unit tests.

Verifies:
- Clean package and subpackage imports
- No circular dependencies
- Configuration initialization without database settings
- Pipeline entry interface process_document
- Schema compliance with frozen shared models
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MLFoundationTests(unittest.TestCase):
    def test_ml_package_import(self):
        import ml
        from ml import MLConfig, default_config, process_document

        self.assertIsNotNone(ml)
        self.assertIsNotNone(MLConfig)
        self.assertIsNotNone(default_config)
        self.assertTrue(callable(process_document))

    def test_subpackages_import(self):
        import ml.extraction
        import ml.ocr
        import ml.patterns
        import ml.preprocessing
        import ml.relationships
        import ml.resolution
        import ml.validation

        self.assertIsNotNone(ml.preprocessing)
        self.assertIsNotNone(ml.ocr)
        self.assertIsNotNone(ml.extraction)
        self.assertIsNotNone(ml.relationships)
        self.assertIsNotNone(ml.resolution)
        self.assertIsNotNone(ml.patterns)
        self.assertIsNotNone(ml.validation)

    def test_config_safety(self):
        from ml.config import MLConfig, default_config

        config = MLConfig()
        self.assertGreaterEqual(config.min_entity_confidence, 0.0)
        self.assertLessEqual(config.min_entity_confidence, 1.0)
        # Ensure no database/server settings exist in ML config
        self.assertFalse(hasattr(config, "database_url"))
        self.assertFalse(hasattr(config, "postgres_url"))
        self.assertFalse(hasattr(config, "neo4j_uri"))
        self.assertFalse(hasattr(config, "neo4j_password"))

    def test_process_document_interface(self):
        from ml.pipeline import process_document
        from shared.schemas.models import ExtractionResult

        # Valid call returns valid ExtractionResult envelope
        result = process_document("doc_001", "Sample document text.")
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_001")
        self.assertEqual(result.entities, [])
        self.assertEqual(result.relationships, [])

        # Empty document_id raises ValueError
        with self.assertRaises(ValueError):
            process_document("", "Sample document text.")

    def test_output_validator(self):
        from ml.validation import validate_extraction_result
        from shared.schemas.models import ExtractionResult

        valid_payload = {
            "document_id": "doc_test_100",
            "entities": [],
            "relationships": [],
        }
        validated = validate_extraction_result(valid_payload)
        self.assertIsInstance(validated, ExtractionResult)
        self.assertEqual(validated.document_id, "doc_test_100")


if __name__ == "__main__":
    unittest.main()
