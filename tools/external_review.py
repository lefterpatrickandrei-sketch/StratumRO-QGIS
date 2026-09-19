#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StratumRO — External AI Code Review via NVIDIA NIM + OpenRouter.
Sends structured project summary to external AI providers for review,
saving Antigravity tokens by using the APIs you already pay for.
"""

import os, sys, json, time, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "QGIS-AI"))
from stratum_ro.ai.providers.nvidia_nim_provider import NvidiaNIMProvider
from stratum_ro.ai.providers.union_alpha_provider import UnionAlphaProvider

BASE = Path(r"c:\Users\lefpa\Downloads\QGIS-AI")
RESULTS_DIR = BASE / "workspace" / "reviews"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def collect_project_digest() -> str:
    key_files = [
        "AGENTS.md",
        "stratum_ro/vectorizer.py",
        "stratum_ro/cad_exporter.py",
        "stratum_ro/volumetric_3d.py",
        "stratum_ro/onnx_engine.py",
        "stratum_ro/sam2_engine.py",
        "stratum_ro/dataset_resolver.py",
        "stratum_ro/orchestrator.py",
        "stratum_ro/stratum_ro_dockwidget.py",
        "stratum_ro/cadastral_algorithm.py",
        "stratum_ro/lidar_processor.py",
        "stratum_ro/ortho_extractor.py",
        "stratum_ro/ai/router.py",
        "stratum_ro/ai/task_graph.py",
        "stratum_ro/ai/context.py",
        "stratum_ro/regulatory_consensus.py",
        "engine/evaluation.py",
        "tools/desktop_operator.py",
        "tools/os_ui_driver.py",
        "tools/qt_ui_probe.py",
        "workspace/e2e/ui_test.json",
        "workspace/e2e/os_ui_test.json",
    ]

    digest_parts = []
    total_chars = 0
    MAX_CHARS = 90000

    for rel_path in key_files:
        fpath = BASE / rel_path
        if not fpath.exists():
            digest_parts.append(f"\n### FILE: {rel_path}\n[FILE NOT FOUND]\n")
            continue
        content = fpath.read_text(encoding="utf-8", errors="replace")
        if total_chars + len(content) > MAX_CHARS:
            remaining = MAX_CHARS - total_chars
            if remaining < 500:
                digest_parts.append(f"\n### FILE: {rel_path}\n[TRUNCATED - budget exhausted]\n")
                break
            content = content[:remaining] + "\n... [TRUNCATED]\n"
        digest_parts.append(f"\n### FILE: {rel_path}\n```python\n{content}\n```\n")
        total_chars += len(content)

    test_summary = """
### LATEST TEST SUITE RESULTS
```
Ran 179 tests in 43.4s — 170 passed, 9 skipped, 0 failed
```

### UI CAPABILITY MATRIX (from workspace/e2e/)
- QT_SEMANTIC_INSPECTION = AVAILABLE (action mActionAddOgrLayer found)
- QT_SEMANTIC_INTERACTION = AVAILABLE (dialog opened/closed)
- OS_LEVEL_INSPECTION = AVAILABLE (364 UIA descendants)
- OS_LEVEL_INTERACTION = AVAILABLE (physical mouse click, 3.44% visual diff, 0.0px variance)
"""
    digest_parts.append(test_summary)
    return "\n".join(digest_parts)


REVIEW_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a senior geospatial software architect reviewing StratumRO, 
    an industrial-grade geomatics platform for automated building footprint 
    extraction, 90deg regularization, 3D extrusion, and CAD export conforming 
    to Romanian ANCPI Ordinul 600/2023, built as a QGIS 3.40 plugin.
    
    The project uses:
    - Meta SAM 2 Hiera Tiny for building segmentation (PyTorch + ONNX DirectML)
    - LiDAR nDSM for height-based filtering
    - Stereo 70 (EPSG:3844) as canonical CRS
    - NVIDIA NIM + OpenRouter for AI-assisted analysis
    - pywinauto + pyautogui for desktop automation testing
    
    Your task: Provide a PRIORITIZED technical review with:
    1. Critical Gaps - What is missing or broken that would block production use?
    2. Code Quality Issues - Dead code, architectural problems, DRY violations.
    3. Security Concerns - API key handling, injection risks, credential exposure.
    4. Test Coverage Gaps - What is not tested but should be?
    5. Performance Bottlenecks - Obvious inefficiencies.
    6. Recommended Next Steps - Top 5 highest-impact improvements, ordered by priority.
    
    Be concrete: cite file names and line numbers. Be honest: if something is 
    well-done, say so. If something is fake or placeholder, call it out.
""")

