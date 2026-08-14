#!/usr/bin/env python3
"""
tools/test_llm_orchestrator.py

- Conectează la NVIDIA NIM API (base_url=https://integrate.api.nvidia.com/v1)
  folosind pachetul openai (Python OpenAI client).
- Listează modelele disponibile (client.models.list()) înainte de a hardcoda ID-uri.
- Definește un tool (OpenAI function-calling) numit `process_segmentation`
  cu schema IDENTICĂ cu payload-ul din docs/architecture.md pentru POST /api/v1/segmentation/process.
- Rulează 3 prompturi de test pe fiecare model din MODELS_TO_TEST (sau primele modele listate
  dacă MODELS_TO_TEST nu e definit), salvează rezultatele într-un fișier JSON.
- Nu modifică nimic din stratum_ro/ și funcționează offline (fără backend live).
"""

import os
import json
import time
from datetime import datetime
from typing import Any, Dict, List

# Import OpenAI Python client
# This script assumes the "openai" package that exposes OpenAI client class
# (e.g., from openai import OpenAI; client = OpenAI()) is installed.
from openai import OpenAI
from openai.error import OpenAIError

# Configuration
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_API_KEY = os.environ.get("NVIDIA_API_KEY")
# Optional env var to override which models to test: comma-separated model IDs/names
MODELS_TO_TEST_ENV = os.environ.get("MODELS_TO_TEST")  # e.g. "model-x,model-y"
# Output file
OUT_DIR = "tools/llm_test_results"
os.makedirs(OUT_DIR, exist_ok=True)


def init_client():
    if not NIM_API_KEY:
        raise RuntimeError("Environment variable NVIDIA_API_KEY is not set.")
    # Ensure the OpenAI client uses NVIDIA base and key
    # Use environment variables so client.models.list() uses them
    os.environ["OPENAI_API_BASE"] = NIM_BASE_URL
    os.environ["OPENAI_API_KEY"] = NIM_API_KEY
    # Create client
    client = OpenAI()
    return client


def build_process_segmentation_schema() -> Dict[str, Any]:
    """
    Build JSON Schema for the function parameters IDENTIC with the request body shown
    in docs/architecture.md for POST /api/v1/segmentation/process.
    """
    schema = {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "crs": {"type": "string"},
            "crs_vertical": {"type": "string"},
            "crs_compound": {"type": "string"},
            "supported_crs": {
                "type": "array",
                "items": {"type": "string"},
            },
            "dimension": {"type": "string"},
            "aoi_selection_mode": {"type": "string"},
            "geometry": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["Polygon"]},
                    "coordinates": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                            },
                        },
                    },
                },
                "required": ["type", "coordinates"],
            },
            "administrative": {
                "type": "object",
                "properties": {
                    "siruta_code": {"type": "integer"},
                    "level": {"type": "string"},
                    "name": {"type": "string"},
                    "county": {"type": "string"},
                },
                "required": ["siruta_code", "level", "name", "county"],
            },
            "parameters": {
                "type": "object",
                "properties": {
                    "model_version": {"type": "string"},
                    "confidence_threshold": {"type": "number"},
                },
                "required": ["model_version", "confidence_threshold"],
            },
        },
        "required": [
            "project_name",
            "crs",
            "crs_vertical",
            "crs_compound",
            "supported_crs",
            "dimension",
            "aoi_selection_mode",
            "geometry",
            "administrative",
            "parameters",
        ],
    }
    return schema


