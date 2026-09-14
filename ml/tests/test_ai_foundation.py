"""Phase 1 AI / Multimodal Foundation Unit Tests.

Verifies:
1. Vendor-neutral provider abstraction
2. Multimodal input representation (TEXT, IMAGE, PDF, STRUCTURED)
3. Normalized model response boundary
4. Deterministic offline mock provider
5. Client boundary with bounded timeouts, retries, and input limits
6. Normalized AI error hierarchy
7. Secret masking and credential security
8. Regression compatibility with existing CrimeLens ML pipeline
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.ai import (
    AIAuthenticationError,
    AIClient,
    AIConfigurationError,
    AIError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
    AIUnsupportedInputError,
    InputType,
    MockReasoningProvider,
    ModelResponse,
    MultimodalInput,
    ReasoningModelProvider,
    create_ai_client,
)
from ml.ai.errors import redact_secrets
from ml.config import MLConfig, default_config
from ml.pipeline import process_document
from shared.schemas.models import ExtractionResult


class TestProviderAbstraction(unittest.TestCase):
    """Verifies that the provider abstraction is clean, vendor-neutral, and isolated."""

    def test_abstract_class_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            ReasoningModelProvider()  # type: ignore

    def test_mock_provider_conforms_to_abstraction(self):
        provider = MockReasoningProvider()
        self.assertIsInstance(provider, ReasoningModelProvider)
        self.assertEqual(provider.provider_name, "mock")
        self.assertTrue(provider.is_available)
        self.assertTrue(provider.health_check())

    def test_custom_provider_implementation(self):
        class DummyVendorProvider(ReasoningModelProvider):
            @property
            def provider_name(self) -> str:
                return "dummy-vendor"

            def analyze(self, input_data, *, context=None):
                return ModelResponse(
                    provider_name=self.provider_name,
                    model_name="dummy-v1",
                    structured_payload={"entities": []},
                )

        dummy = DummyVendorProvider()
        self.assertEqual(dummy.provider_name, "dummy-vendor")
        inp = MultimodalInput.from_text("Test probe")
        res = dummy.analyze(inp)
        self.assertEqual(res.provider_name, "dummy-vendor")


class TestMultimodalInputRepresentation(unittest.TestCase):
    """Verifies typed multimodal input representations across supported modalities."""

    def test_from_text(self):
        inp = MultimodalInput.from_text("First Information Report content", filename="fir.txt")
        self.assertEqual(inp.input_type, InputType.TEXT)
        self.assertEqual(inp.content, "First Information Report content")
        self.assertEqual(inp.mime_type, "text/plain")
        self.assertEqual(inp.filename, "fir.txt")
        self.assertEqual(inp.extracted_text, "First Information Report content")
        self.assertGreater(inp.byte_size, 0)

    def test_from_image(self):
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        inp = MultimodalInput.from_image(fake_png, mime_type="image/png", filename="evidence.png")
        self.assertEqual(inp.input_type, InputType.IMAGE)
        self.assertEqual(inp.content, fake_png)
        self.assertEqual(inp.mime_type, "image/png")
        self.assertEqual(inp.filename, "evidence.png")
        self.assertEqual(inp.byte_size, len(fake_png))

    def test_from_pdf(self):
        fake_pdf = b"%PDF-1.4\n%evidence"
        inp = MultimodalInput.from_pdf(
            fake_pdf,
            filename="case_file.pdf",
            extracted_text="Pre-extracted text from page 1",
            metadata={"pages": 1},
        )
        self.assertEqual(inp.input_type, InputType.PDF)
        self.assertEqual(inp.content, fake_pdf)
        self.assertEqual(inp.mime_type, "application/pdf")
        self.assertEqual(inp.extracted_text, "Pre-extracted text from page 1")
        self.assertEqual(inp.metadata.get("pages"), 1)

    def test_from_structured_records(self):
        records = [
            {"source": "ACC-101", "target": "ACC-202", "amount": 50000},
            {"source": "ACC-202", "target": "ACC-303", "amount": 50000},
        ]
        inp = MultimodalInput.from_structured(records, filename="txns.json")
        self.assertEqual(inp.input_type, InputType.STRUCTURED)
        self.assertEqual(inp.mime_type, "application/json")
        self.assertEqual(inp.metadata.get("record_count"), 2)
        self.assertIn("ACC-101", inp.content)

    def test_from_bytes_with_mime_inference(self):
        data = b"Hello world"
        inp = MultimodalInput.from_bytes(data, InputType.TEXT, filename="notes.txt")
        self.assertEqual(inp.mime_type, "text/plain")

    def test_invalid_empty_input_rejected(self):
        with self.assertRaises(AIUnsupportedInputError):
            MultimodalInput.from_text("")

        with self.assertRaises(AIUnsupportedInputError):
            MultimodalInput.from_text("   \n\t  ")

        with self.assertRaises(AIUnsupportedInputError):
            MultimodalInput.from_image(b"")

    def test_invalid_type_rejected(self):
        with self.assertRaises(AIUnsupportedInputError):
            MultimodalInput.from_text(12345)  # type: ignore

        with self.assertRaises(AIUnsupportedInputError):
            MultimodalInput.from_image("not bytes")  # type: ignore

        with self.assertRaises(AIUnsupportedInputError):
            MultimodalInput.from_structured("not a list or dict")  # type: ignore


class TestNormalizedModelResponse(unittest.TestCase):
    """Verifies provider-neutral response representation and isolation."""

    def test_response_getters(self):
        payload = {
            "entities": [
                {"id": "mention_mock_01", "type": "PERSON", "name": "Vikram", "confidence": 0.95}
            ],
            "relationships": [
                {
                    "id": "rel_mock_01",
                    "source_entity_id": "mention_mock_01",
                    "target_entity_id": "mention_mock_02",
                    "relationship": "CALLED",
                    "confidence": 0.9,
                }
            ],
            "patterns": [{"id": "pat_01", "type": "CIRCULAR_TRANSACTION", "severity": "HIGH"}],
            "leads": [{"id": "lead_01", "type": "FINANCIAL_NETWORK", "priority": "HIGH"}],
        }
        res = ModelResponse(
            provider_name="mock",
            model_name="mock-reasoner-v1",
            structured_payload=payload,
            latency_ms=12.5,
        )
        self.assertEqual(len(res.get_candidate_entities()), 1)
        self.assertEqual(res.get_candidate_entities()[0]["name"], "Vikram")
        self.assertEqual(len(res.get_candidate_relationships()), 1)
        self.assertEqual(len(res.get_candidate_patterns()), 1)
        self.assertEqual(len(res.get_candidate_leads()), 1)

    def test_response_with_empty_payload(self):
        res = ModelResponse(provider_name="mock", model_name="mock-reasoner-v1")
        self.assertEqual(res.get_candidate_entities(), [])
        self.assertEqual(res.get_candidate_relationships(), [])
        self.assertEqual(res.get_candidate_patterns(), [])
        self.assertEqual(res.get_candidate_leads(), [])


class TestDeterministicMockProvider(unittest.TestCase):
    """Verifies deterministic offline behavior and error simulation."""

    def test_deterministic_identical_output(self):
        provider = MockReasoningProvider()
        inp1 = MultimodalInput.from_text("Suspect Rajesh Sharma called Priya Patel on 9876543210.")
        inp2 = MultimodalInput.from_text("Suspect Rajesh Sharma called Priya Patel on 9876543210.")

        res1 = provider.analyze(inp1)
        res2 = provider.analyze(inp2)

        self.assertEqual(res1.structured_payload, res2.structured_payload)
        self.assertEqual(res1.raw_content, res2.raw_content)

    def test_custom_payload_injection(self):
        custom = {"entities": [{"id": "mention_test", "name": "Custom", "type": "PERSON"}]}
        provider = MockReasoningProvider(custom_payload=custom)
        inp = MultimodalInput.from_text("probe")
        res = provider.analyze(inp)
        self.assertEqual(res.structured_payload, custom)

    def test_controlled_error_simulations(self):
        # 1. Timeout
        with self.assertRaises(AITimeoutError):
            MockReasoningProvider(simulate_timeout=True).analyze(MultimodalInput.from_text("probe"))

        # 2. Rate Limit
        with self.assertRaises(AIRateLimitError):
            MockReasoningProvider(simulate_rate_limit=True).analyze(MultimodalInput.from_text("probe"))

        # 3. Auth Failure
        with self.assertRaises(AIAuthenticationError):
            MockReasoningProvider(simulate_auth_failure=True).analyze(MultimodalInput.from_text("probe"))

        # 4. Unavailable
        with self.assertRaises(AIProviderUnavailableError):
            MockReasoningProvider(simulate_unavailable=True).analyze(MultimodalInput.from_text("probe"))

        # 5. Malformed Response
        with self.assertRaises(AIMalformedResponseError):
            MockReasoningProvider(simulate_malformed=True).analyze(MultimodalInput.from_text("probe"))

        # 6. Execution Error
        with self.assertRaises(AIExecutionError):
            MockReasoningProvider(simulate_execution_error=True).analyze(MultimodalInput.from_text("probe"))


class TestAIClientBoundary(unittest.TestCase):
    """Verifies client boundary guarantees: bounded retries, timeouts, input limits."""

    def test_successful_client_call(self):
        provider = MockReasoningProvider()
        client = AIClient(provider, timeout_seconds=15.0, max_retries=1)
        inp = MultimodalInput.from_text("Evidence case statement")
        res = client.analyze(inp)
        self.assertIsInstance(res, ModelResponse)
        self.assertEqual(res.provider_name, "mock")

    def test_oversized_input_rejected_before_provider(self):
        provider = MockReasoningProvider()
        client = AIClient(provider, max_input_bytes=10)
        inp = MultimodalInput.from_text("This text exceeds ten bytes by far.")
        with self.assertRaises(AIUnsupportedInputError) as ctx:
            client.analyze(inp)
        self.assertIn("exceeds configured limit", str(ctx.exception))

    def test_transient_retry_success(self):
        """Provider fails transiently once then succeeds on attempt 2."""
        call_count = 0

        class TransientProvider(ReasoningModelProvider):
            @property
            def provider_name(self) -> str:
                return "transient"

            def analyze(self, input_data, *, context=None):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise AITimeoutError("Simulated first-attempt timeout")
                return ModelResponse(
                    provider_name=self.provider_name,
                    model_name="transient-v1",
                    structured_payload={"entities": []},
                )

        client = AIClient(TransientProvider(), max_retries=2)
        inp = MultimodalInput.from_text("probe")
        res = client.analyze(inp)
        self.assertEqual(call_count, 2)
        self.assertEqual(res.provider_name, "transient")

    def test_bounded_retry_exhaustion(self):
        """Repeated transient errors stop strictly at 1 + max_retries."""
        call_count = 0

        class AlwaysFailsTransientProvider(ReasoningModelProvider):
            @property
            def provider_name(self) -> str:
                return "always-fails"

            def analyze(self, input_data, *, context=None):
                nonlocal call_count
                call_count += 1
                raise AIRateLimitError("Simulated 429 quota exhausted")

        client = AIClient(AlwaysFailsTransientProvider(), max_retries=2)
        inp = MultimodalInput.from_text("probe")
        with self.assertRaises(AIRateLimitError):
            client.analyze(inp)
        self.assertEqual(call_count, 3)  # 1 initial + 2 retries

    def test_non_transient_auth_error_not_retried(self):
        """Authentication error fails immediately without wasteful retries."""
        call_count = 0

        class AuthFailProvider(ReasoningModelProvider):
            @property
            def provider_name(self) -> str:
                return "auth-fail"

            def analyze(self, input_data, *, context=None):
                nonlocal call_count
                call_count += 1
                raise AIAuthenticationError("Invalid API key")

        client = AIClient(AuthFailProvider(), max_retries=3)
        inp = MultimodalInput.from_text("probe")
        with self.assertRaises(AIAuthenticationError):
            client.analyze(inp)
        self.assertEqual(call_count, 1)  # No retry

    def test_context_sanitization_removes_sensitive_keys(self):
        captured_context = None

        class ContextCaptureProvider(ReasoningModelProvider):
            @property
            def provider_name(self) -> str:
                return "context-capture"

            def analyze(self, input_data, *, context=None):
                nonlocal captured_context
                captured_context = context
                return ModelResponse(provider_name="context-capture", model_name="v1")

        client = AIClient(ContextCaptureProvider())
        inp = MultimodalInput.from_text("probe")
        dirty_context = {
            "document_id": "doc_001",
            "api_key": "sk-1234567890abcdef1234567890",
            "password": "supersecretpassword",
            "db_session": "active_conn",
            "safe_hint": "phone_fraud",
        }
        client.analyze(inp, context=dirty_context)
        self.assertIsNotNone(captured_context)
        self.assertIn("document_id", captured_context)
        self.assertIn("safe_hint", captured_context)
        self.assertNotIn("api_key", captured_context)
        self.assertNotIn("password", captured_context)
        self.assertNotIn("db_session", captured_context)


class TestSecretSecurityAndRedaction(unittest.TestCase):
    """Verifies that secrets and API keys are strictly redacted in errors, logs, and configs."""

    def test_secret_redaction_in_exceptions(self):
        raw_err = "Failed calling provider with api_key: AIzaSyD9876543210abcdefghijklmnop123"
        err = AIError(raw_err)
        self.assertNotIn("AIzaSyD9876543210abcdefghijklmnop123", str(err))
        self.assertIn("***REDACTED***", str(err))
        self.assertNotIn("AIzaSyD9876543210abcdefghijklmnop123", repr(err))

    def test_openai_format_key_redaction(self):
        raw_msg = "Error connecting with sk-abcdef12345678901234567890"
        redacted = redact_secrets(raw_msg)
        self.assertNotIn("sk-abcdef12345678901234567890", redacted)
        self.assertIn("***REDACTED***", redacted)

    def test_config_repr_masks_api_key(self):
        config = MLConfig(ai_api_key="super_secret_ai_key_99999999")
        repr_str = repr(config)
        self.assertNotIn("super_secret_ai_key_99999999", repr_str)
        self.assertIn("***REDACTED***", repr_str)

    def test_config_safety_defaults(self):
        config = MLConfig()
        self.assertFalse(config.ai_enabled)
        self.assertEqual(config.ai_provider, "mock")
        self.assertIsNone(config.ai_api_key)
        self.assertGreater(config.ai_timeout_seconds, 0)
        self.assertGreaterEqual(config.ai_max_retries, 0)


class TestPipelineRegressionCompatibility(unittest.TestCase):
    """Verifies existing ML entry point process_document continues working without changes."""

    def test_process_document_text_regression(self):
        text = "Rajesh Sharma (+919876543210) met Priya Patel in Mumbai."
        result = process_document("doc_reg_001", text)
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_reg_001")
        self.assertGreaterEqual(len(result.entities), 1)

    def test_process_document_bytes_backend_convention(self):
        data = b"Amit Kumar transferred funds to Suresh Raina."
        result = process_document(data, "statement.txt", "doc_reg_002")
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_reg_002")

    def test_factory_helper_create_ai_client(self):
        client = create_ai_client()
        self.assertIsInstance(client, AIClient)
        self.assertIsInstance(client.provider, MockReasoningProvider)


if __name__ == "__main__":
    unittest.main()