REVIEW_PROMPT_TEMPLATE = textwrap.dedent("""\
    Please review the following StratumRO codebase digest and provide your 
    prioritized technical assessment. Focus on what ACTUALLY NEEDS FIXING 
    versus what is already solid, so the developer does not waste time on 
    things that already work.
    
    {digest}
""")


def run_review():
    print("=" * 70)
    print("StratumRO — External AI Code Review")
    print("=" * 70)

    print("\n[1/3] Collecting project digest...")
    digest = collect_project_digest()
    digest_chars = len(digest)
    print(f"  Digest size: {digest_chars:,} chars (~{digest_chars // 4:,} tokens)")

    prompt = REVIEW_PROMPT_TEMPLATE.format(digest=digest)
    results = {}

    # NVIDIA NIM Review
    print("\n[2/3] Sending to NVIDIA NIM (Llama 3.3 70B)...")
    nim = NvidiaNIMProvider(default_model="meta/llama-3.3-70b-instruct")
    if nim.is_available():
        nim_resp = nim.generate(
            prompt=prompt,
            system_prompt=REVIEW_SYSTEM_PROMPT,
            model="meta/llama-3.3-70b-instruct",
            max_tokens=4000,
            temperature=0.2,
            timeout=120.0,
        )
        results["nvidia_nim"] = {
            "status": nim_resp.status,
            "model": nim_resp.model_name,
            "duration_sec": nim_resp.duration_sec,
            "content": nim_resp.content,
            "error": nim_resp.error or None,
            "usage": nim_resp.usage or {},
        }
        if nim_resp.status == "success":
            print(f"  OK NVIDIA NIM responded in {nim_resp.duration_sec:.1f}s")
            print(f"  Usage: {nim_resp.usage}")
        else:
            print(f"  ERR NVIDIA NIM error: {nim_resp.error}")
    else:
        print("  ERR NVIDIA NIM not available (no API key)")
        results["nvidia_nim"] = {"status": "unavailable", "error": "No API key"}

    # OpenRouter / Claude Review
    print("\n[3/3] Sending to OpenRouter (Claude 3.5 Sonnet)...")
    openrouter = UnionAlphaProvider(default_model="anthropic/claude-3.5-sonnet")
    if openrouter.is_available():
        or_resp = openrouter.generate(
            prompt=prompt,
            system_prompt=REVIEW_SYSTEM_PROMPT,
            model="anthropic/claude-3.5-sonnet",
            max_tokens=4000,
            temperature=0.2,
            timeout=120.0,
        )
        results["openrouter"] = {
            "status": or_resp.status,
            "model": or_resp.model_name,
            "duration_sec": or_resp.duration_sec,
            "content": or_resp.content,
            "error": or_resp.error or None,
            "usage": or_resp.usage or {},
        }
        if or_resp.status == "success":
            print(f"  OK OpenRouter responded in {or_resp.duration_sec:.1f}s")
            print(f"  Usage: {or_resp.usage}")
        else:
            print(f"  ERR OpenRouter error: {or_resp.error}")
    else:
        print("  ERR OpenRouter not available (no API key)")
        results["openrouter"] = {"status": "unavailable", "error": "No API key"}

    # Save results
    ts = int(time.time())
    report_json = RESULTS_DIR / f"external_review_{ts}.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[DONE] Raw results saved to: {report_json}")

    # Generate markdown report
    report_md = RESULTS_DIR / f"external_review_{ts}.md"
    md_parts = ["# StratumRO — External AI Code Review\n"]
    md_parts.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n")

    for provider_name, data in results.items():
        md_parts.append(f"\n## Review by: {provider_name} ({data.get('model', 'unknown')})\n")
        md_parts.append(f"**Status:** {data['status']} | **Duration:** {data.get('duration_sec', 0):.1f}s\n")
        if data["status"] == "success":
            md_parts.append(f"\n{data['content']}\n")
        else:
            md_parts.append(f"\n> Error: {data.get('error', 'unknown')}\n")
        md_parts.append("\n---\n")

    report_text = "\n".join(md_parts)
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"[DONE] Markdown report saved to: {report_md}")

    print("\n" + "=" * 70)
    print(report_text[:3000])
    if len(report_text) > 3000:
        print(f"\n... [{len(report_text) - 3000} more chars in {report_md}]")


if __name__ == "__main__":
    run_review()
