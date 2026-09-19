# ARTIFACT_MANIFEST.md — StratumRO Master Artifact & Provenance Manifest

> **Standard:** StratumRO Master Execution Protocol (Sections 21 & 22)  
> **Governance:** AGENTS.md 8 Evidence-First Scientific Rules  
> **Repository:** `lefterpatrickandrei-sketch/StratumRO-QGIS`  
> **Last Verified:** 2026-09-19  

---

## 1. Master Artifact Inventory

| Artifact Identifier | Phase | Artifact Type | Origin Classification | Physical Path | Lifecycle Status | Visualized | Tested | Notes / SHA-256 Hash |
|:---|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---|
| **`tier1_gt`** | Phase 2 | `VECTOR` | `EXTERNAL_REFERENCE` | `data/ground_truth/tier1_teren.geojson` | `FROZEN` | Yes | Yes | 29 official cadastral buildings in Stereo 70.<br>`4edecae807e795bb9dec46e41b61e7122526d88986440c9fe63f3f33d2574424` |
| **`tier2_gt`** | Phase 2 | `VECTOR` | `EXTERNAL_REFERENCE` | `data/ground_truth/tier2_extended_gt.geojson` | `FROZEN` | Yes | Yes | Extended cadastral reference polygons.<br>`44deb76b82f639f81fd64e4327a17a80783b48d6b0d188a818ef97f473671d34` |
| **`unique_150_gt`** | Phase 2 | `VECTOR` | `DERIVED` | `data/derived_reference/cluj_combined_unique_150.geojson` | `FROZEN` | Yes | Yes | 150 unique reference buildings across campus.<br>`967c3028da1e23c21f8362fcbb1381465d30d7b3073ce8b4b72cc19c8da5ad44` |
| **`cluj_ortho_crop`**| Phase 2 | `RASTER` | `OBSERVED` | `workspace/e2e/04_orthophoto/active_ortho_crop.tif` | `FROZEN` | Yes | Yes | 0.20m GSD RGB aerial orthophoto, 2500x2000 px.<br>`132b8dc43df659ffe420f2ce2de3998919199052c9a5a8d391c4a7e606d08bbb` |
| **`cluj_ndsm_1m`** | Phase 2 | `RASTER` | `DERIVED` | `workspace/derived/cluj_ndsm_1m.tif` | `FROZEN` | Yes | Yes | 1.0m normalized Digital Surface Model from LiDAR.<br>`0b4bc40b73f154a23a507137edbe44f41ab35c54d8149488695598df5d1b7220` |
| **`p2_raw_pred`** | Phase 2 | `VECTOR` | `MODEL_PREDICTION` | `workspace/predictions/cluj_raw_sam2_predictions.geojson` | `FROZEN` | Yes | Yes | Raw SAM2 masks (94 polygons, 4 TP, 90 FP).<br>`04d37e59a0d16082e08206a6e2ee6783fcb3fb9dea060bc9fd5924d1b2f14bc7` |
| **`p2_reg_pred`** | Phase 2 | `VECTOR` | `HEURISTIC` | `workspace/predictions/cluj_regularized_predictions.geojson`| `FROZEN` | Yes | Yes | 90° CAD regularized baseline footprints.<br>`1ad0517a2a8c07f3ca049df9322802072ae538cb7028c1ec3ae1b31fe92faf7b` |
| **`cand_gen_mod`** | Phase 3 | `CODE` | `DERIVED` | `stratum_ro/candidate_generator.py` | `VERIFIED` | N/A | Yes | Morphological closing $5\times5$ + hole filling. |
| **`veg_filter_mod`** | Phase 3 | `CODE` | `DERIVED` | `stratum_ro/vegetation_filter.py` | `VERIFIED` | N/A | Yes | Multimodal vegetation filter (ExG + LiDAR + $\sigma_Z$). |
| **`prompt_gen_mod`** | Phase 3 | `CODE` | `DERIVED` | `stratum_ro/prompt_generator.py` | `VERIFIED` | N/A | Yes | Adaptive box and multi-point interior medoid prompts. |
| **`mask_fusion_mod`**| Phase 3 | `CODE` | `DERIVED` | `stratum_ro/mask_fusion.py` | `VERIFIED` | N/A | Yes | Adjacency graph topology fusion (`unary_union`). |
| **`orient_reg_mod`** | Phase 3 | `CODE` | `DERIVED` | `stratum_ro/orientation_regularizer.py` | `VERIFIED` | N/A | Yes | Principal facade angle rotation & 90° orthogonal snapping. |
| **`p3_test_suite`** | Phase 3 | `CODE` | `TESTED` | `stratum_ro/test/test_phase3_modules.py` | `VERIFIED` | N/A | Yes | 5 unit test cases covering Phase 3 modules. |
| **`p3_spectator_qgs`**| Phase 3| `QGIS_PROJECT`| `DERIVED` | `workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs` | `VERIFIED` | Yes | Yes | Pre-centered QGIS 3.40 inspection project on Cluj AOI. |
| **`p3_overview_png`**| Phase 3 | `IMAGE` | `DERIVED` | `docs/assets/phases/phase3/StratumRO_phase3_overview.png` | `VERIFIED` | Yes | Yes | 2500x2000 px inspection map with legend and scale bar. |
| **`p3_e9_vector`** | Phase 3 | `VECTOR` | `MODEL_PREDICTION` | `workspace/phase3/predictions/EXP_009_integrated_pipeline_reg.geojson` | `VERIFIED` | Yes | Yes | 26 regularized building footprints (4 TP, 22 FP). |
| **`p3_lidar_cls`** | Phase 3 | `RASTER` | `DERIVED` | `workspace/phase3/derived/cluj_lidar_classes_1m.tif` | `VERIFIED` | Yes | Yes | 1.0m raster grid of ASPRS point cloud classes. |
| **`p3_audit_dossier`**| Phase 3| `BENCHMARK`| `MEASURED` | `workspace/phase3/audit_factual_dossier.json` | `VERIFIED` | N/A | Yes | Complete recalculated metrics and hashes across E0–E9. |
| **`p3_kilo_audit`** | Phase 3 | `REPORT` | `HUMAN_VERIFIED` | `reports/cluj/phase3/KILO_PHASE3_INDEPENDENT_AUDIT.md` | `VERIFIED` | N/A | Yes | Independent 19-section audit from OpenRouter (Llama 3.3). |
| **`p3_reconcile`** | Phase 3 | `REPORT` | `HUMAN_VERIFIED` | `reports/cluj/phase3/PHASE3_RECONCILIATION.md` | `VERIFIED` | N/A | Yes | Formal reconciliation answering the 10 mandatory questions. |
| **`p4_arch_map`** | Phase 4 | `REPORT` | `DERIVED` | `docs/architecture/ADAPTIVE_GEOAI_CORE_MAP.md` | `BLUEPRINT`| N/A | Yes | Architectural topology, TaskSpec, 11 workflow modes. |
| **`p4_kilo_review`** | Phase 4 | `REPORT` | `HUMAN_VERIFIED` | `reports/cluj/phase3/KILO_PHASE4_ARCHITECTURE_REVIEW.md`| `VERIFIED` | N/A | Yes | Adversarial milestone review on Phase 4 blueprint. |

