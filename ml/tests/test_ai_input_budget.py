"""Mocked tests for the AI input budget (bounded AI overlay).

Covers:
- Normal small input passes through byte-identical (no truncation)
- Oversized input is bounded to budget with head+tail preserved + marker
- Exact boundary (== budget untouched, budget+1 truncated)
- HTTP 413 maps to AIRequestTooLargeError (Groq + Gemini) with no retry
- 413 falls back to deterministic ML
- Deterministic ML still receives the COMPLETE input (head/middle/tail)
- Groq provider selection logs no "Unrecognized provider" warning

All tests are offline. No live calls. Fake keys only.
"""

from __future__ import annotations

import json
import unittest
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from ml.ai.client.client import AIClient, DEFAULT_MAX_INPUT_CHARS
from ml.ai.errors import AIRequestTooLargeError
from ml.ai.pipeline_integration import AIPipelineCoordinator
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.providers.gemini import GeminiReasoningProvider
from ml.ai.providers.groq import GroqReasoningProvider
from ml.ai.types import ModelResponse, MultimodalInput
from ml.config import MLConfig
from ml.pipeline import process_document

_PATCH_GROQ_SUBPROCESS = "ml.ai.providers.groq.subprocess.run"
_PATCH_GEMINI_SUBPROCESS = "ml.ai.providers.gemini.subprocess.run"
_PATCH_SLEEP = "ml.ai.client.client.time.sleep"

BUDGET = 1000


