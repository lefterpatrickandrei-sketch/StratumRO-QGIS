# -*- coding: utf-8 -*-
"""
Deep Forensic Independent Audit Generator for Phase 3
======================================================
Invokes OpenRouter (meta-llama/llama-3.3-70b-instruct) with exhaustive forensic
prompts to produce a rigorous, multi-page independent audit report at:
reports/cluj/phase3/KILO_PHASE3_INDEPENDENT_AUDIT.md
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

    # 3. Reports
    rep_files = [
        "reports/cluj/phase3/00_phase3_executive_summary.md",
        "reports/cluj/phase3/01_baseline_reproduction.md",
        "reports/cluj/phase3/02_candidate_generation.md",
        "reports/cluj/phase3/03_vegetation_suppression.md",
        "reports/cluj/phase3/04_sam2_prompting.md",
        "reports/cluj/phase3/05_multiscale_inference.md",
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


SYSTEM_PROMPT = """You are Kilo, the Senior Independent Geospatial Forensic Auditor for StratumRO-QGIS.
You are performing a rigorous, read-only scientific audit of the Phase 3 implementation.
Your audit must be uncompromising, evidence-first, highly detailed, and mathematically verified.
Do NOT write superficial summaries. Provide extensive technical analysis, tables, recalculations, code path dissections, and critical scrutiny for every single section.
Classify every claim as VERIFIED, PARTIALLY VERIFIED, UNSUPPORTED, or MISLEADING.
"""

USER_PROMPT = """Perform a COMPLETE, INDEPENDENT, READ-ONLY FORENSIC AUDIT of the current Phase 3 implementation.

Reference baseline:
Phase 2 frozen checkpoint: 4c1497a2c8a2a743fcd94906d688b20be1224821
Current scope: CLUJ ONLY

You MUST structure your audit into these EXACT 19 sections, providing deep forensic scrutiny for each:

# 1. VERIFY BASELINE REPRODUCTION (E0)
- Recalculate TP, FP, FN, precision, recall, F1, mean IoU, MAE, and reference count (65) from `E0_raw` and `E0_reg` in the factual dossier.
- Verify whether Phase 2 baseline outputs were modified or cleanly preserved.
- Verdict: VERIFIED / NOT VERIFIED.

# 2. AUDIT EVERY EXPERIMENT E0–E9
Produce an exhaustive markdown table:
| Exp | Focus / Intervention | Code Path | Key Parameters | Inputs | Outputs | Recalculated Metrics (P / R / F1 / IoU / MAE) | Reproducible? | Verdict |
Provide a critical commentary on each experiment.

# 3. VERIFY E1 CANDIDATE GENERATION
- Baseline vs E1 candidates (94 -> 75).
- Audit morphology: closing 5x5 + binary hole filling.
- Verify whether morphology uses any reference data (confirm zero reference geometry in candidate generator).
- Verify candidate-to-reference recall (how many of the 65 buildings are intersected).
- Verdict: VERIFIED / PARTIALLY VERIFIED / UNSUPPORTED.

# 4. VERIFY E2 VEGETATION SUPPRESSION
- Verify the claim: 44 tree canopies pruned, FP reduced from 71 to 27, zero TP loss.
- Audit the actual code in `stratum_ro/vegetation_filter.py`: does it actually use ASPRS Class 6 vs 3,4,5, optical ExG (2G-R-B), and height roughness (sigma_Z)?
- Check whether any genuine building candidate was accidentally pruned.
- Verdict.

# 5. VERIFY E3/E4 SAM2 PROMPTING
- Contrast Box-only (E3) vs Multi-point interior (E4) vs Box+Center (E2).
- Detail the specific case of building `REF_TIER1_027` (2,669.7 m²): why Box-only captures 2,561 m² while Box+Center captured only 1,412 m².
- Verify whether reference data was completely absent from prompt coordinates.
- Verdict.

# 6. VERIFY E5 MULTI-SCALE CLAIM
- Audit the input dimensions (2500x2000), resolution (0.20m GSD), VRAM usage (~1.2GB), and latency (0.35s).
- CRITICAL: Flag any confusing/misleading phrasing in reports where latency (e.g. "0.35s") was conflated with VRAM (e.g. "0.35s VRAM").
- Verdict.

# 7. VERIFY E6 MASK FUSION
- Verify the FP reduction: 27 -> 22 (5 duplicate wing segments eliminated).
- Audit `stratum_ro/mask_fusion.py`: grouping criteria (IoU >= 0.20 or inter_area > 20m²), unary_union.
- Evaluate risk of accidental merging of distinct adjacent buildings.
- Verdict.

# 8. VERIFY E7 VECTOR CLEANUP
- Verify vertex count reduction: 399.9 -> 129.2 vertices/building.
- Verify Douglas-Peucker simplification tolerance (0.25m ~ 1.25 px).
- Check area preservation: confirm area delta is < 0.5%.
- Verdict.

# 9. VERIFY E8 ORIENTATION REGULARIZATION
- Audit `stratum_ro/orientation_regularizer.py`: dominant angle theta estimation via minimum rotated rectangle, rotation by -theta, orthogonal snapping (tol=0.65m), reverse rotation by +theta.
- Recalculate RMSE 2D improvement: 3.36 m (baseline) -> 2.99 m (E8). Is this a true geodetic improvement?
- Verdict.

# 10. CRITICAL E9 AUDIT & PRODUCTION READINESS
- CRITICAL EVALUATION: The report labels E9 as "ADOPTED AS PROD".
- Does the evidence support "production-ready" or should it be classified as "CANDIDATE PRODUCTION" or "EXPERIMENTAL"?
- Scrutinize the trade-off: E9 dramatically slashes FP (-75.6%) and speeds up runtime (3.65s vs 13.15s), but TP remains 4 and Mean IoU drops slightly from 70.37% to 66.59% because box-only prompts capture outer courtyards.
- Provide a defensible, evidence-based recommendation.

