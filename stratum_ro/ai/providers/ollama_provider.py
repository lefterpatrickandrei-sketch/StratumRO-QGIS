# -*- coding: utf-8 -*-
"""
Local Ollama Provider for StratumRO.
Connects to a local Ollama daemon (http://localhost:11434) for 100% offline,
zero-cost, private reasoning and planning without sending data to external clouds.
"""

import os
import time
from typing import Any, Dict, List, Optional
from .base import BaseAIProvider, ProviderCapability, ProviderResponse, extract_json


class OllamaProvider(BaseAIProvider):
    """
    Local Ollama inference provider.
    """

    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODELS = ["llama3.2:3b", "qwen2.5-coder:7b", "mistral:7b"]

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: str = "llama3.2:3b"
    ):
        super().__init__(name="ollama")
        self.base_url = (base_url or os.getenv("OLLAMA_HOST") or self.DEFAULT_HOST).rstrip("/")
        self.default_model = default_model
        self._available_cache: Optional[bool] = None
        self._cached_models: List[str] = []

    def is_available(self) -> bool:
        """Pings local Ollama service to verify connectivity."""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                self._cached_models = [m["name"] for m in data.get("models", [])]
                self._available_cache = True
                return True
        except Exception:
            pass
        self._available_cache = False
        return False

    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.LOCAL_INFERENCE,
            ProviderCapability.REASONING,
            ProviderCapability.PLANNING,
        ]

    def list_models(self) -> List[str]:
        if self._cached_models:
            return self._cached_models
        return list(self.DEFAULT_MODELS)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 15.0,
        **kwargs
    ) -> ProviderResponse:
        t0 = time.time()
        chosen_model = model or self.default_model

        if self._available_cache is False:
            # Re-check once
            if not self.is_available():
                return ProviderResponse(
                    content="",
                    model_name=chosen_model,
                    provider_name=self.name,
                    status="failed",
                    duration_sec=0.0,
                    error=f"Ollama server not reachable at {self.base_url}"
                )

        try:
            import requests
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": chosen_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.1),
                    "num_predict": kwargs.get("max_tokens", 800)
                }
            }

            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=timeout
            )
            elapsed = time.time() - t0

            if resp.status_code == 200:
                data = resp.json()
                raw_text = data.get("message", {}).get("content", "")
                parsed = extract_json(raw_text)

                return ProviderResponse(
                    content=raw_text,
                    model_name=chosen_model,
                    provider_name=self.name,
                    status="success",
                    duration_sec=round(elapsed, 3),
                    raw_payload=data,
                    parsed_json=parsed,
                    usage={
                        "total_duration": data.get("total_duration", 0),
                        "eval_count": data.get("eval_count", 0)
                    }
                )
            else:
                return ProviderResponse(
                    content="",
                    model_name=chosen_model,
                    provider_name=self.name,
                    status="failed",
                    duration_sec=round(elapsed, 3),
                    error=f"Ollama error HTTP {resp.status_code}: {resp.text[:200]}"
                )

        except Exception as e:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=round(time.time() - t0, 3),
                error=f"Ollama request error: {str(e)}"
            )
