"""Focused tests: Gemini failure → deterministic fallback.

Verifies that every failure mode (503, 429 quota, timeout, network error,
malformed response) causes the document pipeline to fall back cleanly to
deterministic extraction WITHOUT leaving the document stuck or partially
corrupting any persistence state.

All tests are offline — subprocess.run is mocked throughout.
No live Gemini calls are made.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from ml.ai.client.client import AIClient, TRANSIENT_ERRORS, _BASE_BACKOFF_SECONDS
from ml.ai.errors import (
    AIAuthenticationError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIQuotaExhaustedError,
    AIRateLimitError,
    AITimeoutError,
)
from ml.ai.pipeline_integration import AIPipelineCoordinator
from ml.ai.providers.gemini import GeminiReasoningProvider
from ml.ai.types import MultimodalInput, InputType
from ml.config import MLConfig
from ml.pipeline import process_document

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_SUBPROCESS = "ml.ai.providers.gemini.subprocess.run"
_PATCH_SLEEP = "ml.ai.client.client.time.sleep"


def _text_input(text: str) -> MultimodalInput:
    return MultimodalInput.from_text(text)


def _mock_curl_response(body, status_code: int) -> MagicMock:
    """Build a successful curl completion with given HTTP status."""
    mock_resp = MagicMock()
    mock_resp.returncode = 0
    body_str = json.dumps(body) if isinstance(body, dict) else body
    mock_resp.stdout = f"{body_str}\n{status_code}"
    return mock_resp


def _mock_curl_network_error(returncode: int = 7) -> MagicMock:
    """Simulate curl non-zero exit (e.g. code 7 = couldn't connect, 28 = timeout)."""
    mock_resp = MagicMock()
    mock_resp.returncode = returncode
    mock_resp.stdout = ""
    return mock_resp


def _valid_gemini_body() -> dict:
    return {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps({
                "entities": [{"id": "g_1", "type": "PERSON", "name": "Test Person", "confidence": 0.9}],
                "relationships": [],
                "patterns": [],
                "leads": [],
            })}]},
            "finishReason": "STOP",
        }],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20, "totalTokenCount": 30},
    }


# ---------------------------------------------------------------------------
# 1. Error classification tests
# ---------------------------------------------------------------------------

class TestGeminiErrorClassification(unittest.TestCase):
    """Verify the provider raises the correct error subclass for each HTTP status."""

    def setUp(self):
        self.provider = GeminiReasoningProvider(api_key="fake_key", model_name="gemini-test")
        self.fake_input = _text_input("test document")

    def test_503_raises_provider_unavailable(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_500_raises_provider_unavailable(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 500)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_429_rate_limit_raises_rate_limit_error(self):
        # Generic 429 without quota keywords -> AIRateLimitError
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({"error": {"message": "rate limited"}}, 429)):
            with self.assertRaises(AIRateLimitError):
                self.provider.analyze(self.fake_input)

    def test_429_quota_exhausted_raises_quota_error(self):
        # 429 with "quota" in body -> AIQuotaExhaustedError (subclass of AIRateLimitError)
        body = {"error": {"message": "RESOURCE_EXHAUSTED: Quota exceeded for daily quota"}}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(body, 429)):
            with self.assertRaises(AIQuotaExhaustedError):
                self.provider.analyze(self.fake_input)

    def test_curl_code_28_raises_provider_unavailable(self):
        # curl code 28 = operation timed out
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(28)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_curl_code_7_raises_provider_unavailable(self):
        # curl code 7 = couldn't connect
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(7)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_subprocess_timeout_raises_ai_timeout(self):
        with patch(_PATCH_SUBPROCESS, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)):
            with self.assertRaises(AITimeoutError):
                self.provider.analyze(self.fake_input)

    def test_malformed_response_raises_malformed(self):
        bad = {"candidates": [{"content": {"parts": [{"text": "NOT VALID JSON !!!"}]}, "finishReason": "STOP"}]}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(bad, 200)):
            with self.assertRaises(AIMalformedResponseError):
                self.provider.analyze(self.fake_input)

    def test_successful_200_returns_model_response(self):
        from ml.ai.types import ModelResponse
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(_valid_gemini_body(), 200)):
            response = self.provider.analyze(self.fake_input)
        self.assertIsInstance(response, ModelResponse)
        self.assertEqual(response.provider_name, "gemini")


