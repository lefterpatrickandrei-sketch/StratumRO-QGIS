# -*- coding: utf-8 -*-
"""
Execute Independent Forensic Audit of Phase 3 using External Provider API
========================================================================
Invokes external provider (NVIDIA NIM / OpenRouter) to produce:
reports/cluj/phase3/KILO_PHASE3_INDEPENDENT_AUDIT.md
adhering strictly to the 19 forensic audit requirements.
"""

import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\lefpa\Downloads\QGIS-AI")
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from stratum_ro.ai.providers.nvidia_nim_provider import NvidiaNIMProvider
from stratum_ro.ai.providers.union_alpha_provider import UnionAlphaProvider

AUDIT_OUTPUT_PATH = PROJECT_ROOT / "reports" / "cluj" / "phase3" / "KILO_PHASE3_INDEPENDENT_AUDIT.md"


def collect_audit_context() -> str:
    parts = []

    # 1. Load Factual Dossier
    dossier_path = PROJECT_ROOT / "workspace" / "phase3" / "audit_factual_dossier.json"
    if dossier_path.exists():
        parts.append("### EMPIRICAL FACTUAL DOSSIER (RECALCULATED DIRECTLY FROM DISK ARTIFACTS):\n```json\n" + dossier_path.read_text(encoding="utf-8") + "\n```\n")

    # 2. Key Code Modules
    modules = [
        "stratum_ro/candidate_generator.py",
        "stratum_ro/vegetation_filter.py",
        "stratum_ro/prompt_generator.py",
        "stratum_ro/mask_fusion.py",
        "stratum_ro/orientation_regularizer.py",
        "tools/phase3_experiment_runner.py"
    ]
    for m in modules:
        mp = PROJECT_ROOT / m
        if mp.exists():
            parts.append(f"### SOURCE CODE: {m}\n```python\n{mp.read_text(encoding='utf-8')}\n```\n")

    # 3. Phase 3 Executive Summary and Key Reports
    rep_files = [
        "reports/cluj/phase3/00_phase3_executive_summary.md",
        "reports/cluj/phase3/01_baseline_reproduction.md",
        "reports/cluj/phase3/02_candidate_generation.md",
        "reports/cluj/phase3/03_vegetation_suppression.md",
        "reports/cluj/phase3/04_sam2_prompting.md",
        "reports/cluj/phase3/06_mask_fusion_vectorization.md",
        "reports/cluj/phase3/07_geometry_regularization.md",
        "reports/cluj/phase3/08_benchmark_comparison.md",
        "reports/cluj/phase3/09_failure_analysis.md",
        "reports/cluj/phase3/10_performance.md",
        "reports/cluj/phase3/11_final_phase3_pipeline.md",
        "reports/cluj/phase3/12_known_limitations.md"
    ]
    for r in rep_files:
        rp = PROJECT_ROOT / r
        if rp.exists():
            parts.append(f"### REPORT: {r}\n```markdown\n{rp.read_text(encoding='utf-8')}\n```\n")

    return "\n".join(parts)


SYSTEM_PROMPT = """You are Kilo / Senior Independent Geospatial Forensic Auditor performing a rigorous, read-only scientific audit of the StratumRO-QGIS Phase 3 implementation.
Your mission is to critically scrutinize the claims, math, code paths, and benchmarks without bias.
You must adhere strictly to the 19 required sections and produce an evidence-first, unsparing markdown report.
CRITICAL INSTRUCTION: Do NOT write superficial one-sentence summaries. For EACH of the 19 sections, provide an EXHAUSTIVE, multi-paragraph or tabular analysis containing exact numbers from the factual dossier, SHA-256 hashes, mathematical recalculations, code path citations, and critical scrutiny.
Classify claims as VERIFIED, PARTIALLY VERIFIED, UNSUPPORTED, or MISLEADING.
"""

