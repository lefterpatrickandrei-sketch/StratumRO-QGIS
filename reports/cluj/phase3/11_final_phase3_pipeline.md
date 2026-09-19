# 11. Final Phase 3 Pipeline Architecture & Operational Guide

**Document ID:** `REPORT-CLUJ-P3-11-FINAL-PIPELINE`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (IMPLEMENTED, TESTED, REPRODUCED)

---

## 1. Architectural Blueprint

The definitive Phase 3 production architecture executes the following deterministic-AI hybrid workflow:

```text
       ┌───────────────────────┐         ┌────────────────────────┐
       │ CLJ RGB Orthophoto    │         │ CLJ LiDAR LAZ + DTM    │
       │ (0.20m, EPSG:3844)    │         │ (EPSG:3844)            │
       └───────────┬───────────┘         └───────────┬────────────┘
                   │                                 │
                   │                                 ▼
                   │                     ┌────────────────────────┐
                   │                     │ Authentic nDSM (1.0m)  │
                   │                     │ (cluj_ndsm_1m.tif)     │
                   │                     └───────────┬────────────┘
                   │                                 │
                   ▼                                 ▼
       ┌──────────────────────────────────────────────────────────┐
       │ STAGE 1: Candidate Generation (CandidateGenerator)       │
       │ - Height threshold >= 2.5m                               │
       │ - Morphological Closing 5x5 + Binary Hole Filling        │
       │ - Area Constraints: 25.0 m² <= Area <= 8,000.0 m²        │
       └───────────────────────────┬──────────────────────────────┘
                                   │ (75 Candidate Envelopes)
                                   ▼
       ┌──────────────────────────────────────────────────────────┐
       │ STAGE 2: Multimodal Vegetation Filtering                 │
       │ (MultimodalVegetationFilter)                             │
       │ - Optical Excess Green: ExG = 2G - R - B                 │
       │ - LiDAR ASPRS Class Evidence (Class 6 vs 3,4,5)          │
       │ - Surface Roughness: sigma_Z                             │
       └───────────────────────────┬──────────────────────────────┘
                                   │ (31 Accepted Building Candidates)
                                   ▼
       ┌──────────────────────────────────────────────────────────┐
       │ STAGE 3: Vision Prompting & Segmentation                 │
       │ (PromptGenerator + SAM2ImagePredictor)                   │
       │ - Deterministic Bounding Box Prompting                   │
       │ - Meta SAM 2 Hiera Neural Inference on GPU (CUDA)        │
       └───────────────────────────┬──────────────────────────────┘
                                   │ (31 Raw Segmented Masks)
                                   ▼
       ┌──────────────────────────────────────────────────────────┐
       │ STAGE 4: Topology Mask Fusion & Vector Cleanup           │
       │ (MaskFusionEngine)                                       │
       │ - Intersection Adjacency Graph & Unary Union             │
       │ - Multi-wing building assembly (31 -> 26 structures)     │
       │ - Douglas-Peucker Simplification (0.25m step reduction)  │
       └───────────────────────────┬──────────────────────────────┘
                                   │ (26 Clean Vector Footprints)
                                   ▼
       ┌──────────────────────────────────────────────────────────┐
       │ STAGE 5: Dominant-Orientation Cadastral Regularization   │
       │ (OrientationAwareRegularizer)                            │
       │ - Compute facade angle theta via minimum rotated bbox    │
       │ - Rotate (-theta) -> snap 90° edges -> rotate (+theta)   │
       │ - Area preservation check (Delta Area <= 20%)            │
       └───────────────────────────┬──────────────────────────────┘
                                   │
                                   ▼
       ┌──────────────────────────────────────────────────────────┐
       │ STAGE 6: Serialization & QGIS Review                     │
       │ - Output: cluj_phase3_integrated_predictions.geojson    │
       │ - Visual Review: StratumRO_Cluj_Phase3_Spectator.qgs     │
       └──────────────────────────────────────────────────────────┘
```

---

## 2. Re-running the Final Pipeline

The entire pipeline is executable from the project root in a single CLI invocation:

```powershell
# Activate local virtual environment
.\venv\Scripts\Activate.ps1

# Run integrated Phase 3 extraction pipeline
python tools/phase3_experiment_runner.py --experiment E9
```

Output artifacts are generated at:
- Predictions: `workspace/predictions/cluj_phase3_integrated_predictions.geojson`
- Experiment Metadata: `reports/cluj/phase3/experiments/EXP_009_integrated_pipeline/`
- QGIS Project: `workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs`