# ---------------------------------------------------------------------------
# 2. Client retry/backoff behaviour tests
# ---------------------------------------------------------------------------

class TestClientRetryBehaviour(unittest.TestCase):
    """Verify the AIClient retry/backoff/non-retry rules."""

    def _make_client(self, max_retries: int = 2) -> AIClient:
        provider = GeminiReasoningProvider(api_key="fake_key")
        return AIClient(provider, max_retries=max_retries)

    def test_503_is_retried_up_to_max_retries(self):
        """AIProviderUnavailableError (503) must now be retried."""
        client = self._make_client(max_retries=2)
        fake_input = _text_input("doc")

        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)) as mock_sub, \
             patch(_PATCH_SLEEP) as mock_sleep:
            with self.assertRaises(AIProviderUnavailableError):
                client.analyze(fake_input)

        # 1 initial + 2 retries = 3 total subprocess calls
        self.assertEqual(mock_sub.call_count, 3)
        # Backoff sleep must be called between retries (2 times for 2 retries)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_503_backoff_is_exponential(self):
        """Each retry backoff must double."""
        client = self._make_client(max_retries=2)
        fake_input = _text_input("doc")

        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)), \
             patch(_PATCH_SLEEP) as mock_sleep:
            with self.assertRaises(AIProviderUnavailableError):
                client.analyze(fake_input)

        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        # First backoff = 0.5s, second backoff = 1.0s
        self.assertAlmostEqual(sleep_args[0], 0.5, places=5)
        self.assertAlmostEqual(sleep_args[1], 1.0, places=5)

    def test_quota_exhausted_is_not_retried(self):
        """AIQuotaExhaustedError (429 quota) must NOT be retried."""
        client = self._make_client(max_retries=2)
        fake_input = _text_input("doc")

        quota_body = {"error": {"message": "quota exhausted for daily limit"}}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(quota_body, 429)) as mock_sub, \
             patch(_PATCH_SLEEP) as mock_sleep:
            with self.assertRaises(AIQuotaExhaustedError):
                client.analyze(fake_input)

        # Must stop after first attempt
        self.assertEqual(mock_sub.call_count, 1)
        self.assertEqual(mock_sleep.call_count, 0)

    def test_auth_error_is_not_retried(self):
        """401 must not be retried."""
        client = self._make_client(max_retries=2)
        fake_input = _text_input("doc")

        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 401)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIAuthenticationError):
                client.analyze(fake_input)

        self.assertEqual(mock_sub.call_count, 1)

    def test_transient_then_success_returns_result(self):
        """One 503 then 200 -> client retries and succeeds."""
        from ml.ai.types import ModelResponse
        client = self._make_client(max_retries=2)
        fake_input = _text_input("doc")

        responses = [
            _mock_curl_response({}, 503),
            _mock_curl_response(_valid_gemini_body(), 200),
        ]
        with patch(_PATCH_SUBPROCESS, side_effect=responses), \
             patch(_PATCH_SLEEP):
            result = client.analyze(fake_input)

        self.assertIsInstance(result, ModelResponse)

    def test_timeout_is_retried(self):
        """AITimeoutError must be retried."""
        client = self._make_client(max_retries=1)
        fake_input = _text_input("doc")

        with patch(_PATCH_SUBPROCESS, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AITimeoutError):
                client.analyze(fake_input)

        self.assertEqual(mock_sub.call_count, 2)  # 1 initial + 1 retry

    def test_curl_network_error_is_retried(self):
        """curl code 28 (network/timeout) must be retried."""
        client = self._make_client(max_retries=1)
        fake_input = _text_input("doc")

        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(28)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIProviderUnavailableError):
                client.analyze(fake_input)

        self.assertEqual(mock_sub.call_count, 2)


