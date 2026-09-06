# -*- coding: utf-8 -*-
"""
LLM Orchestrator Service for StratumRO.
Implements a resilient Multi-Tier Fallback Chain for NVIDIA NIM and Local Mock fallback,
guaranteeing 100% availability for Stereo70 (EPSG:3844) GeoJSON segmentation plans.
"""

import os
import json
import time
from pathlib import Path
from .logic_handler import extract_json_from_llm, StratumOrchestrator


def _get_api_key() -> str:
    """Reads NVIDIA_API_KEY from environment or .env file."""
    key = os.getenv("NVIDIA_API_KEY")
    if key:
        return key.strip()
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("NVIDIA_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return ""


# Active, verified Fallback Chain for Romanian Geodetic Planning
DEFAULT_FALLBACK_CHAIN = [
    {"name": "meta/llama-3.2-11b-vision-instruct", "timeout": 8.0, "desc": "Tier 1: Fast Multimodal (Llama 3.2 11B)"},
    {"name": "meta/llama-3.2-90b-vision-instruct", "timeout": 10.0, "desc": "Tier 2: Heavy Quality (Llama 3.2 90B)"},
    {"name": "meta/llama-3.3-70b-instruct",        "timeout": 8.0, "desc": "Tier 3: Reasoning Backup (Llama 3.3 70B)"},
    {"name": "local_mock_engine",                  "timeout": 0.1, "desc": "Tier 4: Guaranteed Local Mock Fallback"}
]

SYSTEM_PROMPT = """Ești un orchestrator GIS pentru România (StratumRO). Răspunde EXCLUSIV cu un obiect JSON valid care respectă schema de segmentare.
Nu include explicații sau markdown blocks.
Câmpuri obligatorii:
- project_name (string)
- crs (string, e.g. "EPSG:3844")
- geometry (obiect GeoJSON: type Polygon, coordinates în Stereo 70)
- administrative (obiect: siruta_code int, name string, county string)"""


def request_segmentation_plan(
    siruta_code: int, 
    project_name: str = "StratumRO_Segmentation", 
    chain: list = None
) -> tuple[StratumOrchestrator, str]:
    """
    Executes an automatic Fallback Chain across available models and falls back to local mock
    if network/API issues arise, ensuring zero application crashes.

    :param siruta_code: Romanian SIRUTA administrative code.
    :param project_name: Project label.
    :param chain: Optional custom model fallback chain.
    :return: Tuple of (StratumOrchestrator instance, winning_model_name).
    """
    active_chain = chain or DEFAULT_FALLBACK_CHAIN
    api_key = _get_api_key()

    user_prompt = f"Generează planul de segmentare JSON pentru localitatea cu codul SIRUTA {siruta_code} în sistemul de coordonate Stereo70 (EPSG:3844)."

    client = None
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )
        except ImportError:
            client = None

    for item in active_chain:
        m_name = item["name"]
        t_out = item.get("timeout", 8.0)

        # Tier 4 / Local Offline Mock
        if m_name == "local_mock_engine" or client is None:
            mock_orch = get_mock_segmentation_plan(siruta_code, project_name)
            return mock_orch, "local_mock_engine"

        try:
            resp = client.chat.completions.create(
                model=m_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=600,
                timeout=t_out
            )

            raw_text = resp.choices[0].message.content
            payload = extract_json_from_llm(raw_text)

            if payload:
                orch = StratumOrchestrator(payload)
                if orch.validate_plan():
                    return orch, m_name

        except Exception as e:
            # Silently catch and fall back to the next tier
            continue

    # Absolute fallback
    return get_mock_segmentation_plan(siruta_code, project_name), "local_mock_engine"


def get_mock_segmentation_plan(siruta_code: int, project_name: str) -> StratumOrchestrator:
    """Generates a valid mock Stereo70 plan for guaranteed offline execution."""
    mock_payload = {
        "project_name": project_name,
        "crs": "EPSG:3844",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [434741.51, 571142.19],
                    [435341.29, 571142.19],
                    [435341.29, 572142.19],
                    [434741.51, 572142.19],
                    [434741.51, 571142.19]
                ]
            ]
        },
        "administrative": {
            "siruta_code": siruta_code,
            "name": "Localitate_Mock",
            "county": "Romania"
        }
    }
    return StratumOrchestrator(mock_payload)
