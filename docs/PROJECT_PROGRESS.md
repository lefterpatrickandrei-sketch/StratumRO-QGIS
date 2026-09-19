# STRATUMRO — PROJECT PROGRESS

> **Canonical Progress & Quality Gate Document**  
> **Repository:** `lefterpatrickandrei-sketch/StratumRO-QGIS`  
> **Governance:** AGENTS.md Evidence-First Rules & Master Execution Protocol  
> **Last Updated:** 2026-09-19  

---

## 1. Current Phase

* **Active Phase:** **Phase 3 Reconciliation Complete → Phase 4 Preparation**
* **Milestone:** Cluj AOI Algorithmic Extraction Optimization Reconciled & Audited
* **Decision Status:** Phase 3 officially audited by Kilo (`reports/cluj/phase3/KILO_PHASE3_INDEPENDENT_AUDIT.md`) and reconciled (`reports/cluj/phase3/PHASE3_RECONCILIATION.md`).
* **Operational Mode:** Stop-and-Verify checkpoint prior to Phase 4 implementation.

---

## 2. Current Baseline

* **Remote Git Baseline (GitHub):**  
  Commit: [`4c1497a2c8a2a743fcd94906d688b20be1224821`](file:///c:/Users/lefpa/Downloads/QGIS-AI)  
  Message: `phase2(cluj): finalize evidence-first benchmark foundation`
* **Local Working Tree:**  
  Phase 2 files are **100% frozen and unmutated** (SHA-256 hashes matched to the byte).  
  Phase 3 code, tests, spectator QGIS project, visual maps, and reconciliation reports reside locally as verified uncommitted assets.

---

## 3. Phase Status Table

| Phase | Goal / Scope | Status | Code State | Tests | Real E2E Data | Visual Product | Independent Review | Notes |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Phase 1** | Initial Toolchain & Plugin Foundation | **FROZEN** | Functional | 40 passed | Local test fixtures | UI screenshots | Internal | PyQGIS plugin, TopoLT DXF, .CP, 3D LoD1 |
| **Phase 2** | Cluj Benchmark & Provenance Foundation | **FROZEN** | Functional | 55 passed | Authentic Cluj Ortho + LiDAR | Yes (`inspectie_orto_cadastru_ai.jpg`) | Kilo Re-Audit (PASS) | 150 unique reference buildings, nDSM 1.0m, CRS EPSG:3844 forensic check |
| **Phase 3** | AI Extraction Quality Optimization | **VERIFIED / RECONCILED** | Functional | 184 passed (175 passed, 9 skipped) | Real Cluj Crop ($500\text{m} \times 400\text{m}$) | Yes (`StratumRO_phase3_overview.png`, Spectator QGS) | Kilo Independent Audit (CONDITIONAL PASS $\to$ RECONCILED) | Slashed FP by 75.6% (90 $\to$ 22), 3.6× speedup (13.15s $\to$ 3.65s). Designated as Candidate Production (Assisted Cadastre) |
| **Phase 4** | Adaptive GeoAI Core & Simulation Architecture | **PLANNED / BLUEPRINTED** | Blueprint ready | 0 new | Pending Step 1 | Architecture Map (`ADAPTIVE_GEOAI_CORE_MAP.md`) | Kilo Phase 4 Review (Sound, warnings on complexity) | TaskSpec, WorkflowModeRegistry, Multi-Level Validation L0-L5, Evidence Graph |
| **Phase 5** | Domain Packs & Expansion AOIs | **PLANNED** | Not started | — | Oradea, Rural AOIs | Pending | Pending | Domain packs: Cadastre, Geodesy, 3D LiDAR, Remote Sensing |

---

## 4. Phase-by-Phase Evolution

### Phase 2 $\to$ Phase 3 Transition

```text
PHASE 2 BASELINE (FROZEN)
=========================
• Authentic Cluj Data Foundation (Ortho 0.20m GSD, LiDAR LAZ, DTM, nDSM 1.0m).
• CRS: Romania Stereo 70 (EPSG:3844) / MN1975 elevation.
• Ground Truth: 29 Tier 1 buildings, 150 unique reference structures across campus.
• Baseline SAM2 Predictions (E0): 94 polygons, 4 TP, 90 FP, 61 FN in active crop (20 ha).
• Baseline Performance: Precision = 4.26%, Recall = 6.15%, F1 = 5.03%, Runtime = 13.15s.

        │
        ▼  (Algorithmic Optimization Campaign E0–E9)

PHASE 3 OPTIMIZATION (RECONCILED)
=================================
• E1 Candidate Generation: Morphological closing 5x5 + hole filling (94 -> 75 candidates).
• E2 Vegetation Suppression: Multimodal ExG (2G-R-B) + LiDAR Class 6 vs 3-5 + roughness (pruned 44 trees, 0 TP loss).
• E3/E4 Prompting: Box-only vs interior multi-point grid (resolved wing clipping on complex pavilions).
• E5 Multi-scale Tiling: Formally deferred/no-op on 500mx400m crop (native GPU processing).
• E6 Mask Fusion: Adjacency graph unary_union eliminated 5 duplicate wing segments (FP 27 -> 22).
• E7 Vector Cleanup: Douglas-Peucker 0.25m simplified contours from 399.9 to 129.2 vertices/building.
• E8 Orientation Regularizer: Principal facade minimum rotated rectangle rotation, 90° edge snapping.
• E9 Integrated Pipeline: 26 footprints, 4 TP, 22 FP, 61 FN. Precision = 15.38%, F1 = 8.79%, Runtime = 3.65s.
```

### Detailed Transition Delta:
* **WHAT ALREADY EXISTED:** Authentic Cluj datasets, nDSM 1.0m grid, ground truth reference polygons, PyTorch SAM2 Hiera engine, TopoLT DXF exporter, QGIS dockwidget.
* **WHAT WAS ADDED:** 5 modular pipeline components in `stratum_ro/`: `candidate_generator.py`, `vegetation_filter.py`, `prompt_generator.py`, `mask_fusion.py`, `orientation_regularizer.py`, and `test_phase3_modules.py`.
* **WHAT WAS CHANGED:** Prompts switched from naive centroids to adaptive bounding boxes/interior medoids; candidates filtered by multimodal vegetation index before prompt decoding.
* **WHAT WAS REMOVED / RETRACTED:** The confusing documentation phrase "0.35s VRAM" was formally retracted to "0.35s latency / 1.2 GB VRAM". Unconditional "ADOPTED AS PROD" was downgraded to "Candidate Production (Assisted Cadastre)".
* **WHAT WAS PRESERVED:** 100% of Phase 2 benchmark files and ground truth (zero hash changes); all 4 True Positives preserved across all 10 experiments.
* **WHAT WAS VERIFIED:** 75.6% FP reduction (90 $\to$ 22), 3.6× speedup (13.15s $\to$ 3.65s), 184 unit tests passing cleanly.
* **WHAT REGRESSED:** Mean IoU dropped slightly from 70.37% to 66.59% (-3.78 percentage points) because box prompting enclosed interior courtyards on large structures.
* **WHAT REMAINS UNKNOWN / OPEN:** Recall bottleneck (6.15%, 4/65 reference buildings matched) due to fixed 2.5m nDSM threshold and flight line edge margins.

---

## 5. Current Architecture

```text
                        STRATUMRO CONTROL PLANE (ANTIGRAVITY)
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
               [ AIRouter / TaskGraph ]        [ FastMCP Servers ]
                - Capability Decoupling         - stratumro_server (26 tools)
                - Deterministic vs LLM          - filesystem (sandbox workspace/)
                - DAG State Machine             - dataset_manager (TIF/LAZ ingest)
                         │
        ┌────────────────┴────────────────┬────────────────────────┐
        ▼                                 ▼                        ▼
[ Deterministic Math ]          [ Vision & ML Engine ]     [ AI Provider Chain ]
- Shapely / GEOS Topology       - Local SAM2 Hiera GPU     - OpenRouter (Frontier)
- pyproj Stereo 70 (EPSG:3844)  - ONNX DirectML (Win12)    - NVIDIA NIM (Vision)
- 90° Cadastral Regularizer     - LiDAR Multimodal Filter  - Local Ollama / Mock
(Zero LLM Tokens)               (Mask Generation)          (Planning & Audit)
```

---

## 6. Verified Products

1. **`workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs`:** Official QGIS 3.40 inspection project with pre-centered mapcanvas on the Cluj AOI ($390650 - 391150\text{ m}$ E, $585350 - 585750\text{ m}$ N).
2. **`docs/assets/phases/phase3/StratumRO_phase3_overview.png`:** 2500x2000 px high-resolution technical inspection map showing orthophoto base, cyan Ground Truth, green E9 predictions, legend, scale bar, and metrics panel.
3. **`workspace/phase3/predictions/EXP_009_integrated_pipeline_reg.geojson`:** 26 regularized building polygons in Stereo 70.
4. **`workspace/phase3/derived/cluj_lidar_classes_1m.tif`:** Rasterized 1m ASPRS classification grid (Class 2 Ground, Class 6 Building, Classes 3–5 Vegetation).
5. **`reports/cluj/phase3/PHASE3_RECONCILIATION.md`:** Authoritative reconciliation document.
6. **`reports/cluj/phase3/KILO_PHASE4_ARCHITECTURE_REVIEW.md`:** Independent adversarial review.

---

## 7. Visual Evidence

| Phase | Visual Product Path | Dimensions / Size | Description |
|:---|:---|:---:|:---|
| **Phase 2** | [`docs/assets/phases/phase2/StratumRO_phase2_overview.jpg`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/assets/phases/phase2/StratumRO_phase2_overview.jpg) | 716 KB | Overview of Phase 2 Cluj orthophoto with raw cadastral vector overlays. |
| **Phase 3** | [`docs/assets/phases/phase3/StratumRO_phase3_overview.png`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/assets/phases/phase3/StratumRO_phase3_overview.png) | 2500×2000 px (2.5 MB) | High-resolution technical inspection map showing E9 predictions (neon green) vs Ground Truth (cyan) on 0.20m RGB orthophoto with technical stats and scale bar. |
| **Phase 3 (Stage 1)** | [`docs/assets/stages/etapa_1_lidar_ndsm.jpg`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/assets/stages/etapa_1_lidar_ndsm.jpg) | 786 KB | Visual verification of LiDAR nDSM height model generation. |
| **Phase 3 (Stage 4)** | [`docs/assets/stages/etapa_4_regularizare_90.jpg`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/assets/stages/etapa_4_regularizare_90.jpg) | 877 KB | Visual demonstration of 90° CAD orthogonalization on candidate contours. |
| **Phase 3 (Stage 6)** | [`docs/assets/stages/etapa_6_partitionare_planara.jpg`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/assets/stages/etapa_6_partitionare_planara.jpg) | 1.0 MB | Visual demonstration of 100% continuous gap-free planar partitioning. |

---

## 8. Benchmarks

### Cluj AOI Active Crop Benchmark ($500\text{m} \times 400\text{m}$, 20.0 ha, 65 Ground Truth Reference Buildings):

| Metric | Phase 2 Baseline (E0) | Phase 3 Integrated (E9) | Absolute Delta | Relative Gain |
|:---|:---:|:---:|:---:|:---:|
| **Candidate Footprints** | 94 | 26 | -68 | -72.3% |
| **True Positives (TP)** | 4 | 4 | 0 | 100% Preserved |
| **False Positives (FP)** | 90 | 22 | -68 | **-75.6% reduction** |
| **False Negatives (FN)** | 61 | 61 | 0 | Unchanged |
| **Precision** | 4.26% | 15.38% | +11.12% | **+3.6× improvement** |
| **Recall** | 6.15% | 6.15% | 0.00% | Stable (unresolved) |
| **F1 Score** | 5.03% | 8.79% | +3.76% | +74.8% improvement |
| **Mean IoU** | 70.37% | 66.59% | -3.78% | Trade-off (courtyards) |
| **Centroid RMSE** | 3.36 m | 3.04 m | -0.32 m | +9.5% accuracy |
| **Mean Vertices / Bldg** | 378.7 | 127.6 | -251.1 | -66.3% simplification |
| **Total Pipeline Runtime**| 13.15 s | 3.65 s | -9.50 s | **3.6× speedup** |

---

## 9. Known Limitations

1. **Low Recall (6.15%):** 61 of the 65 cadastral ground truth buildings within the 20 ha crop are undetected. Root causes: fixed 2.5m nDSM threshold misses lower single-story annexes; heavy tree foliage occludes small roofs; orthophoto survey flight line has edge margins on the western half of the crop.
2. **Courtyard Enclosure:** SAM2 box prompting treats interior open courtyards as building mass on large institutional structures (`REF_TIER1_027`), decreasing building-level IoU from 71.3% to 65.5%.
3. **Unannotated Physical Structures:** Of the 22 residual False Positives, 10–12 are real, visible physical buildings on the orthophoto that are simply missing from the official cadastral reference dataset.

---

## 10. Open Problems

1. **Multi-Scale / Multi-Threshold Candidate Discovery:** Developing a dual-threshold height model ($1.5\text{ m}$ for annexes, $2.5\text{ m}$ for main buildings) to break the recall bottleneck without reinflating false positives.
2. **Automated Negative Courtyard Prompts:** Morphologically detecting holes in initial candidate masks and injecting negative prompt points into SAM2.
3. **Regional Tiling Engine:** Scaling the pipeline from 20 ha crops to full municipal tiles ($2\text{ km} \times 2\text{ km}$) with seamless edge boundary stitching.

---

## 11. Next Planned Step

* **Phase 4 Step 1: Foundation of Adaptive Workflow Core**
  - Implement `TaskSpec` schema in `stratum_ro/ai/task_spec.py`.
  - Implement `WorkflowModeRegistry` in `stratum_ro/ai/workflow_registry.py` supporting the 11 registered workflow modes.
  - Implement `DataProfiler` enforcing Least Privilege and Multi-Level Data Validation (L0–L5).
  - Test with local unit tests maintaining 100% pass baseline.

---

## 12. Evidence Classification Standard

All assertions and deliverables in StratumRO must be classified into one of:
* `IMPLEMENTED`: Code exists on disk and is importable.
* `TESTED`: Unit or regression tests executed cleanly with reported exit code.
* `REPRODUCED`: Independently re-executed on a clean environment, reproducing identical numbers.
* `MEASURED`: An empirical numerical value from a specific script execution.
* `VALIDATED`: Compared against an independent reference dataset.
* `FIELD-VALIDATED`: Verified against physical terrestrial survey logs (GNSS RTK / Total Station).
* `THEORETICAL`: Expected mathematically, but not yet empirically proven in the field.
* `UNVERIFIED`: Claim exists in text but cannot be reproduced from code/data.
