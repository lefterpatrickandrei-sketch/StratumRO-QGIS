# -*- coding: utf-8 -*-
"""
Smoke test script for NVIDIA NIM API (text and vision capabilities).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratum_ro.ai.providers.nvidia_nim_provider import NvidiaNIMProvider


def test_nvidia():
    provider = NvidiaNIMProvider()
    print("NVIDIA NIM Provider initialized.")
    print(f"Is Available: {provider.is_available()}")
    
    if not provider.is_available():
        print("Error: NVIDIA_API_KEY is missing or invalid.")
        return False
    
    print("\n[1] Testing Reasoning/Text Model (meta/llama-3.3-70b-instruct)...")
    resp = provider.generate(
        prompt="Confirm operational status for StratumRO GeoAI Platform in one sentence.",
        timeout=15.0
    )
    print(f"Status: {resp.status}")
    print(f"Model: {resp.model_name}")
    print(f"Duration: {resp.duration_sec:.2f}s")
    print(f"Error: {resp.error}")
    print(f"Response: {resp.content}")
    
    return resp.is_ok()


if __name__ == "__main__":
    test_nvidia()
