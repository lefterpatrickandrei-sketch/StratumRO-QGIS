# -*- coding: utf-8 -*-
"""
NVIDIA NIM AI Provider for StratumRO.
Connects to NVIDIA NIM endpoints (https://integrate.api.nvidia.com/v1)
supporting Llama 3.2 11B/90B Vision Instruct and Llama 3.3 70B Instruct.
"""

import time
from typing import Any, Dict, List, Optional
from .base import BaseAIProvider, ProviderCapability, ProviderResponse, extract_json, read_env_file_key


class NvidiaNIMProvider(BaseAIProvider):
    """
    NVIDIA NIM inference provider using OpenAI-compatible REST endpoints.
    """

    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
    DEFAULT_MODELS = [
        "meta/llama-3.3-70b-instruct",
        "nemotron-4-340b",
        "meta-llama/llama-3.1-8b-instruct",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "meta/llama-3.3-70b-instruct"
    ):
        super().__init__(name="nvidia_nim")
        self.api_key = api_key if api_key is not None else (read_env_file_key("NVIDIA_API_KEY") or "")
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.default_model = default_model

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.VISION,
            ProviderCapability.REASONING,
            ProviderCapability.PLANNING,
        ]

    def list_models(self) -> List[str]:
        return list(self.DEFAULT_MODELS)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
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
                error="NVIDIA_API_KEY not configured or empty."
            )

        images: Optional[List[str]] = kwargs.get("images")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if images:
            user_content = [{"type": "text", "text": prompt}]
            for img in images:
                if img.startswith("http://") or img.startswith("https://") or img.startswith("data:"):
                    url = img
                else:
                    url = f"data:image/jpeg;base64,{img}"
                user_content.append({"type": "image_url", "image_url": {"url": url}})
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": prompt})

        # Try OpenAI client wrapper first
        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            completion = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 800),
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
                raw_payload={"choices": [c.message.to_dict() if hasattr(c.message, 'to_dict') else str(c.message) for c in completion.choices]},
                parsed_json=parsed,
                usage=completion.usage.to_dict() if hasattr(completion, 'usage') and hasattr(completion.usage, 'to_dict') else {}
            )

        except Exception as e:
            # Direct requests fallback
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "model": chosen_model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.1),
                    "max_tokens": kwargs.get("max_tokens", 800)
                }
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                    timeout=timeout
                )
                elapsed = time.time() - t0
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["choices"][0]["message"]["content"]
                    return ProviderResponse(
                        content=raw_text,
                        model_name=chosen_model,
                        provider_name=self.name,
                        status="success",
                        duration_sec=round(elapsed, 3),
                        raw_payload=data,
                        parsed_json=extract_json(raw_text),
                        usage=data.get("usage", {})
                    )
                else:
                    return ProviderResponse(
                        content="",
                        model_name=chosen_model,
                        provider_name=self.name,
                        status="failed",
                        duration_sec=round(elapsed, 3),
                        error=f"NVIDIA NIM HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as req_err:
                return ProviderResponse(
                    content="",
                    model_name=chosen_model,
                    provider_name=self.name,
                    status="failed",
                    duration_sec=round(time.time() - t0, 3),
                    error=f"NVIDIA NIM request error: {str(req_err)}"
                )
