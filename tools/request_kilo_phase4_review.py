# -*- coding: utf-8 -*-
"""
Submit Phase 3 Reconciliation & Phase 4 Architectural Blueprint to Kilo
(via OpenRouter API: meta-llama/llama-3.3-70b-instruct)
Strictly adheres to Section 37 Kilo Review Template in the Master Execution Protocol.
"""

import os
import sys
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

MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"
OUTPUT_PATH = PROJECT_ROOT / "reports" / "cluj" / "phase3" / "KILO_PHASE4_ARCHITECTURE_REVIEW.md"

SYSTEM_PROMPT = """You are Kilo, Senior Adversarial Reviewer for the StratumRO-QGIS GeoAI Platform.
Your duty is to challenge architectural assumptions, identify contradictions, enforce the AGENTS.md 8 scientific rules,
and evaluate whether the proposed Phase 4 Adaptive GeoAI Core and simulation architecture are sound, realistic, and non-bloated.
Be direct, skeptical, evidence-first, and constructive."""

def run():
    print("=" * 75)
    print("  STRATUMRO — KILO ADVERSARIAL ARCHITECTURE REVIEW (OPENROUTER)")
    print("=" * 75)

    reconciliation_text = (PROJECT_ROOT / "reports" / "cluj" / "phase3" / "PHASE3_RECONCILIATION.md").read_text(encoding="utf-8")
    architecture_map = (PROJECT_ROOT / "docs" / "architecture" / "ADAPTIVE_GEOAI_CORE_MAP.md").read_text(encoding="utf-8")

    submission = f"""# SUBMISSION TO KILO FOR ADVERSARIAL MILESTONE REVIEW

### GOAL:
1. Reconcile and freeze Phase 3 algorithmic optimization on Cluj benchmark.
2. Review Phase 4 blueprint for Adaptive GeoAI Core (TaskSpec, WorkflowModeRegistry, Common Geospatial Model, Multi-Level Validation, and Simulation-Ready Architecture).

### CHANGED FILES (PHASE 3 TO DATE):
- `stratum_ro/candidate_generator.py` (Morphological closing 5x5 + hole fill)
- `stratum_ro/vegetation_filter.py` (ExG + LiDAR Class 6 vs 3-5 + height roughness)
- `stratum_ro/prompt_generator.py` (Box + multipoint grid)
- `stratum_ro/mask_fusion.py` (Adjacency graph unary_union)
- `stratum_ro/orientation_regularizer.py` (Principal facade rotation + 90° snapping)
- `stratum_ro/test/test_phase3_modules.py` (5 behavioral unit tests)
- `reports/cluj/phase3/PHASE3_RECONCILIATION.md`
- `docs/architecture/ADAPTIVE_GEOAI_CORE_MAP.md`

### ARCHITECTURAL DECISIONS:
- Reject unconditional "production" label for E9; designate as "Candidate Production (Assisted Pre-Cadastre)" due to Recall (6.15%).
- Acknowledge E5 (Multi-Scale Tiling) as deferred/no-op on the current 500mx400m crop.
- Retract "0.35s VRAM" phrasing in favor of "0.35s latency / 1.2 GB VRAM".
- Evolve StratumRO into a general GeoAI Platform with registry-driven Workflow Modes rather than a single fixed pipeline.
- Separate deterministic GIS math (GEOS/GDAL/Shapely) strictly from AI reasoning.
- Multi-level validation (L0 to L5) and multi-source Evidence Graph.

### NEW DEPENDENCIES:
- ZERO new external packages added. Utilizes existing NumPy, SciPy, Rasterio, Shapely, Laspy, FastMCP.

### TEST RESULTS:
- 184 tests ran: 175 passed, 9 skipped (optional GDAL/C++ extensions), 0 failed.

### REAL DATA USED:
- Authentic Cluj Orthophoto (0.20m GSD), airborne LiDAR LAS/LAZ, DTM, nDSM (1.0m), and official Ground Truth (Tier 1: 29 buildings, unique benchmark: 150 buildings, 65 in active crop).
- All Phase 2 SHA-256 hashes verified 100% unchanged.

### BENCHMARK RESULTS (E0 Baseline vs E9 Reconciled):
- TP: 4 -> 4 (preserved)
- FP: 90 -> 22 (-75.6% reduction)
- FN: 61 -> 61 (unchanged)
- Precision: 4.26% -> 15.38% (3.6x improvement)
- Recall: 6.15% (unchanged)
- F1: 5.03% -> 8.79%
- Mean IoU: 70.37% -> 66.59% (-3.78% courtyard trade-off)
- Centroid RMSE: 3.36m -> 3.04m
- Runtime: 13.15s -> 3.65s (3.6x speedup)

### KNOWN LIMITATIONS:
- Severe recall bottleneck (6.15%) remains the primary unsolved geodetic challenge.
- Courtyards enclosed by box prompting on complex institutional structures.
- Residual 22 False Positives contain 10-12 real unannotated physical buildings.

---

### REFERENCE ARTIFACTS:

#### 1. PHASE 3 RECONCILIATION REPORT:
```markdown
{reconciliation_text}
```

#### 2. PHASE 4 ADAPTIVE GEOAI CORE ARCHITECTURE MAP:
```markdown
{architecture_map}
```

---

### MANDATORY KILO REVIEW QUESTIONS TO ANSWER:
1. Is the Phase 3 reconciliation honest, scientifically defensible, and complete?
2. Are the metrics interpreted correctly without feature inflation or overclaiming?
3. Is Phase 2 baseline integrity and non-mutation verified?
4. Is the Phase 4 architectural blueprint (WorkflowModeRegistry, Common Geospatial Model, Multi-Level Validation L0-L5, Evidence Graph) sound, or does it risk unnecessary complexity?
5. Does the Simulation Engine design (procedural scenes, error perturbations, sensor simulation) maintain strict separation between synthetic data and real benchmarks?
6. What are the Top 5 prioritized recommendations for Phase 4 implementation?
"""

    provider = UnionAlphaProvider(default_model=MODEL_NAME)
    print(f"[*] Submitting to Kilo ({MODEL_NAME})...")
    t0 = time.time()
    resp = provider.generate(
        prompt=submission,
        system_prompt=SYSTEM_PROMPT,
        model=MODEL_NAME,
        max_tokens=4000,
        temperature=0.15,
        timeout=180.0
    )

    if resp.status != "success" or not resp.content:
        raise RuntimeError(f"Kilo review failed: {resp.error}")

    print(f"[+] Kilo review received in {time.time() - t0:.1f}s ({len(resp.content):,} characters)")

    header = f"""# KILO ADVERSARIAL MILESTONE REVIEW — Phase 3 Reconciliation & Phase 4 Architecture

**Reviewer:** Kilo (`{MODEL_NAME}` via OpenRouter API)  
**Date:** {time.strftime('%Y-%m-%d')}  
**Target:** Phase 3 Reconciliation & Phase 4 Adaptive GeoAI Core Blueprint  
**Standard:** AGENTS.md 8 Evidence-First Scientific Rules & Master Execution Protocol (Section 37)  

---

"""
    full_review = header + resp.content.strip() + "\n"
    OUTPUT_PATH.write_text(full_review, encoding="utf-8")
    print(f"[+] Successfully saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    run()
