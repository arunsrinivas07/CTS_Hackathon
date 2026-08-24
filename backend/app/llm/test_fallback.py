import unittest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel

from app.llm.factory import FallbackLLMProvider, get_llm_provider, RetryingGroqProvider
from app.llm.gemini.provider import GeminiLLMProvider
from app.llm.errors import RateLimitError, NetworkError, AuthenticationError
from app.llm.config import settings


class TestResponse(BaseModel):
    status: str
    message: str


class TestFallbackMechanism(unittest.TestCase):
    def setUp(self):
        self.primary = RetryingGroqProvider(max_retries=1)
        self.fallback = GeminiLLMProvider()
        self.provider = FallbackLLMProvider(primary=self.primary, fallback=self.fallback)

    @patch("llm.groq_provider.GroqLLMProvider.complete_json")
    @patch("llm.gemini.provider.GeminiLLMProvider.complete_json")
    def test_a_mock_groq_success(self, mock_gemini, mock_groq):
        """Test A: Mock Groq success."""
        mock_groq.return_value = {"status": "ok", "message": "groq success"}
        
        # We need to mock last_trace manually since we mock complete_json
        from app.llm.base import LLMExecutionTrace
        self.primary.primary.last_trace = LLMExecutionTrace(provider="groq", model="test-model", success=True, latency_ms=10)
        
        res = self.provider.complete_json("sys", "user")
        
        self.assertEqual(res["status"], "ok")
        mock_groq.assert_called_once()
        mock_gemini.assert_not_called()
        self.assertFalse(self.provider.last_trace.fallback_used)
        self.assertEqual(self.provider.last_trace.provider, "groq")

    @patch("llm.groq_provider.GroqLLMProvider.complete_json")
    @patch("llm.gemini.provider.GeminiLLMProvider.complete_json")
    def test_b_mock_groq_ratelimit(self, mock_gemini, mock_groq):
        """Test B: Mock Groq RateLimitError."""
        mock_groq.side_effect = RateLimitError("Rate limited")
        mock_gemini.return_value = {"status": "ok", "message": "gemini fallback"}
        
        from app.llm.base import LLMExecutionTrace
        self.fallback.last_trace = LLMExecutionTrace(provider="gemini", model="test-model", success=True, latency_ms=10)

        res = self.provider.complete_json("sys", "user")
        
        self.assertEqual(res["message"], "gemini fallback")
        mock_gemini.assert_called_once()
        self.assertTrue(self.provider.last_trace.fallback_used)
        self.assertEqual(self.provider.last_trace.fallback_reason, "Rate limited")

    @patch("llm.groq_provider.GroqLLMProvider.complete_json")
    @patch("llm.gemini.provider.GeminiLLMProvider.complete_json")
    def test_c_mock_groq_network_error(self, mock_gemini, mock_groq):
        """Test C: Mock Groq Timeout/Network error."""
        mock_groq.side_effect = NetworkError("Network failed")
        mock_gemini.return_value = {"status": "ok", "message": "gemini network fallback"}
        
        from app.llm.base import LLMExecutionTrace
        self.fallback.last_trace = LLMExecutionTrace(provider="gemini", model="test-model", success=True, latency_ms=10)

        res = self.provider.complete_json("sys", "user")
        
        mock_gemini.assert_called_once()
        self.assertTrue(self.provider.last_trace.fallback_used)
        self.assertEqual(self.provider.last_trace.fallback_reason, "Network failed")

    @patch("llm.groq_provider.GroqLLMProvider.complete_json")
    @patch("llm.gemini.provider.GeminiLLMProvider.complete_json")
    def test_d_mock_both_fail(self, mock_gemini, mock_groq):
        """Test D: Mock both Groq and Gemini failure."""
        mock_groq.side_effect = RateLimitError("Groq rate limited")
        mock_gemini.side_effect = RateLimitError("Gemini rate limited")
        
        from app.llm.base import LLMExecutionTrace
        self.fallback.last_trace = LLMExecutionTrace(provider="gemini", model="test-model", success=False, latency_ms=10, error_type="RateLimitError")

        with self.assertRaises(RateLimitError):
            self.provider.complete_json("sys", "user")
            
        self.assertTrue(self.provider.last_trace.fallback_used)


def test_real_gemini_connectivity():
    print("\n--- Running TEST 10: ONE REAL Gemini connectivity test ---")
    provider = GeminiLLMProvider()
    if not provider.api_key:
        print("SKIP: No GEMINI_API_KEY configured.")
        return
    
    try:
        from pydantic import BaseModel
        class MinimalResponse(BaseModel):
            status: str
            
        res = provider.structured_generate("You are a helpful assistant.", "Return JSON with status 'ok'.", MinimalResponse)
        print("Real Gemini Response:", res.model_dump_json())
        print("Real Gemini Trace:", provider.last_trace.model_dump_json(indent=2))
        print("Real Gemini Test: PASS")
    except Exception as e:
        print(f"Real Gemini Test: FAIL ({e})")


if __name__ == "__main__":
    unittest.main(exit=False)
    test_real_gemini_connectivity()