def prepare_test_prompts() -> List[Dict[str, Any]]:
    """
    Returns three test prompts:
      1) with known SIRUTA
      2) without administrative code (to check hallucination)
      3) with another SIRUTA
    Each prompt requests the model to call the process_segmentation function with the payload.
    """
    base_payload = {
        "project_name": "Segmentare_Nationala_StratumRO",
        "crs": "EPSG:3844",
        "crs_vertical": "EPSG:5781",
        "crs_compound": "EPSG:3844+5781",
        "supported_crs": ["EPSG:3844", "EPSG:31700"],
        "dimension": "3D",
        "aoi_selection_mode": "hybrid",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [125000.00, 245000.00],
                    [880000.00, 245000.00],
                    [880000.00, 770000.00],
                    [125000.00, 770000.00],
                    [125000.00, 245000.00],
                ]
            ],
        },
        "parameters": {"model_version": "v1.0-default", "confidence_threshold": 0.5},
    }

    prompts = []

    # 1) Known SIRUTA (example from docs: 26573)
    p1 = dict(base_payload)
    p1["administrative"] = {
        "siruta_code": 26573,
        "level": "uat",
        "name": "Oradea",
        "county": "Bihor",
    }
    prompts.append({"name": "known_siruta", "payload": p1, "note": "Has known SIRUTA 26573"})

    # 2) Missing administrative code (to see if model invents it)
    p2 = dict(base_payload)
    # intentionally include administrative without siruta_code
    p2["administrative"] = {"level": "uat", "name": "UnknownTown", "county": "UnknownCounty"}
    prompts.append({"name": "missing_siruta", "payload": p2, "note": "No siruta_code provided"})

    # 3) Another SIRUTA
    p3 = dict(base_payload)
    p3["administrative"] = {
        "siruta_code": 12345,
        "level": "uat",
        "name": "AltOras",
        "county": "AltJudet",
    }
    prompts.append({"name": "other_siruta", "payload": p3, "note": "Different SIRUTA 12345"})

    return prompts


def run_tests(client: OpenAI, models_to_test: List[str], function_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    from openai import OpenAIError

    results = []
    prompts = prepare_test_prompts()

    functions_def = [
        {
            "name": "process_segmentation",
            "description": "Process segmentation task - payload must match API contract POST /api/v1/segmentation/process",
            "parameters": function_schema,
        }
    ]

    for model in models_to_test:
        for test in prompts:
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model": model,
                "test_name": test["name"],
                "note": test.get("note"),
                "prompt_payload": test["payload"],
                "response": None,
                "error": None,
            }
            try:
                # Use chat completions with function calling
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Te rog completează apelul funcției `process_segmentation` "
                                "cu schema exactă dată. Nu inventa câmpuri suplimentare. "
                                "Folosește datele din payload-ul furnizat."
                            ),
                        },
                        {"role": "system", "content": "You are a strict JSON-function caller that must return arguments matching the schema."},
                        {"role": "user", "content": json.dumps(test["payload"])},
                    ],
                    functions=functions_def,
                    function_call={"name": "process_segmentation"},  # force call
                    temperature=0.0,
                    max_tokens=1024,
                )
                # Record the whole response object
                record["response"] = resp.model_dump() if hasattr(resp, "model_dump") else resp.__dict__
            except OpenAIError as e:
                record["error"] = {"type": type(e).__name__, "message": str(e)}
            except Exception as e:
                record["error"] = {"type": type(e).__name__, "message": str(e)}
            results.append(record)
            # small delay to be polite
            time.sleep(0.5)

    return results


def choose_models(client: OpenAI) -> List[str]:
    """
    List models live, print them out, and choose models to test.
    Behavior:
      - If MODELS_TO_TEST env var is set, use those IDs (split by comma).
      - Otherwise, take up to first 3 models from client.models.list() response.
    """
    print("Listing available models from NVIDIA NIM API...")
    models_list = []
    try:
        r = client.models.list()
        # r.data is expected to be a list of model entries
        raw_models = getattr(r, "data", None) or r.get("data", [])
        for m in raw_models:
            # model id could be m.id or m.get("id")
            mid = getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else None)
            if mid:
                models_list.append(mid)
    except Exception as e:
        print("Error listing models:", e)
        # fallback: empty list
        models_list = []

    if MODELS_TO_TEST_ENV:
        picks = [m.strip() for m in MODELS_TO_TEST_ENV.split(",") if m.strip()]
        print("Using MODELS_TO_TEST from env:", picks)
        return picks

    # default: first up to 3 models from listing
    if models_list:
        picks = models_list[:3]
        print("Selected models to test (from live list):", picks)
        return picks

    raise RuntimeError("No models available to test and MODELS_TO_TEST not set.")


def save_results(results: List[Dict[str, Any]]):
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(OUT_DIR, f"llm_orchestrator_results_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Saved results to", out_path)


def main():
    client = init_client()
    # Build tool schema exactly as in docs/architecture.md
    function_schema = build_process_segmentation_schema()

    # Print the schema for transparency
    print("process_segmentation schema:")
    print(json.dumps(function_schema, indent=2, ensure_ascii=False))

    # List models and pick
    models_to_test = choose_models(client)

    # Run tests
    try:
        results = run_tests(client, models_to_test, function_schema)
        save_results(results)
    except Exception as e:
        print("Fatal error during tests:", repr(e))
        raise


if __name__ == "__main__":
    main()
