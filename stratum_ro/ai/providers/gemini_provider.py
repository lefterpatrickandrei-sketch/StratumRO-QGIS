# -*- coding: utf-8 -*-
"""
Google Gemini API Provider for StratumRO.

Why this provider exists (measured 2026-10-08):
  The previous VLM audit had exactly ONE paid route left (NVIDIA NIM), and
  `meta/llama-3.2-11b-vision-instruct` failed the falsification controls with
  1/9 discrimination (it approved pure noise). Gemini's free tier model
  `gemini-3.1-flash-lite` passed 4/4 controls: it rejected noise, solid red and
  solid white chips and correctly described the real building chip.

Implements a real multimodal path: `kwargs["images"]` is a list of base64
JPEG/PNG payloads (raw base64 or a data: URL) and is forwarded as
`inline_data` parts. `raw_payload["images_sent"]` reports how many images
actually reached the model, so callers can refuse text-only verdicts.

Note: `system_instruction` is the correct Gemini field for a system prompt;
older `systemInstruction` casing is silently ignored by some deployments.
"""

import time
from typing import Any, Dict, List, Optional

import requests

from .base import (
    BaseAIProvider,
    ProviderCapability,
    ProviderResponse,
    extract_json,
    read_env_file_key,
)

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_VISION_MODEL = "gemini-3.1-flash-lite"
DEFAULT_TEXT_MODEL = "gemini-3.1-flash-lite"


def _strip_data_url(b64: str) -> str:
    """Returns raw base64 from either 'data:image/jpeg;base64,XXX' or 'XXX'."""
    if b64.startswith("data:"):
        return b64.split(",", 1)[-1]
    return b64


class GeminiProvider(BaseAIProvider):
    """Google Gemini API (generativelanguage.googleapis.com) provider."""

    def __init__(
        self,
        name: str = "gemini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        super().__init__(name)
        self.api_key = api_key or read_env_file_key("GEMINI_API_KEY")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.default_model = default_model or DEFAULT_TEXT_MODEL

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return bool(self.api_key)

    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.REASONING,
            ProviderCapability.PLANNING,
            ProviderCapability.VISION,
            ProviderCapability.CODE_ANALYSIS,
        ]

    def list_models(self) -> List[str]:
        """Returns the model ids Gemini currently exposes for this key."""
        if not self.api_key:
            return []
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers={"x-goog-api-key": self.api_key},
                timeout=20,
            )
            if r.status_code != 200:
                return []
            out = []
            for m in r.json().get("models", []):
                mid = m.get("name", "")
                if mid.startswith("models/"):
                    out.append(mid.split("/", 1)[1])
            return out
        except Exception:
            return []

    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        **kwargs
    ) -> ProviderResponse:
        t0 = time.time()
        chosen_model = model or self.default_model

        if not self.api_key:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=0.0,
                error="GEMINI_API_KEY not configured",
            )

        # Build the parts list. Images first-class: never silently dropped.
        parts: List[Dict[str, Any]] = []
        images: Optional[List[str]] = kwargs.get("images")
        if images:
            for img in images:
                parts.append({
                    "inline_data": {
                        "mime_type": kwargs.get("mime_type", "image/jpeg"),
                        "data": _strip_data_url(img),
                    }
                })
        parts.append({"text": prompt})

        body: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.0),
                "maxOutputTokens": kwargs.get("max_tokens", 800),
            },
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        # The free tier enforces a requests-per-minute quota and answers 429
        # once a burst exceeds it, so honour Retry-After and back off.
        attempts = int(kwargs.get("max_attempts", 4))
        resp = None
        for attempt in range(attempts):
            try:
                resp = requests.post(
                    f"{self.base_url}/models/{chosen_model}:generateContent",
                    headers={"x-goog-api-key": self.api_key,
                             "content-type": "application/json"},
                    json=body,
                    timeout=timeout,
                )
            except Exception as e:
                return ProviderResponse(
                    content="",
                    model_name=chosen_model,
                    provider_name=self.name,
                    status="failed",
                    duration_sec=round(time.time() - t0, 3),
                    error=f"Gemini request exception: {e}",
                )
            if resp.status_code not in (429, 503) or attempt == attempts - 1:
                break
            retry_after = resp.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else 0.0
            except ValueError:
                wait = 0.0
            wait = max(wait, 8.0 * (2 ** attempt))
            if wait > 90.0:
                break
            time.sleep(wait)

        if resp is None:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=round(time.time() - t0, 3),
                error="Gemini: no response",
            )

        elapsed = round(time.time() - t0, 3)

        if resp.status_code != 200:
            detail = resp.text[:300]
            # Extract the most useful message when Google returns structured errors.
            try:
                detail = resp.json().get("error", {}).get("message", detail)
            except Exception:
                pass
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=elapsed,
                error=f"Gemini HTTP {resp.status_code}: {detail}",
            )

        try:
            data = resp.json()
        except Exception as e:
            return ProviderResponse(
                content="",
                model_name=chosen_model,
                provider_name=self.name,
                status="failed",
                duration_sec=elapsed,
                error=f"Gemini response not JSON: {e}",
            )

        # Assemble text from all parts (a model may interleave thoughts).
        raw_text = ""
        try:
            for cand in data.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    if "text" in part:
                        raw_text += part["text"]
        except Exception:
            raw_text = ""

        usage = data.get("usageMetadata", {}) or {}
        data["images_sent"] = len([p for p in parts if "inline_data" in p])

        return ProviderResponse(
            content=raw_text,
            model_name=chosen_model,
            provider_name=self.name,
            status="success" if raw_text else "failed",
            duration_sec=elapsed,
            raw_payload=data,
            parsed_json=extract_json(raw_text),
            usage=usage,
            error=None if raw_text else "Gemini returned an empty completion",
        )