# -*- coding: utf-8 -*-
"""
Union Alpha Provider for StratumRO.
Integrates stealth/union-alpha via OpenRouter for large-context (256k) repository analysis,
multi-file architectural reasoning, and complex cadastral debugging.
"""

import time
import requests
from typing import Any, Dict, List, Optional
from .base import BaseAIProvider, ProviderCapability, ProviderResponse, extract_json, read_env_file_key


class UnionAlphaProvider(BaseAIProvider):
    """
    Union Alpha provider via OpenRouter endpoint.
    Offers 262k context window and frontier-level code analysis and reasoning.
    """

    DEFAULT_MODELS = [
        "stealth/union-alpha",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "stealth/union-alpha"
    ):
        super().__init__(name="union_alpha")
        self.api_key = (
            api_key
            if api_key is not None
            else (read_env_file_key("UNION_ALPHA_API_KEY") or read_env_file_key("OPENROUTER_API_KEY") or "")
        )
        self.base_url = (base_url or "https://openrouter.ai/api/v1").rstrip("/")
        self.default_model = default_model

    def is_available(self) -> bool:
        return bool(self.api_key and (self.api_key.startswith("sk-or-") or self.api_key.startswith("sk-")))

    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.REASONING,
            ProviderCapability.PLANNING,
            ProviderCapability.CODE_ANALYSIS,
            ProviderCapability.VISION,
        ]

    def list_models(self) -> List[str]:
        return list(self.DEFAULT_MODELS)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> ProviderResponse:
        t0 = time.time()
        chosen_model = model or self.default_model

        if not self.is_available():
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=0.0,
                error="UNION_ALPHA_API_KEY or OPENROUTER_API_KEY not configured or invalid."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS",
            "X-Title": "StratumRO-QGIS",
        }

        payload: Dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }

        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs:
            payload["tool_choice"] = kwargs["tool_choice"]
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            elapsed = time.time() - t0

            if resp.status_code != 200:
                return ProviderResponse(
                    content="",
                    model_name=chosen_model,
                    provider_name=self.name,
                    status="failed",
                    duration_sec=round(elapsed, 3),
                    error=f"Union Alpha HTTP {resp.status_code}: {resp.text[:200]}"
                )

            data = resp.json()
            choices = data.get("choices", [])
            raw_text = choices[0].get("message", {}).get("content", "") if choices else ""
            parsed = extract_json(raw_text)

            return ProviderResponse(
                content=raw_text,
                model_name=chosen_model,
                provider_name=self.name,
                status="success",
                duration_sec=round(elapsed, 3),
                raw_payload={"choices": [str(c.get("message")) for c in choices]},
                parsed_json=parsed,
                usage=data.get("usage", {})
            )

        except Exception as e:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=round(time.time() - t0, 3),
                error=f"Union Alpha error: {str(e)}"
            )
