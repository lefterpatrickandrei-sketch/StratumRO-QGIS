---
trigger: model_decision
description: Decide when a task should become a Colab GPU job card instead of running locally, and how to hand results back.
---

# Hybrid routing & 2D-First Continuous Loop Rule

Applies when a task would train a model, run SAM 2.1 over many tiles, evaluate a VLM, or run the continuous 2D roof extraction loop on Colab Pro. Background: `docs/HYBRID_DEV_WORKFLOW.md`.

1. **Local GPU is an RTX 4050 with 6 GB; Colab Pro uses `A100` (`--gpu A100`).** The native `colab` CLI is installed directly on Windows (WSL2 is not required).
2. **Phase 1 is Strictly 2D Roof Shape (RGB-Only, Domain-Generalizable to Any Zone) -> Phase 2 is 3D (LOD1/LOD2 with Heights):**
   - Do NOT make the Phase 1 2D roof segmentation/vectorization pipeline depend on LiDAR `nDSM` heights; it must generalize to any city/commune/UAT using RGB orthophotos alone.
   - Heights (`nDSM` / photogrammetry) and roof planes are applied in the subsequent 3D stage on top of validated 2D roof polygons to build `LOD1` and `LOD2` models.
3. **Canonical Terminology & Opera GX Review Semantics (`user_verified_feedback_20261026.json`):**
   - `ADMIS`: Best available 2D roof shapes (both 4-node rectangles and 6–12 node articulated `L`, `U`, `T` roofs).
   - `AJUSTARE_CONTUR` (replaces `CALCAN_ERROR` — never call them "calcan"): Real buildings whose 2D roof contour needs adjustment (tree-crown occlusions biting a corner, single-slope/partial roof fragments, or neighbor/edge alignment).
   - `MUTILAT` (`MUTILATED`): Model vectorization errors where photogrammetric mesh distortions (e.g., at `NoData` borders) were mistaken for buildings.
   - `ELIMINAT_EROARE_MAJORA` (`FALSE_POS`): Major vectorization errors or non-building false positives (asphalt, cars, bare earth, autumn trees, or a second bad vectorization overlapping an `ADMIS` building).
4. **Hierarchical Spatial Deduplication (`ADMIS > AJUSTARE_CONTUR > MUTILAT > ELIMINAT`):**
   - Always deduplicate overlapping polygons (`_INCOMPLET` duplicates and double vectorizations on the same building) before generating training masks. Never allow an `ELIMINAT` / `FALSE_POS` polygon to overwrite pixels inside an `ADMIS` roof.
5. **Simultaneous 6-Form Validation Protocol (`V1..V6` in Parallel):**
   - Never validate a building using a single metric. Every iteration of the continuous loop must simultaneously evaluate:
     * `V1`: Multimodal Visual Inspection on rendered orthophoto chips (VLM + Agent visual check),
     * `V2`: Whole-Roof Structural Continuation (detects and merges half-roofs / single slopes),
     * `V3`: Tree-Crown Occlusion vs. Real `L/U/T` Shape (completes straight roof corners underneath overhanging trees),
     * `V4`: 2D Roof Orthogonality ($90^\circ/45^\circ$, min edge $\ge 1.20\text{ m}$, zero spikes),
     * `V5`: Anti-Deformation (`NoData` border) & Semantic Purity (no roads/cars/trees),
     * `V6`: Planar NMS (zero double vectorizations) & Whole-Zone Completeness.
6. **Always stop the Colab VM (`colab stop`)** when the loop finishes and record provenance (git SHA, hashes, before/after visual sheets).
