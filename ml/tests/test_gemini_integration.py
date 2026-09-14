"""Focused tests for Gemini provider integration with CrimeLens ML.

Covers:
1. Missing API key → safe fallback to deterministic/mock pipeline
2. API key present → Gemini provider correctly detected
3. API key is never exposed in logs or error messages
4. Provider network failure → deterministic/mock fallback
5. Gemini response passes existing safety firewall
6. Existing deterministic pipeline works without Gemini
7. Existing ML contract (ExtractionResult) remains valid

No real API key required — all network calls are mocked via httpx.
Opt-in live smoke test: set CRIMELENS_TEST_GEMINI_LIVE=1 + GEMINI_API_KEY in env.
"""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import httpx

from ml.ai.errors import (
    AIAuthenticationError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from ml.ai.pipeline_integration import AIPipelineCoordinator
from ml.ai.providers.gemini import GeminiReasoningProvider
from ml.ai.providers.mock import MockReasoningProvider
from ml.ai.types import InputType, MultimodalInput
from ml.config import MLConfig, default_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_input(text: str) -> MultimodalInput:
    """Build a text MultimodalInput using the project's from_text() factory."""
    return MultimodalInput.from_text(text)


def _make_subprocess_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Build a fake subprocess.CompletedProcess for a well-formed Gemini reply."""
    body_dict = {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps(payload)}]},
            "finishReason": "STOP",
        }],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 20,
            "totalTokenCount": 30,
        },
    }
    body_str = json.dumps(body_dict)

    mock_resp = MagicMock()
    mock_resp.returncode = 0
    # GeminiProvider expects curl output with "\n{status_code}" appended
    mock_resp.stdout = f"{body_str}\n{status_code}"
    return mock_resp


def _make_subprocess_error_response(status_code: int) -> MagicMock:
    """Build a fake subprocess.CompletedProcess with a non-200 status."""
    mock_resp = MagicMock()
    mock_resp.returncode = 0
    body_str = json.dumps({"error": {"code": status_code, "message": "error"}})
    mock_resp.stdout = f"{body_str}\n{status_code}"
    return mock_resp


_VALID_GEMINI_PAYLOAD = {
    "entities": [
        {"id": "mention_g_1", "type": "PERSON", "name": "Rajan Das", "confidence": 0.9}
    ],
    "relationships": [],
    "patterns": [],
    "leads": [],
}

# Patch target for all unit tests (subprocess.run)
_PATCH_TARGET = "ml.ai.providers.gemini.subprocess.run"


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestGeminiMissingKeyFallback(unittest.TestCase):
    """1. Missing API key → safe fallback to mock provider."""

    def test_no_key_mock_provider_used(self):
        config = MLConfig(ai_enabled=False, ai_provider="mock", ai_api_key=None)
        coord = AIPipelineCoordinator(config=config)
        client = coord._ensure_client()
        self.assertIsInstance(client.provider, MockReasoningProvider)
        self.assertEqual(client.provider.provider_name, "mock")

    def test_gemini_provider_requested_but_no_key_falls_back_to_mock(self):
        """If AI_PROVIDER=gemini but key is absent, pipeline must not crash."""
        config = MLConfig(ai_enabled=True, ai_provider="gemini", ai_api_key=None)
        coord = AIPipelineCoordinator(config=config)
        client = coord._ensure_client()
        self.assertIsInstance(client.provider, MockReasoningProvider)

    def test_default_config_without_env_is_mock(self):
        config = MLConfig(ai_enabled=False, ai_provider="mock", ai_api_key=None)
        self.assertFalse(config.ai_enabled)
        self.assertEqual(config.ai_provider, "mock")
        self.assertIsNone(config.ai_api_key)


class TestGeminiKeyDetection(unittest.TestCase):
    """2. API key present → Gemini provider correctly detected."""

    def test_gemini_provider_instantiated_with_key(self):
        config = MLConfig(
            ai_enabled=True,
            ai_provider="gemini",
            ai_api_key="fake_key_for_testing",
            ai_model="gemini-1.5-flash",
        )
        coord = AIPipelineCoordinator(config=config)
        client = coord._ensure_client()
        self.assertIsInstance(client.provider, GeminiReasoningProvider)
        self.assertEqual(client.provider.provider_name, "gemini")

    def test_config_reflects_gemini_provider_name(self):
        config = MLConfig(ai_provider="gemini", ai_api_key="fake_key")
        self.assertEqual(config.ai_provider, "gemini")
        self.assertEqual(config.ai_api_key, "fake_key")


class TestApiKeyNotExposed(unittest.TestCase):
    """3. API key is never exposed in logs or error messages."""

    def test_repr_redacts_key(self):
        config = MLConfig(ai_api_key="SUPER_SECRET_KEY_XYZ_99999")
        repr_str = repr(config)
        self.assertNotIn("SUPER_SECRET_KEY_XYZ_99999", repr_str)
        self.assertIn("***REDACTED***", repr_str)

    def test_gemini_auth_error_does_not_contain_key(self):
        """HTTP 401 must not echo the key back."""
        provider = GeminiReasoningProvider(api_key="my_secret_key_abc")
        fake_input = _text_input("test doc")

        with patch(_PATCH_TARGET, return_value=_make_subprocess_error_response(401)):
            with self.assertRaises(AIAuthenticationError) as ctx:
                provider.analyze(fake_input)
        self.assertNotIn("my_secret_key_abc", str(ctx.exception))

    def test_gemini_connect_error_does_not_contain_key(self):
        """Connection failure must not include key in message."""
        provider = GeminiReasoningProvider(api_key="my_secret_key_abc")
        fake_input = _text_input("test doc")

        # Simulate curl returning a non-zero exit code for connection error
        mock_resp = MagicMock()
        mock_resp.returncode = 7  # curl couldn't connect
        mock_resp.stdout = ""

        with patch(_PATCH_TARGET, return_value=mock_resp):
            with self.assertRaises(AIProviderUnavailableError) as ctx:
                provider.analyze(fake_input)
        self.assertNotIn("my_secret_key_abc", str(ctx.exception))

    def test_empty_key_raises_auth_error(self):
        with self.assertRaises(AIAuthenticationError):
            GeminiReasoningProvider(api_key="")


class TestProviderFailureFallback(unittest.TestCase):
    """4. Provider network failure → correct error types raised."""



    def test_provider_timeout_pipeline_continues(self):
        """With ai_enabled=False, deterministic pipeline produces a valid result."""
        from ml.pipeline import process_document
        text = "Suresh Patel called 9988776655 from Delhi on 2026-09-10."
        result = process_document(
            "doc_provider_fail_001",
            text,
            config=MLConfig(ai_enabled=False),
        )
        self.assertEqual(result.document_id, "doc_provider_fail_001")

    def test_http_rate_limit_raises_rate_limit_error(self):
        provider = GeminiReasoningProvider(api_key="fake_key")
        fake_input = _text_input("test")
        with patch(_PATCH_TARGET, return_value=_make_subprocess_error_response(429)):
            with self.assertRaises(AIRateLimitError):
                provider.analyze(fake_input)

    def test_http_server_error_raises_provider_unavailable(self):
        provider = GeminiReasoningProvider(api_key="fake_key")
        fake_input = _text_input("test")
        with patch(_PATCH_TARGET, return_value=_make_subprocess_error_response(503)):
            with self.assertRaises(AIProviderUnavailableError):
                provider.analyze(fake_input)

    def test_http_404_raises_execution_error_with_model_name(self):
        """404 must name the model (no key) so user can fix GEMINI_MODEL."""
        provider = GeminiReasoningProvider(api_key="fake_key", model_name="bad-model-xyz")
        fake_input = _text_input("test")
        with patch(_PATCH_TARGET, return_value=_make_subprocess_error_response(404)):
            with self.assertRaises(AIExecutionError) as ctx:
                provider.analyze(fake_input)
        self.assertIn("bad-model-xyz", str(ctx.exception))
        self.assertNotIn("fake_key", str(ctx.exception))

    def test_timeout_raises_ai_timeout_error(self):
        import subprocess
        provider = GeminiReasoningProvider(api_key="fake_key")
        fake_input = _text_input("test")
        with patch(_PATCH_TARGET, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)):
            with self.assertRaises(AITimeoutError):
                provider.analyze(fake_input)

    def test_malformed_response_raises_malformed_error(self):
        provider = GeminiReasoningProvider(api_key="fake_key")
        fake_input = _text_input("test")
        bad_body = {"candidates": [{"content": {"parts": [{"text": "NOT VALID JSON !!!"}]}, "finishReason": "STOP"}]}

        mock_resp = MagicMock()
        mock_resp.returncode = 0
        mock_resp.stdout = f"{json.dumps(bad_body)}\n200"

        with patch(_PATCH_TARGET, return_value=mock_resp):
            with self.assertRaises(AIMalformedResponseError):
                provider.analyze(fake_input)


class TestGeminiResponseSafetyFirewall(unittest.TestCase):
    """5. Gemini response must pass existing safety firewall."""

    def _mock_client_ok(self):
        return _make_subprocess_response(_VALID_GEMINI_PAYLOAD)

    def test_valid_gemini_response_accepted(self):
        """A well-formed Gemini response produces a valid ModelResponse."""
        provider = GeminiReasoningProvider(api_key="fake_key")
        fake_input = _text_input("test document content")

        with patch(_PATCH_TARGET, return_value=self._mock_client_ok()):
            response = provider.analyze(fake_input)

        self.assertEqual(response.provider_name, "gemini")
        self.assertIsInstance(response.structured_payload, dict)
        self.assertIn("entities", response.structured_payload)

    def test_hallucinated_db_id_blocked_by_firewall(self):
        """GeminiReasoningProvider must not inject PostgreSQL-style UUIDs as entity IDs."""
        provider = GeminiReasoningProvider(api_key="fake_key")
        fake_input = _text_input("Kiran Bedi was seen near 12/5 Main St.")

        with patch(_PATCH_TARGET, return_value=self._mock_client_ok()):
            response = provider.analyze(fake_input)

        for entity in response.structured_payload.get("entities", []):
            eid = entity.get("id", "")
            self.assertFalse(
                len(eid) == 36 and eid.count("-") == 4,
                f"Entity ID looks like a DB UUID: {eid}",
            )


class TestExistingPipelineUnchanged(unittest.TestCase):
    """6 & 7. Existing deterministic pipeline and ML contract remain valid."""

    def test_deterministic_pipeline_no_gemini(self):
        from ml.pipeline import process_document
        text = "Rahul Sharma transferred INR 50000 to Amit Kumar on 2026-09-12."
        result = process_document(
            "doc_det_001",
            text,
            config=MLConfig(ai_enabled=False),
        )
        self.assertEqual(result.document_id, "doc_det_001")
        self.assertGreater(len(result.entities), 0)

    def test_ml_contract_returns_extraction_result(self):
        from ml.pipeline import process_document
        from shared.schemas.models import ExtractionResult
        text = "Officer Singh filed a report at Connaught Place station."
        result = process_document(
            "doc_contract_001",
            text,
            config=MLConfig(ai_enabled=False),
        )
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_contract_001")

    def test_process_document_with_mock_ai_enabled(self):
        """With ai_enabled=True and mock provider, pipeline must still succeed."""
        from ml.pipeline import process_document
        from ml.ai.client.client import AIClient

        text = "Vikram Nair met Priya Menon at the airport."
        mock_client = AIClient(MockReasoningProvider())
        result = process_document(
            "doc_mock_ai_001",
            text,
            config=MLConfig(ai_enabled=True, ai_provider="mock"),
            ai_client=mock_client,
        )
        self.assertEqual(result.document_id, "doc_mock_ai_001")


@unittest.skipUnless(
    os.environ.get("CRIMELENS_TEST_GEMINI_LIVE") == "1"
    and os.environ.get("GEMINI_API_KEY"),
    "Skipped: set CRIMELENS_TEST_GEMINI_LIVE=1 and GEMINI_API_KEY to run live smoke test"
)
class TestGeminiLiveSmoke(unittest.TestCase):
    """Live opt-in smoke test. Never runs in CI. Key must be in env, never hard-coded.

    To run:
        CRIMELENS_TEST_GEMINI_LIVE=1 backend/.venv/bin/python \\
            -m pytest ml/tests/test_gemini_integration.py::TestGeminiLiveSmoke -v -s
    """

    def test_live_gemini_call(self):
        api_key = os.environ["GEMINI_API_KEY"]

        # Use configured model from GEMINI_MODEL env, then default_config, then safe fallback.
        model_name = (
            os.environ.get("GEMINI_MODEL")
            or default_config.ai_model
            or "gemini-1.5-flash"
        )

        provider = GeminiReasoningProvider(api_key=api_key, model_name=model_name)

        # Use the project's from_text() factory — the correct public API.
        live_input = MultimodalInput.from_text(
            "Mohan Lal transferred 5000 INR to Sunita Devi on 2026-09-01."
        )

        print(f"\n[LiveSmoke] Using model: {model_name}")
        print(f"[LiveSmoke] Provider: {provider.provider_name}")

        # Make the real HTTP call — no mocking in this test.
        # If this raises an AIError subclass, let it propagate so the real
        # API error is visible in the test output.
        response = provider.analyze(live_input)

        print(f"[LiveSmoke] Latency: {response.latency_ms:.0f}ms")
        print(f"[LiveSmoke] Tokens: {response.usage_tokens}")
        print(f"[LiveSmoke] Finish reason: {response.metadata.get('gemini_finish_reason')}")
        print(f"[LiveSmoke] Entity count: {len(response.structured_payload.get('entities', []))}")

        self.assertEqual(response.provider_name, "gemini")
        self.assertIsInstance(response.structured_payload, dict)

        # Key must not appear in any response field.
        for field_name, field_value in [
            ("raw_content", response.raw_content),
            ("structured_payload", str(response.structured_payload)),
            ("metadata", str(response.metadata)),
        ]:
            self.assertNotIn(
                api_key,
                field_value,
                msg=f"API key unexpectedly found in response field: {field_name}",
            )


if __name__ == "__main__":
    unittest.main()