class _RecordingProvider(ReasoningModelProvider):
    """Offline stub that records the exact MultimodalInput it receives."""

    def __init__(self) -> None:
        self.received: list[MultimodalInput] = []

    @property
    def provider_name(self) -> str:
        return "recorder"

    def analyze(
        self,
        input_data: MultimodalInput,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ModelResponse:
        self.received.append(input_data)
        return ModelResponse(
            provider_name="recorder",
            model_name="recorder-v1",
            raw_content="{}",
            structured_payload={"entities": [], "relationships": [], "patterns": [], "leads": []},
        )


def _effective_text(inp: MultimodalInput) -> str:
    if inp.extracted_text is not None:
        return inp.extracted_text
    if isinstance(inp.content, str):
        return inp.content
    return inp.content.decode("utf-8", errors="replace")


def _mock_curl_response(body, status_code: int) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.returncode = 0
    body_str = json.dumps(body) if isinstance(body, dict) else body
    mock_resp.stdout = f"{body_str}\n{status_code}"
    return mock_resp


# ---------------------------------------------------------------------------
# 1. Small input passes through untouched
# ---------------------------------------------------------------------------

class TestSmallInputPassThrough(unittest.TestCase):

    def test_small_input_byte_identical(self):
        provider = _RecordingProvider()
        client = AIClient(provider, max_input_chars=BUDGET)
        original = MultimodalInput.from_text("Short FIR text about Rahul Sharma.")
        client.analyze(original)
        self.assertEqual(len(provider.received), 1)
        self.assertIs(provider.received[0], original)
        self.assertFalse(client.last_input_truncated)

    def test_default_budget_value(self):
        self.assertEqual(DEFAULT_MAX_INPUT_CHARS, 100_000)
        self.assertEqual(MLConfig().ai_max_input_chars, 100_000)


# ---------------------------------------------------------------------------
# 2. Oversized input is bounded with head+tail+marker
# ---------------------------------------------------------------------------

class TestOversizedInputBounded(unittest.TestCase):

    def _run(self, text: str, budget: int = BUDGET):
        provider = _RecordingProvider()
        client = AIClient(provider, max_input_chars=budget)
        client.analyze(MultimodalInput.from_text(text))
        return provider, client

    def test_oversized_bounded_to_budget(self):
        text = "E" * (BUDGET + 5000)
        provider, client = self._run(text)
        sent = _effective_text(provider.received[0])
        self.assertLessEqual(len(sent), BUDGET)
        self.assertTrue(client.last_input_truncated)

    def test_head_and_tail_preserved(self):
        head = "HEADMARKER-" + "A" * 100
        tail = "Z" * 100 + "-TAILMARKER"
        filler_len = (BUDGET + 5000) - len(head) - len(tail)
        text = head + ("M" * filler_len) + tail
        provider, _ = self._run(text)
        sent = _effective_text(provider.received[0])
        self.assertTrue(sent.startswith(head), "beginning must be preserved")
        self.assertTrue(sent.endswith(tail), "closing evidence must be preserved")

    def test_truncation_marker_present(self):
        text = "E" * (BUDGET + 5000)
        provider, _ = self._run(text)
        sent = _effective_text(provider.received[0])
        self.assertIn("AI input truncated", sent)
        self.assertIn("deterministic ML processed the complete document", sent)

    def test_no_document_content_in_logs(self):
        unique = "UNIQUELOGPROBEZZZ9"
        text = unique + ("E" * (BUDGET + 5000))
        provider = _RecordingProvider()
        client = AIClient(provider, max_input_chars=BUDGET)
        with self.assertLogs("ml.ai.client.client", level="WARNING") as cm:
            client.analyze(MultimodalInput.from_text(text))
        combined = "\n".join(cm.output)
        self.assertNotIn(unique, combined)


# ---------------------------------------------------------------------------
# 3. Exact boundary
# ---------------------------------------------------------------------------

class TestExactBoundary(unittest.TestCase):

    def test_exact_budget_untouched(self):
        text = "B" * BUDGET
        provider = _RecordingProvider()
        client = AIClient(provider, max_input_chars=BUDGET)
        original = MultimodalInput.from_text(text)
        client.analyze(original)
        self.assertIs(provider.received[0], original)
        self.assertFalse(client.last_input_truncated)

    def test_budget_plus_one_truncated(self):
        text = "B" * (BUDGET + 1)
        provider = _RecordingProvider()
        client = AIClient(provider, max_input_chars=BUDGET)
        client.analyze(MultimodalInput.from_text(text))
        sent = _effective_text(provider.received[0])
        self.assertLessEqual(len(sent), BUDGET)
        self.assertTrue(client.last_input_truncated)
        self.assertIn("AI input truncated", sent)


# ---------------------------------------------------------------------------
# 4. HTTP 413 mapping + no retry
# ---------------------------------------------------------------------------

class TestRequestTooLargeMapping(unittest.TestCase):

    def test_groq_413_raises_request_too_large(self):
        provider = GroqReasoningProvider(api_key="fake_key")
        with patch(_PATCH_GROQ_SUBPROCESS, return_value=_mock_curl_response({"error": "too large"}, 413)):
            with self.assertRaises(AIRequestTooLargeError):
                provider.analyze(MultimodalInput.from_text("doc"))

    def test_gemini_413_raises_request_too_large(self):
        provider = GeminiReasoningProvider(api_key="fake_key")
        with patch(_PATCH_GEMINI_SUBPROCESS, return_value=_mock_curl_response({"error": "too large"}, 413)):
            with self.assertRaises(AIRequestTooLargeError):
                provider.analyze(MultimodalInput.from_text("doc"))

    def test_413_not_retried(self):
        provider = GroqReasoningProvider(api_key="fake_key")
        client = AIClient(provider, max_retries=2)
        with patch(_PATCH_GROQ_SUBPROCESS, return_value=_mock_curl_response({"error": "too large"}, 413)) as mock_sub, \
             patch(_PATCH_SLEEP):
            with self.assertRaises(AIRequestTooLargeError):
                client.analyze(MultimodalInput.from_text("doc"))
        self.assertEqual(mock_sub.call_count, 1)


# ---------------------------------------------------------------------------
# 5. 413 falls back to deterministic ML
# ---------------------------------------------------------------------------

class TestTooLargeFallback(unittest.TestCase):

    def test_413_fallback_returns_deterministic_result(self):
        text = "Rajan Das called 9999888800 from Mumbai on 12/12/2026."
        config = MLConfig(
            ai_enabled=True, ai_provider="groq",
            ai_api_key="fake_key", ai_model="groq-test", ai_max_retries=0,
        )
        with patch(_PATCH_GROQ_SUBPROCESS, return_value=_mock_curl_response({"error": "too large"}, 413)), \
             patch(_PATCH_SLEEP):
            result = process_document("doc_413_001", text, config=config)
        self.assertEqual(result.document_id, "doc_413_001")
        self.assertGreater(len(result.entities), 0)

    def test_oversized_input_fallback_matches_deterministic(self):
        filler = "Routine observation noted for the record. "
        text = (
            "Rajan Das called 9999888800 from Mumbai on 12/12/2026. "
            + filler * 400
            + " Vikram Nair met Sunita Devi at Chennai airport on 2026-09-01."
        )
        self.assertGreater(len(text), BUDGET)
        config_ai = MLConfig(
            ai_enabled=True, ai_provider="groq",
            ai_api_key="fake_key", ai_model="groq-test",
            ai_max_retries=0, ai_max_input_chars=BUDGET,
        )
        config_det = MLConfig(ai_enabled=False)
        with patch(_PATCH_GROQ_SUBPROCESS, return_value=_mock_curl_response({}, 503)), \
             patch(_PATCH_SLEEP):
            result_fb = process_document("doc_big_001", text, config=config_ai)
        result_det = process_document("doc_big_001", text, config=config_det)
        names_fb = sorted(e.name for e in result_fb.entities)
        names_det = sorted(e.name for e in result_det.entities)
        self.assertEqual(names_fb, names_det)
        self.assertIn("Sunita Devi", names_det)


# ---------------------------------------------------------------------------
# 6. Deterministic ML receives the COMPLETE input
# ---------------------------------------------------------------------------

class TestDeterministicReceivesCompleteInput(unittest.TestCase):

    def test_long_document_deterministic_sees_head_middle_tail(self):
        filler = "Routine observation noted for the record. "
        text = (
            "Rajan Das called 9999888800 from Mumbai on 12/12/2026. "
            + filler * 200
            + " Amit Singh transferred 50000 to Priya Sharma on 2026-09-10. "
            + filler * 200
            + " Vikram Nair met Sunita Devi at Chennai airport on 2026-09-01."
        )
        self.assertGreater(len(text), 3 * BUDGET)
        result = process_document("doc_full_001", text, config=MLConfig(ai_enabled=False))
        names = [e.name for e in result.entities]
        self.assertIn("Rajan Das", names)
        self.assertIn("Priya Sharma", names)
        self.assertIn("Sunita Devi", names)


# ---------------------------------------------------------------------------
# 7. Groq selection: no "Unrecognized provider" warning
# ---------------------------------------------------------------------------

class TestGroqSelectionClean(unittest.TestCase):

    def test_groq_selected_without_unrecognized_warning(self):
        config = MLConfig(
            ai_enabled=True, ai_provider="groq",
            ai_api_key="fake_key", ai_model="groq-test",
            ai_max_retries=0, ai_max_input_chars=BUDGET,
        )
        coord = AIPipelineCoordinator(config=config)
        with self.assertNoLogs("ml.ai.pipeline_integration", level="WARNING"):
            client = coord._ensure_client()
        self.assertIsInstance(client.provider, GroqReasoningProvider)
        self.assertEqual(client.max_input_chars, BUDGET)


if __name__ == "__main__":
    unittest.main()
