"""Mocked unit tests for GroqReasoningProvider.

Covers:
1. Provider initialization (empty key, model name)
2. Successful Groq response
3. Malformed response
4. HTTP authentication failure (401/403)
5. Rate limit (429)
6. Provider unavailable (503/500)
7. Timeout / network failure
8. Pipeline fallback to deterministic ML on Groq failure

All tests are offline — subprocess.run is mocked throughout.
No live Groq calls are made.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from ml.ai.client.client import AIClient
from ml.ai.errors import (
    AIAuthenticationError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIQuotaExhaustedError,
    AIRateLimitError,
    AITimeoutError,
)
from ml.ai.providers.groq import GroqReasoningProvider
from ml.ai.types import ModelResponse, MultimodalInput
from ml.config import MLConfig
from ml.pipeline import process_document

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_SUBPROCESS = "ml.ai.providers.groq.subprocess.run"
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
    """Simulate curl non-zero exit (e.g. code 7 = couldn't connect)."""
    mock_resp = MagicMock()
    mock_resp.returncode = returncode
    mock_resp.stdout = ""
    return mock_resp


def _valid_groq_body() -> dict:
    """Groq/OpenAI-compatible response body."""
    return {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "entities": [
                        {"id": "g_1", "type": "PERSON", "name": "Test Person", "confidence": 0.9},
                    ],
                    "relationships": [],
                    "patterns": [],
                    "leads": [],
                })
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


# ---------------------------------------------------------------------------
# 1. Provider initialization tests
# ---------------------------------------------------------------------------

class TestGroqProviderInit(unittest.TestCase):

    def test_empty_key_raises_auth_error(self):
        with self.assertRaises(AIAuthenticationError):
            GroqReasoningProvider(api_key="")

    def test_provider_name(self):
        p = GroqReasoningProvider(api_key="fake_key")
        self.assertEqual(p.provider_name, "groq")

    def test_is_available_with_key(self):
        p = GroqReasoningProvider(api_key="fake_key")
        self.assertTrue(p.is_available)

    def test_health_check(self):
        p = GroqReasoningProvider(api_key="fake_key")
        self.assertTrue(p.health_check())

    def test_custom_model_name(self):
        p = GroqReasoningProvider(api_key="fake_key", model_name="custom-model")
        self.assertEqual(p._model_name, "custom-model")


# ---------------------------------------------------------------------------
# 2. Successful response tests
# ---------------------------------------------------------------------------

class TestGroqSuccessResponse(unittest.TestCase):

    def setUp(self):
        self.provider = GroqReasoningProvider(api_key="fake_key", model_name="groq-test")
        self.fake_input = _text_input("test document")

    def test_200_returns_model_response(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(_valid_groq_body(), 200)):
            response = self.provider.analyze(self.fake_input)
        self.assertIsInstance(response, ModelResponse)
        self.assertEqual(response.provider_name, "groq")
        self.assertEqual(response.model_name, "groq-test")

    def test_response_has_entities(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(_valid_groq_body(), 200)):
            response = self.provider.analyze(self.fake_input)
        self.assertIn("entities", response.structured_payload)
        self.assertGreater(len(response.structured_payload["entities"]), 0)

    def test_response_metadata(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(_valid_groq_body(), 200)):
            response = self.provider.analyze(self.fake_input)
        self.assertIn("groq_finish_reason", response.metadata)


# ---------------------------------------------------------------------------
# 3. Malformed response tests
# ---------------------------------------------------------------------------

class TestGroqMalformedResponse(unittest.TestCase):

    def setUp(self):
        self.provider = GroqReasoningProvider(api_key="fake_key")
        self.fake_input = _text_input("test doc")

    def test_invalid_json_raises_malformed(self):
        bad = {"choices": [{"message": {"content": "NOT VALID JSON !!!"}, "finish_reason": "stop"}]}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(bad, 200)):
            with self.assertRaises(AIMalformedResponseError):
                self.provider.analyze(self.fake_input)

    def test_missing_choices_raises_malformed(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 200)):
            with self.assertRaises(AIMalformedResponseError):
                self.provider.analyze(self.fake_input)


# ---------------------------------------------------------------------------
# 4. HTTP authentication failure tests
# ---------------------------------------------------------------------------

class TestGroqAuthFailure(unittest.TestCase):

    def setUp(self):
        self.provider = GroqReasoningProvider(api_key="fake_key")
        self.fake_input = _text_input("test doc")

    def test_401_raises_auth_error(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 401)):
            with self.assertRaises(AIAuthenticationError):
                self.provider.analyze(self.fake_input)

    def test_403_raises_auth_error(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 403)):
            with self.assertRaises(AIAuthenticationError):
                self.provider.analyze(self.fake_input)

    def test_auth_error_not_retried(self):
        provider = GroqReasoningProvider(api_key="fake_key")
        client = AIClient(provider, max_retries=2)
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 401)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIAuthenticationError):
                client.analyze(self.fake_input)
        self.assertEqual(mock_sub.call_count, 1)


# ---------------------------------------------------------------------------
# 5. Rate limit tests
# ---------------------------------------------------------------------------

