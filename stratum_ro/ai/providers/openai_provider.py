# -*- coding: utf-8 -*-
"""
OpenAI Platform Provider for StratumRO.
Integrates GPT-4o, GPT-4o-mini, and o3-mini for architectural planning,
failure diagnosis, and high-context cadastral reviews.
"""

import time
from typing import Any, Dict, List, Optional
from .base import BaseAIProvider, ProviderCapability, ProviderResponse, extract_json, read_env_file_key


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI Platform provider for advanced reasoning and multi-step planning.
    """

    DEFAULT_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o"
    ):
        super().__init__(name="openai")
        self.api_key = api_key if api_key is not None else (read_env_file_key("OPENAI_API_KEY") or "")
        self.base_url = base_url or "https://api.openai.com/v1"
        self.default_model = default_model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-"))

    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.REASONING,
            ProviderCapability.PLANNING,
            ProviderCapability.CODE_ANALYSIS,
        ]

    def list_models(self) -> List[str]:
        return list(self.DEFAULT_MODELS)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 12.0,
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
                error="OPENAI_API_KEY not configured or invalid."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            completion = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 1000),
                timeout=timeout,
            )
            elapsed = time.time() - t0
            raw_text = completion.choices[0].message.content or ""
            parsed = extract_json(raw_text)

            return ProviderResponse(
                content=raw_text,
                model_name=chosen_model,
                provider_name=self.name,
                status="success",
                duration_sec=round(elapsed, 3),
                raw_payload={"choices": [str(c.message) for c in completion.choices]},
                parsed_json=parsed,
                usage=completion.usage.to_dict() if hasattr(completion, 'usage') and hasattr(completion.usage, 'to_dict') else {}
            )

        except Exception as e:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=round(time.time() - t0, 3),
                error=f"OpenAI error: {str(e)}"
            )