# ---------------------------------------------------------------------------
# 3. Pipeline coordinator fallback tests
# ---------------------------------------------------------------------------

class TestPipelineCoordinatorFallback(unittest.TestCase):
    """Verify AIPipelineCoordinator falls back to deterministic extraction on every error."""

    def _make_gemini_config(self) -> MLConfig:
        return MLConfig(
            ai_enabled=True,
            ai_provider="gemini",
            ai_api_key="fake_key_for_testing",
            ai_model="gemini-test",
            ai_max_retries=0,  # no retries in coordinator-level tests to keep them fast
        )

    def _run_pipeline(self, text: str, config=None):
        cfg = config or self._make_gemini_config()
        return process_document("doc_fallback_001", text, config=cfg)

    def test_503_fallback_returns_deterministic_result(self):
        """503 from Gemini -> pipeline completes with deterministic output."""
        text = "Rajan Das called 9999888800 from Mumbai on 12/12/2026."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_fallback_001")
        self.assertGreater(len(result.entities), 0)

    def test_429_quota_fallback_returns_deterministic_result(self):
        """Quota exhausted -> pipeline completes with deterministic output, no retry."""
        text = "Amit Singh transferred 50000 to Priya Sharma on 2026-09-10."
        quota_body = {"error": {"message": "quota exhausted daily limit"}}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(quota_body, 429)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_fallback_001")
        self.assertGreater(len(result.entities), 0)

    def test_timeout_fallback_returns_deterministic_result(self):
        """subprocess.TimeoutExpired -> pipeline completes with deterministic output."""
        text = "Suspect Rahul Kumar spotted at Delhi Railway Station."
        with patch(_PATCH_SUBPROCESS, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_fallback_001")

    def test_network_error_fallback_returns_deterministic_result(self):
        """curl code 28 network error -> deterministic fallback."""
        text = "Call detail record for 9876543210 and 9123456789."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(28)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_fallback_001")

    def test_malformed_gemini_response_fallback(self):
        """Malformed JSON response -> deterministic fallback."""
        text = "Suspect last seen at Juhu Beach, Mumbai."
        bad_body = {"candidates": [{"content": {"parts": [{"text": "{{not valid json"}]}, "finishReason": "STOP"}]}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(bad_body, 200)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_fallback_001")

    def test_ai_disabled_runs_deterministic_only(self):
        """ai_enabled=False must run pure deterministic pipeline, no Gemini calls at all."""
        text = "Anand Mishra flew to Goa on 2026-09-01."
        with patch(_PATCH_SUBPROCESS) as mock_sub:
            result = process_document(
                "doc_no_ai_001",
                text,
                config=MLConfig(ai_enabled=False),
            )
        mock_sub.assert_not_called()
        self.assertEqual(result.document_id, "doc_no_ai_001")

    def test_successful_gemini_response_used(self):
        """200 from Gemini -> pipeline completes successfully."""
        text = "Test Person met another person in Delhi."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(_valid_gemini_body(), 200)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_fallback_001")
        self.assertIsNotNone(result.entities)

    def test_document_always_reaches_terminal_state_after_503(self):
        """process_document must never hang or raise an uncaught exception on 503."""
        text = "Some investigation text about suspect activities in Kolkata."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertIsNotNone(result)

    def test_repeated_processing_same_document_stable(self):
        """Processing the same document twice must return identical structure."""
        text = "Vijay Mehta called 9988776655 from Pune on 01/09/2026."
        config = MLConfig(ai_enabled=False)
        result1 = process_document("doc_idempotent_001", text, config=config)
        result2 = process_document("doc_idempotent_001", text, config=config)
        names1 = sorted(e.name for e in result1.entities)
        names2 = sorted(e.name for e in result2.entities)
        self.assertEqual(names1, names2)

    def test_partial_gemini_failure_does_not_corrupt_deterministic_entities(self):
        """If understand_document succeeds but entity extraction fails, retain deterministic entities."""
        text = "Prakash Iyer called 9876000001 from Chennai."
        config = self._make_gemini_config()

        # First call succeeds (understand_document), subsequent calls fail
        responses = [
            _mock_curl_response(_valid_gemini_body(), 200),
            _mock_curl_response({}, 503),
        ]
        with patch(_PATCH_SUBPROCESS, side_effect=responses), \
             patch(_PATCH_SLEEP):
            result = process_document("doc_partial_001", text, config=config)

        self.assertEqual(result.document_id, "doc_partial_001")
        self.assertGreater(len(result.entities), 0)


# ---------------------------------------------------------------------------
# 4. TRANSIENT_ERRORS registration tests
# ---------------------------------------------------------------------------

class TestTransientErrorRegistration(unittest.TestCase):
    """Verify the TRANSIENT_ERRORS tuple is correctly configured."""

    def test_provider_unavailable_is_transient(self):
        self.assertTrue(issubclass(AIProviderUnavailableError, TRANSIENT_ERRORS))

    def test_timeout_is_transient(self):
        self.assertTrue(issubclass(AITimeoutError, TRANSIENT_ERRORS))

    def test_rate_limit_is_transient(self):
        self.assertTrue(issubclass(AIRateLimitError, TRANSIENT_ERRORS))

    def test_quota_exhausted_is_subclass_of_rate_limit(self):
        self.assertTrue(issubclass(AIQuotaExhaustedError, AIRateLimitError))

    def test_quota_exhausted_stops_after_one_call(self):
        """The client catches AIQuotaExhaustedError before TRANSIENT_ERRORS."""
        provider = GeminiReasoningProvider(api_key="fake_key")
        client = AIClient(provider, max_retries=2)
        fake_input = _text_input("test")

        quota_body = {"error": {"message": "quota exhausted"}}
        call_count = 0

        def counting_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _mock_curl_response(quota_body, 429)

        with patch(_PATCH_SUBPROCESS, side_effect=counting_subprocess), \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIQuotaExhaustedError):
                client.analyze(fake_input)

        self.assertEqual(call_count, 1)

    def test_backoff_base_is_reasonable(self):
        self.assertGreater(_BASE_BACKOFF_SECONDS, 0)
        self.assertLessEqual(_BASE_BACKOFF_SECONDS, 2.0)


