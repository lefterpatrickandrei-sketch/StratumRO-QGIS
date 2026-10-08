# -*- coding: utf-8 -*-
"""
Anthropic Claude Provider for StratumRO.
Integrates Claude 3.5 Sonnet, Claude 3.7 Sonnet, and Claude 3.5 Haiku
for rigorous architectural reviews, code auditing, and cadastral edge-case reasoning.
"""

import time
from typing import Any, Dict, List, Optional
from .base import BaseAIProvider, ProviderCapability, ProviderResponse, extract_json, read_env_file_key


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude provider for deep reasoning, architectural reviews, and adversarial audits.
    """

    DEFAULT_MODELS = [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-7-sonnet-latest",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "claude-3-5-sonnet-latest"
    ):
        super().__init__(name="anthropic")
        self.api_key = api_key if api_key is not None else (read_env_file_key("ANTHROPIC_API_KEY") or "")
        self.default_model = default_model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))

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
        timeout: float = 15.0,
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
                error="ANTHROPIC_API_KEY not configured or invalid."
            )

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key, timeout=timeout)

            # Real multimodal payload: Anthropic image content blocks.
            # Previously the images kwarg was dropped here even though this
            # provider advertised ProviderCapability.VISION.
            images: Optional[List[str]] = kwargs.get("images")
            if images:
                user_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
                for img in images:
                    if img.startswith("http://") or img.startswith("https://"):
                        user_content.append({"type": "image", "source": {"type": "url", "url": img}})
                    else:
                        if img.startswith("data:"):
                            img = img.split(",", 1)[-1]
                        user_content.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": img},
                        })
                message_content: Any = user_content
            else:
                message_content = prompt

            call_kwargs: Dict[str, Any] = {
                "model": chosen_model,
                "max_tokens": kwargs.get("max_tokens", 1500),
                "messages": [{"role": "user", "content": message_content}],
            }
            # anthropic>=1.x Messages.create() exposes no `temperature` parameter
            # (it is rejected as an unexpected kwarg), so it must not be passed.
            # Temperature is set through extra_body instead, when requested.
            if "temperature" in kwargs:
                call_kwargs["extra_body"] = {"temperature": kwargs["temperature"]}
            if system_prompt:
                call_kwargs["system"] = system_prompt

            response = client.messages.create(**call_kwargs)
            elapsed = time.time() - t0

            raw_text = ""
            for block in response.content:
                if getattr(block, "type", "") == "text":
                    raw_text += getattr(block, "text", "")

            parsed = extract_json(raw_text)

            usage_dict = {}
            if hasattr(response, "usage"):
                usage_dict = {
                    "input_tokens": getattr(response.usage, "input_tokens", 0),
                    "output_tokens": getattr(response.usage, "output_tokens", 0),
                }

            return ProviderResponse(
                content=raw_text,
                model_name=chosen_model,
                provider_name=self.name,
                status="success",
                duration_sec=round(elapsed, 3),
                raw_payload={"id": response.id, "model": response.model,
                             "images_sent": len(images) if images else 0},
                parsed_json=parsed,
                usage=usage_dict
            )

        except Exception as e:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=round(time.time() - t0, 3),
                error=f"Anthropic error: {str(e)}"
            )
