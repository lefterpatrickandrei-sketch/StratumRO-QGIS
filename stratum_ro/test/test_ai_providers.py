# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Providers.
Tests provider discovery, mock execution, error resilience, and JSON parsing
without requiring active internet connections or live API keys.
"""

import unittest
from unittest.mock import MagicMock, patch

from stratum_ro.ai.providers.base import (
    BaseAIProvider,
    ProviderCapability,
    ProviderResponse,
    extract_json,
    read_env_file_key,
)
from stratum_ro.ai.providers.local_provider import LocalProvider
from stratum_ro.ai.providers.nvidia_nim_provider import NvidiaNIMProvider
from stratum_ro.ai.providers.openai_provider import OpenAIProvider
from stratum_ro.ai.providers.ollama_provider import OllamaProvider


class TestAIProviders(unittest.TestCase):

    def test_extract_json_clean(self):
        raw = '{"project": "StratumRO", "crs": "EPSG:3844"}'
        parsed = extract_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("crs"), "EPSG:3844")

    def test_extract_json_markdown_wrapped(self):
        raw = """Here is the segmentation plan:
```json
{
  "task": "extract_buildings",
  "siruta_code": 26573
}
```
Hope this helps!"""
        parsed = extract_json(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("siruta_code"), 26573)

    def test_extract_json_invalid(self):
        raw = "Not a json response at all."
        self.assertIsNone(extract_json(raw))
        self.assertIsNone(extract_json(None))

    def test_local_provider_always_available(self):
        provider = LocalProvider()
        self.assertTrue(provider.is_available())
        self.assertIn(ProviderCapability.PLANNING, provider.capabilities())

        resp = provider.generate(
            prompt="Plan building extraction",
            context={"siruta_code": 12345, "project_name": "TestCluj"}
        )
        self.assertTrue(resp.is_ok())
        self.assertEqual(resp.status, "fallback")
        self.assertIsNotNone(resp.parsed_json)
        self.assertEqual(resp.parsed_json["administrative"]["siruta_code"], 12345)
        self.assertEqual(resp.parsed_json["crs"], "EPSG:3844")

    def test_nvidia_nim_provider_availability(self):
        # Empty key -> unavailable
        p_empty = NvidiaNIMProvider(api_key="")
        self.assertFalse(p_empty.is_available())
        resp = p_empty.generate("Test prompt")
        self.assertEqual(resp.status, "failed")
        self.assertIn("NVIDIA_API_KEY", resp.error)

        # Valid mock key -> available
        p_valid = NvidiaNIMProvider(api_key="nvapi-valid-mock-key-123456789")
        self.assertTrue(p_valid.is_available())
        self.assertIn(ProviderCapability.VISION, p_valid.capabilities())

    @patch("openai.OpenAI")
    def test_nvidia_nim_provider_mock_generate(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = '{"status": "ok", "buildings_found": 12}'
        mock_choice.message.to_dict.return_value = {"content": mock_choice.message.content}

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.to_dict.return_value = {"total_tokens": 42}
        mock_client.chat.completions.create.return_value = mock_completion

        provider = NvidiaNIMProvider(api_key="nvapi-test-mock-key-12345")
        resp = provider.generate("Analyze buildings", timeout=5.0)

        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.parsed_json.get("buildings_found"), 12)
        self.assertEqual(resp.usage.get("total_tokens"), 42)

    def test_openai_provider_availability(self):
        p_no_key = OpenAIProvider(api_key="")
        self.assertFalse(p_no_key.is_available())
        resp = p_no_key.generate("Test prompt")
        self.assertEqual(resp.status, "failed")

        p_valid = OpenAIProvider(api_key="sk-proj-mock-key-for-test-suite-123")
        self.assertTrue(p_valid.is_available())
        self.assertIn(ProviderCapability.REASONING, p_valid.capabilities())

    @patch("requests.get")
    def test_ollama_provider_detection(self, mock_get):
        provider = OllamaProvider(base_url="http://mock-ollama:11434")

        # Mock unreachable
        mock_get.side_effect = Exception("Connection refused")
        self.assertFalse(provider.is_available())

        # Mock reachable
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "llama3.2:3b"}, {"name": "qwen2.5:7b"}]
        }
        mock_get.side_effect = None
        mock_get.return_value = mock_resp

        self.assertTrue(provider.is_available())
        self.assertIn("llama3.2:3b", provider.list_models())


if __name__ == "__main__":
    unittest.main()
