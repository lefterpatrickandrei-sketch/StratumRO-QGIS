# -*- coding: utf-8 -*-
"""
StratumRO-QGIS: Lightweight Unified Project Validation & Diagnostic Entry Point.
Conforms to MD 1C specification.
Supports:
  --mode fast : Rapid iteration (<0.1s), golden geometry tests, provider status.
  --mode full : Full regression test suite (109 tests), topology & CRS verification.
  --check-providers : Inspects configured AI providers (NVIDIA NIM, Union Alpha, OpenAI, Local).
  --live-union-alpha : Verifies live inference on stealth/union-alpha via OpenRouter.
"""

import sys
import os
import time
import argparse
import unittest
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_golden_tests() -> bool:
    """Executes the 17 deterministic golden geometry tests."""
    print("\n--- 1. GOLDEN GEOMETRY TESTS (17 Typologies & Defects) ---")
    t0 = time.time()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName("stratum_ro.test.test_geometry_golden")
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    elapsed = time.time() - t0
    success = result.wasSuccessful()
    status_str = "PASS" if success else "FAIL"
    print(f"[{elapsed:.3f}s] Golden Geometry: {result.testsRun} tests run, {len(result.failures)} failures, {len(result.errors)} errors -> {status_str}")
    return success


def run_full_regression_tests() -> bool:
    """Executes the full test suite across stratum_ro/test."""
    print("\n--- 2. FULL REGRESSION TEST SUITE (109 Tests) ---")
    t0 = time.time()
    loader = unittest.TestLoader()
    start_dir = str(PROJECT_ROOT / "stratum_ro" / "test")
    suite = loader.discover(start_dir)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    elapsed = time.time() - t0
    success = result.wasSuccessful()
    status_str = "PASS" if success else "FAIL"
    print(f"[{elapsed:.2f}s] Full Regression: {result.testsRun} tests run, {len(result.failures)} failures, {len(result.errors)} errors, {len(result.skipped)} skipped -> {status_str}")
    return success


def check_ai_providers() -> Dict[str, Any]:
    """Inspects status of all registered AI providers without spending tokens."""
    print("\n--- 3. AI PROVIDER STATUS AUDIT ---")
    t0 = time.time()
    from stratum_ro.ai.providers import (
        LocalProvider,
        NvidiaNIMProvider,
        OpenAIProvider,
        OllamaProvider,
        UnionAlphaProvider,
    )

    providers = {
        "local": LocalProvider(),
        "union_alpha": UnionAlphaProvider(),
        "nvidia_nim": NvidiaNIMProvider(),
        "openai": OpenAIProvider(),
        "ollama": OllamaProvider(),
    }

    report = {}
    for name, p in providers.items():
        avail = p.is_available()
        models = p.list_models()
        caps = [c.value for c in p.capabilities()]
        report[name] = {"available": avail, "models": models, "capabilities": caps}
        status_tag = "[AVAILABLE]" if avail else "[NOT CONFIGURED / OFFLINE]"
        print(f"  * {name:<14} {status_tag:<26} models={models[:2]} caps={caps}")

    elapsed = time.time() - t0
    print(f"[{elapsed:.3f}s] Provider inspection complete.")
    return report


def test_live_union_alpha() -> bool:
    """Performs a live connectivity test to Union Alpha via OpenRouter."""
    print("\n--- 4. LIVE UNION ALPHA CONNECTIVITY TEST ---")
    t0 = time.time()
    from stratum_ro.ai.providers.union_alpha_provider import UnionAlphaProvider
    p = UnionAlphaProvider()
    if not p.is_available():
        print("  [ERROR] UnionAlphaProvider is not configured (check UNION_ALPHA_API_KEY / OPENROUTER_API_KEY in .env)")
        return False

    resp = p.generate(
        prompt="Verify live geomatics assistant connectivity for StratumRO Stereo 70.",
        system_prompt="You are an AI geomatics expert. Respond in 1 concise sentence.",
        timeout=25.0
    )
    elapsed = time.time() - t0
    if resp.is_ok():
        print(f"[{elapsed:.2f}s] Live Union Alpha Response ({resp.model_name}):")
        print(f"       \"{resp.content.strip()}\"")
        return True
    else:
        print(f"[{elapsed:.2f}s] Live Union Alpha Failed: {resp.error}")
        return False


def verify_crs_and_topology() -> bool:
    """Deterministic validation of Stereo 70 (EPSG:3844) definitions and core geometry validity."""
    print("\n--- 5. DETERMINISTIC CRS & TOPOLOGY CHECKS ---")
    t0 = time.time()
    from shapely.geometry import Polygon
    from stratum_ro.vectorizer import CadastralVectorizer

    vec = CadastralVectorizer(crs="EPSG:3844")
    if vec.crs != "EPSG:3844":
        print("  [FAIL] Vectorizer CRS is not EPSG:3844!")
        return False

    # Check validity preservation on complex concave polygon
    l_poly = Polygon([(0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10)])
    cleaned = vec.clean_cad_polygon(l_poly)
    if not cleaned.is_valid or cleaned.is_empty:
        print("  [FAIL] Topology check failed on L-shape clean!")
        return False

    elapsed = time.time() - t0
    print(f"[{elapsed:.3f}s] CRS & Topology: EPSG:3844 confirmed, Shapely GEOS validity confirmed.")
    return True


def main():
    parser = argparse.ArgumentParser(description="StratumRO-QGIS Unified Validation & Diagnostic Entry Point")
    parser.add_argument("--mode", "-m", choices=["fast", "full"], default="fast",
                        help="Execution mode: 'fast' (golden tests, <0.1s) or 'full' (all 109 tests, ~10s)")
    parser.add_argument("--check-providers", action="store_true", help="Audit status of AI model providers")
    parser.add_argument("--live-union-alpha", action="store_true", help="Run live inference test on Union Alpha")
    args = parser.parse_args()

    print("=================================================================")
    print(f"  STRATUMRO-QGIS: UNIFIED VALIDATION HARNESS (Mode: {args.mode.upper()})")
    print("=================================================================")

    start_total = time.time()
    all_ok = True

    if args.check_providers:
        check_ai_providers()
        return

    if args.live_union_alpha:
        ok = test_live_union_alpha()
        sys.exit(0 if ok else 1)

    # In fast mode:
    if args.mode == "fast":
        ok_golden = run_golden_tests()
        ok_crs = verify_crs_and_topology()
        check_ai_providers()
        all_ok = ok_golden and ok_crs
    elif args.mode == "full":
        ok_golden = run_golden_tests()
        ok_full = run_full_regression_tests()
        ok_crs = verify_crs_and_topology()
        check_ai_providers()
        all_ok = ok_golden and ok_full and ok_crs

    total_time = time.time() - start_total
    print("\n=================================================================")
    if all_ok:
        print(f"  RESULT: ALL CHECKS PASSED in {total_time:.2f}s (Exit Code: 0)")
    else:
        print(f"  RESULT: VALIDATION FAILED in {total_time:.2f}s (Exit Code: 1)")
    print("=================================================================")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