class TestGroqRateLimit(unittest.TestCase):

    def setUp(self):
        self.provider = GroqReasoningProvider(api_key="fake_key")
        self.fake_input = _text_input("test doc")

    def test_429_raises_rate_limit(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({"error": {"message": "rate limited"}}, 429)):
            with self.assertRaises(AIRateLimitError):
                self.provider.analyze(self.fake_input)

    def test_429_quota_exhausted_raises_quota_error(self):
        body = {"error": {"message": "RESOURCE_EXHAUSTED: Quota exceeded for daily quota"}}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(body, 429)):
            with self.assertRaises(AIQuotaExhaustedError):
                self.provider.analyze(self.fake_input)

    def test_quota_exhausted_not_retried(self):
        client = AIClient(self.provider, max_retries=2)
        body = {"error": {"message": "quota exhausted daily limit"}}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(body, 429)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIQuotaExhaustedError):
                client.analyze(self.fake_input)
        self.assertEqual(mock_sub.call_count, 1)


# ---------------------------------------------------------------------------
# 6. Provider unavailable tests
# ---------------------------------------------------------------------------

class TestGroqUnavailable(unittest.TestCase):

    def setUp(self):
        self.provider = GroqReasoningProvider(api_key="fake_key")
        self.fake_input = _text_input("test doc")

    def test_503_raises_unavailable(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_500_raises_unavailable(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 500)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_503_is_retried(self):
        client = AIClient(self.provider, max_retries=2)
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIProviderUnavailableError):
                client.analyze(self.fake_input)
        self.assertEqual(mock_sub.call_count, 3)


# ---------------------------------------------------------------------------
# 7. Timeout / network failure tests
# ---------------------------------------------------------------------------

class TestGroqTimeoutNetwork(unittest.TestCase):

    def setUp(self):
        self.provider = GroqReasoningProvider(api_key="fake_key")
        self.fake_input = _text_input("test doc")

    def test_curl_code_7_raises_unavailable(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(7)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_curl_code_28_raises_unavailable(self):
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(28)):
            with self.assertRaises(AIProviderUnavailableError):
                self.provider.analyze(self.fake_input)

    def test_subprocess_timeout_raises_ai_timeout(self):
        with patch(_PATCH_SUBPROCESS, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)):
            with self.assertRaises(AITimeoutError):
                self.provider.analyze(self.fake_input)

    def test_timeout_is_retried(self):
        client = AIClient(self.provider, max_retries=1)
        with patch(_PATCH_SUBPROCESS, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AITimeoutError):
                client.analyze(self.fake_input)
        self.assertEqual(mock_sub.call_count, 2)


# ---------------------------------------------------------------------------
# 8. Pipeline fallback to deterministic ML on Groq failure
# ---------------------------------------------------------------------------

class TestGroqPipelineFallback(unittest.TestCase):

    def _make_groq_config(self) -> MLConfig:
        return MLConfig(
            ai_enabled=True,
            ai_provider="groq",
            ai_api_key="fake_key_for_testing",
            ai_model="groq-test",
            ai_max_retries=0,
        )

    def _run_pipeline(self, text: str, config=None):
        cfg = config or self._make_groq_config()
        return process_document("doc_groq_fallback_001", text, config=cfg)

    def test_503_fallback_returns_deterministic_result(self):
        text = "Rajan Das called 9999888800 from Mumbai on 12/12/2026."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response({}, 503)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_groq_fallback_001")
        self.assertGreater(len(result.entities), 0)

    def test_429_quota_fallback_returns_deterministic_result(self):
        text = "Amit Singh transferred 50000 to Priya Sharma on 2026-09-10."
        quota_body = {"error": {"message": "quota exhausted daily limit"}}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(quota_body, 429)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_groq_fallback_001")
        self.assertGreater(len(result.entities), 0)

    def test_timeout_fallback_returns_deterministic_result(self):
        text = "Suspect Rahul Kumar spotted at Delhi Railway Station."
        with patch(_PATCH_SUBPROCESS, side_effect=subprocess.TimeoutExpired(cmd=["curl"], timeout=16.0)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_groq_fallback_001")

    def test_network_error_fallback(self):
        text = "Call detail record for 9876543210 and 9123456789."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_network_error(28)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_groq_fallback_001")

    def test_malformed_response_fallback(self):
        text = "Suspect last seen at Juhu Beach, Mumbai."
        bad_body = {"choices": [{"message": {"content": "{{not valid json"}, "finish_reason": "stop"}]}
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(bad_body, 200)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_groq_fallback_001")

    def test_successful_groq_response_used(self):
        text = "Test Person met another person in Delhi."
        with patch(_PATCH_SUBPROCESS, return_value=_mock_curl_response(_valid_groq_body(), 200)), \
             patch(_PATCH_SLEEP):
            result = self._run_pipeline(text)
        self.assertEqual(result.document_id, "doc_groq_fallback_001")
        self.assertIsNotNone(result.entities)

    def test_ai_disabled_runs_deterministic_only(self):
        text = "Anand Mishra flew to Goa on 2026-09-01."
        with patch(_PATCH_SUBPROCESS) as mock_sub:
            result = process_document("doc_no_ai_001", text, config=MLConfig(ai_enabled=False))
        mock_sub.assert_not_called()
        self.assertEqual(result.document_id, "doc_no_ai_001")


if __name__ == "__main__":
    unittest.main()