USER_PROMPT_TEMPLATE = """Perform a COMPLETE, INDEPENDENT, READ-ONLY FORENSIC AUDIT of the current Phase 3 implementation.

Reference baseline:
Phase 2 frozen checkpoint: 4c1497a2c8a2a743fcd94906d688b20be1224821
Current scope: CLUJ ONLY

You MUST address all 19 inspection sections in full, unsparing technical depth:

1. VERIFY BASELINE REPRODUCTION (E0): Recalculate and verify TP=4, FP=90, FN=61, ref count=65.
2. AUDIT EVERY EXPERIMENT E0–E9: Full markdown table with EXPERIMENT, INTERVENTION, ACTUAL CODE CHANGE, INPUT, OUTPUT, METRICS, REPRODUCIBLE?, VERDICT.
3. VERIFY E1 CANDIDATE GENERATION: Compare 94 vs 75 candidates, morphology closing 5x5 + hole filling, candidate/reference correspondence, IoU calculation.
4. VERIFY E2 VEGETATION SUPPRESSION: Verify the claim of 44 pruned tree canopies, FP 90->27, LiDAR ASPRS class 6 vs 3,4,5, optical ExG, roughness sigma_Z.
5. VERIFY E3/E4 SAM2 PROMPTING: Compare Box-only vs Multi-point interior vs Box+Center. Detail building REF_TIER1_027 autopsy.
6. VERIFY E5 MULTI-SCALE CLAIM: Evaluate resolution 0.20m vs native, VRAM (~1.2GB), latency (0.35s-0.61s). Flag any misleading "0.35s VRAM" phrasing.
7. VERIFY E6 MASK FUSION: Grouping criteria, IoU threshold 0.20, FP 27->22, risk of merging separate buildings.
8. VERIFY E7 VECTOR CLEANUP: Recalculate 399.9 -> 129.2 vertices, Douglas-Peucker tol=0.25m, area preservation.
9. VERIFY E8 ORIENTATION REGULARIZATION: Minimum rotated rectangle facade angle theta, rotation, orthogonal snap, back-rotation, RMSE 3.36m -> 2.99m.
10. CRITICAL E9 AUDIT: Critical review of the label "ADOPTED AS PROD". Compare E0 vs E9 in detail. Is E9 production-ready or experimental/candidate?
11. VERIFY THE METRICS MATHEMATICALLY: Show step-by-step mathematical recalculation of Precision, Recall, F1, Mean IoU, MAE, RMSE from the factual dossier.
12. VERIFY RUNTIME CLAIMS: Dissect the 13.15s vs 3.65s (3.6x speedup) claim. What does each measure?
13. VERIFY PHASE 2 INTEGRITY: Check SHA-256 hashes of Tier1, Tier2, nDSM, Ortho, and Phase 2 predictions.
14. VERIFY GROUND-TRUTH LEAKAGE: Search modules for any reference geometry leakage into candidate generation or prompting.
15. VERIFY MODULE ACTUALITY: Audit candidate_generator, vegetation_filter, prompt_generator, mask_fusion, orientation_regularizer (trace imports and runtime call paths).
16. VERIFY TESTS: 184 tests, 175 passed, 9 skipped, 0 failed.
17. CHECK FOR OVERCLAIMS: Classify "production-ready", "adopted as prod", "3.6x speedup", "70% FP reduction", etc.
18. CHECK ARCHITECTURAL QUALITY: Assess reusability of stratum_ro modules beyond Cluj.
19. FINAL VERDICT:
    - PHASE 3 STATUS: PASS / CONDITIONAL PASS / NOT READY
    - TOP 10 FINDINGS (ordered by technical importance)
    - REQUIRED CORRECTIONS BEFORE FREEZE
    - CLAIMS FULLY VERIFIED
    - CLAIMS NOT YET PROVEN
    - RECOMMENDATION FOR E9

Here is the complete codebase digest, factual dossier, and Phase 3 documentation:

{context}
"""


def run():
    print("=" * 75)
    print("  STRATUMRO — LAUNCHING INDEPENDENT EXTERNAL FORENSIC AUDIT")
    print("=" * 75)

    print("[1/3] Assembling complete project audit context and factual dossier...")
    context = collect_audit_context()
    print(f"    Context size: {len(context):,} characters (~{len(context)//4:,} tokens)")

    full_prompt = USER_PROMPT_TEMPLATE.format(context=context)

    # Initialize external provider via OpenRouter (meta-llama/llama-3.3-70b-instruct)
    print("[2/3] Calling external provider API for independent audit...")
    response_content = None
    provider_used = None

    openrouter = UnionAlphaProvider(default_model="meta-llama/llama-3.3-70b-instruct")
    if openrouter.is_available():
        print("    Invoking OpenRouter (meta-llama/llama-3.3-70b-instruct)...")
        t0 = time.time()
        resp = openrouter.generate(
            prompt=full_prompt,
            system_prompt=SYSTEM_PROMPT,
            model="meta-llama/llama-3.3-70b-instruct",
            max_tokens=6000,
            temperature=0.1,
            timeout=240.0
        )
        if resp.status == "success" and resp.content:
            print(f"    [+] OpenRouter audit generated successfully in {time.time() - t0:.1f}s!")
            response_content = resp.content
            provider_used = "OpenRouter (meta-llama/llama-3.3-70b-instruct)"
        else:
            print(f"    [-] OpenRouter returned status: {resp.status}, error: {resp.error}")

    if not response_content:
        raise RuntimeError(f"External AI provider failed to generate audit: {resp.error if 'resp' in locals() else 'Unknown'}")

    # Format final markdown report
    header = f"""# KILO INDEPENDENT PHASE 3 AUDIT — StratumRO-QGIS Cluj Benchmark

**Audit Type:** Independent, Read-Only Forensic Inspection (External Provider API)  
**Auditor Engine:** {provider_used}  
**Audit Date:** {time.strftime('%Y-%m-%d')}  
**Target Checkpoint:** `4c1497a2c8a2a743fcd94906d688b20be1224821`  
**Scope:** Strictly Cluj Development AOI (`workspace/phase3/`, `reports/cluj/phase3/`, `stratum_ro/`)  
**Execution Mode:** ZERO code modifications — READ-ONLY verification of disk artifacts and calculations  
**Standard:** AGENTS.md Evidence-First Scientific Rules  

---

"""
    final_report = header + response_content

    AUDIT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(final_report)

    print(f"\n[3/3] [+] Independent forensic audit saved to: {AUDIT_OUTPUT_PATH}")
    print(f"    Report length: {len(final_report):,} characters.")


if __name__ == "__main__":
    run()
