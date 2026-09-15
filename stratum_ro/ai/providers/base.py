# -*- coding: utf-8 -*-
"""
Base AI Provider Interface for StratumRO.
Defines common data structures and abstract contract for all model providers.
"""

import os
import re
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProviderCapability(str, Enum):
    REASONING = "reasoning"
    PLANNING = "planning"
    VISION = "vision"
    LOCAL_INFERENCE = "local_inference"
    CODE_ANALYSIS = "code_analysis"


@dataclass
class ProviderResponse:
    content: str
    model_name: str
    provider_name: str
    status: str = "success"  # "success", "failed", "fallback"
    duration_sec: float = 0.0
    raw_payload: Optional[Dict[str, Any]] = None
    parsed_json: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)

    def is_ok(self) -> bool:
        return self.status in ("success", "fallback") and self.content is not None


def extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts the first valid JSON dictionary from LLM completion text,
    cleaning markdown code blocks (```json ... ```) if present.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    try:
        # Check if already clean JSON
        return json.loads(raw_text.strip())
    except Exception:
        pass

    try:
        # Regex search for the outermost {...} block
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return None


def read_env_file_key(key_name: str) -> Optional[str]:
    """
    Safely reads an API key from system environment variables,
    falling back to reading .env in the project root if present.
    """
    val = os.getenv(key_name)
    if val:
        return val.strip()

    # Search for .env up to 3 parent directories
    curr = Path(__file__).resolve().parent
    for _ in range(4):
        env_file = curr / ".env"
        if env_file.is_file():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f"{key_name}="):
                            _, v = line.split("=", 1)
                            return v.strip().strip('"').strip("'")
            except Exception:
                pass
            break
        curr = curr.parent

    return None


class BaseAIProvider(ABC):
    """
    Abstract contract for model providers in StratumRO.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and reachable."""
        pass

    @abstractmethod
    def capabilities(self) -> List[ProviderCapability]:
        """Returns the list of capabilities supported by this provider."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """Lists active models provided by this provider."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
        **kwargs
    ) -> ProviderResponse:
        """
        Executes a completion request against the provider.
        Must never throw unhandled exceptions to the caller;
        returns a ProviderResponse with status='failed' on error.
        """
        pass