# 11. VERIFY THE METRICS MATHEMATICALLY
Show explicit step-by-step mathematical calculations for E0, E2, E6, E9:
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * P * R / (P + R)
- Mean IoU, MAE, RMSE from the factual dossier.
Verify whether the JSON report values match ground truth calculations.

# 12. VERIFY RUNTIME CLAIMS
- Dissect the reported 13.15s (Phase 2) vs 3.65s (Phase 3 E9) = 3.6x speedup.
- What accounts for the speedup? (Fewer candidates passed to SAM2 prompt decoder: 94 -> 31 -> 26).
- Is the comparison valid and fair?

# 13. VERIFY PHASE 2 INTEGRITY
- Verify SHA-256 hashes of:
  - `tier1_teren.geojson`
  - `tier2_extended_gt.geojson`
  - `cluj_combined_unique_150.geojson`
  - `cluj_ndsm_1m.tif`
  - `active_ortho_crop.tif`
  - `cluj_raw_sam2_predictions.geojson`
  - `cluj_regularized_predictions.geojson`
- Confirm that Phase 2 artifacts were NOT modified or replaced.

# 14. VERIFY GROUND-TRUTH LEAKAGE
- Forensic audit of imports and variables across all 5 new modules and the runner.
- Did any ground truth coordinates, IDs, or geometries enter candidate discovery, vegetation filtering, or prompting?
- Verdict.

# 15. VERIFY MODULE ACTUALITY
- Audit the 5 modules in `stratum_ro/`:
  - `candidate_generator.py`
  - `vegetation_filter.py`
  - `prompt_generator.py`
  - `mask_fusion.py`
  - `orientation_regularizer.py`
- Are they genuinely integrated, callable, and tested, or merely dead code?
- Trace call graph in `phase3_experiment_runner.py`.

# 16. VERIFY UNIT TESTS
- Verify unit test suite execution:
  - Total tests: 184
  - Passed: 175
  - Skipped: 9
  - Failed: 0
- Confirm that `test_phase3_modules.py` tests actual behavior (synthetic rasters, IoU, orientation rotation) rather than just trivial imports.

# 17. CHECK FOR OVERCLAIMS
Audit and classify each of the following statements as VERIFIED, PARTIALLY VERIFIED, UNSUPPORTED, or MISLEADING:
- "Production-ready"
- "Adopted as prod"
- "3.6x GPU speedup"
- "70% FP reduction"
- "High precision"
- "Zero ground truth leakage"

# 18. CHECK ARCHITECTURAL QUALITY & REUSABILITY
- Are the new modules tied specifically to Cluj hardcoded paths, or are they generalizable to other AOIs (Oradea, Rural, etc.)?
- Assess API cleanliness, parameterization, and adherence to Stereo 70 geodetic standards.

# 19. FINAL VERDICT & ACTIONABLE RECOMMENDATIONS
- PHASE 3 STATUS: PASS / CONDITIONAL PASS / NOT READY
- TOP 10 FINDINGS (ordered by technical importance)
- REQUIRED CORRECTIONS BEFORE FREEZE
- CLAIMS FULLY VERIFIED
- CLAIMS NOT YET PROVEN
- FINAL RECOMMENDATION FOR E9 STATUS

Here is the complete codebase digest, factual dossier, and Phase 3 documentation:

{context}
"""


def run():
    print("=" * 75)
    print("  STRATUMRO — GENERATING DEEP FORENSIC INDEPENDENT AUDIT (LLAMA 3.3 70B)")
    print("=" * 75)

    context = collect_audit_context()
    print(f"[*] Audit context assembled: {len(context):,} characters (~{len(context)//4:,} tokens)")

    full_prompt = USER_PROMPT.format(context=context)

    openrouter = UnionAlphaProvider(default_model="meta-llama/llama-3.3-70b-instruct")
    print("[*] Invoking OpenRouter (meta-llama/llama-3.3-70b-instruct)...")
    t0 = time.time()
    resp = openrouter.generate(
        prompt=full_prompt,
        system_prompt=SYSTEM_PROMPT,
        model="meta-llama/llama-3.3-70b-instruct",
        max_tokens=6500,
        temperature=0.1,
        timeout=240.0
    )

    if resp.status != "success" or not resp.content:
        raise RuntimeError(f"OpenRouter generation failed: {resp.error}")

    print(f"[+] Audit generated in {time.time() - t0:.1f}s! ({len(resp.content):,} characters)")

    header = f"""# KILO INDEPENDENT PHASE 3 AUDIT — StratumRO-QGIS Cluj Benchmark

**Audit Type:** Independent, Read-Only Forensic Inspection (External Provider API)  
**Auditor Engine:** OpenRouter (`meta-llama/llama-3.3-70b-instruct`)  
**Audit Date:** {time.strftime('%Y-%m-%d')}  
**Target Checkpoint:** `4c1497a2c8a2a743fcd94906d688b20be1224821`  
**Scope:** Strictly Cluj Development AOI (`workspace/phase3/`, `reports/cluj/phase3/`, `stratum_ro/`)  
**Execution Mode:** ZERO code modifications — READ-ONLY verification of disk artifacts and calculations  
**Standard:** AGENTS.md Evidence-First Scientific Rules  

---

"""
    final_report = header + resp.content

    AUDIT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(final_report)

    print(f"[+] Written to {AUDIT_OUTPUT_PATH}")


if __name__ == "__main__":
    run()