---

## 2. Provenance Standards & Lineage Tracking

For every generated geospatial deliverable in StratumRO, the following provenance metadata must be preserved in file headers, sidecar JSON, or GeoPackage layer metadata:

```yaml
provenance:
  generator: "StratumRO CadastralVectorizer v3.2 / Phase 3 E9"
  source_data:
    orthophoto: "workspace/e2e/04_orthophoto/active_ortho_crop.tif"
    lidar_ndsm: "workspace/derived/cluj_ndsm_1m.tif"
    ground_truth: "data/derived_reference/cluj_combined_unique_150.geojson"
  spatial_reference:
    crs: "EPSG:3844 (Pulkovo 1942(58) / Stereo 70)"
    vertical_datum: "EPSG:5781 (Marea Neagra 1975)"
    extent_bbox: [390649.99, 585350.00, 391149.99, 585750.00]
  parameters:
    candidate_closing_kernel: "5x5"
    ndsm_height_threshold_m: 2.5
    vegetation_exg_threshold: 0.15
    douglas_peucker_tolerance_m: 0.25
    eave_retraction_offset_m: -0.40
    orientation_orthogonal_tol_m: 0.65
  evidence_classification: "MODEL_PREDICTION + HEURISTIC"
  validation_level: "L3_CROSS_SOURCE_AGREED"
  timestamp_iso: "2026-09-19T17:30:00Z"
```

---

## 3. Git Status & Storage Policy

1. **Tracked in Git (Source of Truth):**
   - Source code (`stratum_ro/`)
   - Test suites (`stratum_ro/test/`)
   - Architecture & governance specifications (`docs/`, `reports/`)
   - Lightweight reference vectors & manifests (`data/ground_truth/`, `docs/ARTIFACT_MANIFEST.md`)
   - Stable visual evidence (`docs/assets/phases/`)
2. **Local Only / Git Ignored (Large Binary Files):**
   - Heavy raw point clouds (`.laz` / `.las` > 100 MB)
   - Temporary preview caches (`workspace/output/preview/`)
   - Intermediate model checkpoints and raw PyTorch weights (`models/sam2/*.pt`)