# ---------------------------------------------------------------------------
# 5. ML-level idempotency tests
# ---------------------------------------------------------------------------

class TestMlLevelIdempotency(unittest.TestCase):

    def test_entity_ids_are_sequential_and_deterministic(self):
        """Same text -> same entity IDs in same order across calls."""
        text = "Suresh Patel transferred 100000 to Manoj Kumar from SBI account 123456."
        config = MLConfig(ai_enabled=False)
        r1 = process_document("idempotent_doc", text, config=config)
        r2 = process_document("idempotent_doc", text, config=config)
        ids1 = [e.id for e in r1.entities]
        ids2 = [e.id for e in r2.entities]
        self.assertEqual(ids1, ids2)

    def test_fallback_after_503_produces_same_entities_as_ai_disabled(self):
        """Entities from fallback path must match entities from ai_disabled path."""
        text = "Arun Joshi called 9001234567 from Delhi on 10/10/2026."
        config_ai = MLConfig(
            ai_enabled=True, ai_provider="gemini",
            ai_api_key="fake_key", ai_model="gemini-test", ai_max_retries=0
        )
        config_det = MLConfig(ai_enabled=False)

        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)), \
             patch(_PATCH_SLEEP):
            result_fallback = process_document("doc_compare_001", text, config=config_ai)
        result_det = process_document("doc_compare_001", text, config=config_det)

        names_fb = sorted(e.name for e in result_fallback.entities)
        names_det = sorted(e.name for e in result_det.entities)
        self.assertEqual(names_fb, names_det)


if __name__ == "__main__":
    unittest.main()
