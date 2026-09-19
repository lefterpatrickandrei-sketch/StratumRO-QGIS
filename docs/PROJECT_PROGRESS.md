# STRATUMRO — PROJECT PROGRESS

> **Canonical Progress, Quality Gate & State Synchronization Document**  
> **Repository:** `lefterpatrickandrei-sketch/StratumRO-QGIS`  
> **Governance:** AGENTS.md Evidence-First Rules & Master Execution Protocol  
> **Last Synchronized:** 2026-09-19  

---

## 1. Current Phase

* **Active Phase:** **Phase 3 Reconciled & Frozen Checkpoint → Phase 4 Planned / Blueprinted (NOT STARTED)**
* **Current Milestone:** Cluj AOI Algorithmic Extraction Optimization Reconciled, Audited, Visually Documented & Synchronized on GitHub Remote.
* **Decision Status:** Phase 3 officially audited by Kilo (`reports/cluj/phase3/KILO_PHASE3_INDEPENDENT_AUDIT.md`), reconciled (`reports/cluj/phase3/PHASE3_RECONCILIATION.md`), visually inspected in QGIS (`StratumRO_phase3_overview.png`), and frozen across Git checkpoints (`19c6d3c`, `1a335d1`, `766ac04`).
* **Operational Mode:** Pre-Phase 4 Stop-and-Verify state synchronization.

---

## 2. Current Baseline & Git State

* **Historical Phase 2 Baseline (Frozen Reference):**  
  Commit: [`4c1497a2c8a2a743fcd94906d688b20be1224821`](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/commit/4c1497a2c8a2a743fcd94906d688b20be1224821)  
  Message: `phase2(cluj): finalize evidence-first benchmark foundation`  
  *Note: Phase 2 benchmark data, ground truth vectors, and reference rasters remain 100% frozen and byte-identical.*

* **Current Remote Git Baseline (`origin/main`):**  
  Commit: [`766ac04b6effc52436e7c84c24178e6bcfb7339a`](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/commit/766ac04b6effc52436e7c84c24178e6bcfb7339a)  
  Message: `feat(ai): synchronize model routing, provider configuration, and external agent instructions for cross-model consulting`  
  *All Phase 3 governance documents, visual products, reconciliation reports, empirical provider/model inventories (`docs/MODEL_PROVIDER_INVENTORY.md`), and cross-model consulting instructions (`.kilorules`, `CLAUDE.md`, `KILO_CONFIGURATION_AUDIT.md`) are committed and pushed to `origin/main`.*

* **Working Tree State:** `100% clean` (`HEAD == origin/main`).

---

## 3. Phase Status Table

| Phase | Goal / Scope | Status | Code State | Tests | Real E2E Data | Visual Product | Independent Review | Notes |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Phase 1** | Initial Toolchain & Plugin Foundation | **FROZEN / HISTORICAL BASELINE** | Functional | 40 passed | Local test fixtures | UI screenshots | Internal | PyQGIS plugin, TopoLT DXF, .CP, 3D LoD1 extrusion |
| **Phase 2** | Cluj Benchmark & Provenance Foundation | **FROZEN** | Functional | 55 passed | Authentic Cluj Ortho + LiDAR | Yes (`inspectie_orto_cadastru_ai.jpg`) | Kilo Re-Audit (PASS) | 150 unique reference buildings, nDSM 1.0m, CRS EPSG:3844 forensic validation |
| **Phase 3** | AI Extraction Quality Optimization | **VERIFIED / RECONCILED / FROZEN CHECKPOINT** | Functional | 184 passed (175 passed, 9 skipped) | Real Cluj Crop ($500\text{m} \times 400\text{m}$) | Yes (`StratumRO_phase3_overview.png`, Spectator QGS) | Kilo Independent Audit (PASS $\to$ RECONCILED) | Slashed FP by 75.6% (90 $\to$ 22), 3.6× speedup (13.15s $\to$ 3.65s). Candidate Production (Assisted Cadastre) |
| **Phase 4** | Adaptive GeoAI Core & Simulation Architecture | **PLANNED / BLUEPRINTED / NOT STARTED** | Blueprint ready | 0 new | Pending Step 1 | Architecture Map (`ADAPTIVE_GEOAI_CORE_MAP.md`) | Kilo Phase 4 Review (Sound, warnings on complexity) | TaskSpec, WorkflowModeRegistry, Multi-Level Validation L0-L5, Evidence Graph |
| **Phase 5** | Domain Packs & Expansion AOIs | **PLANNED** | Not started | — | Oradea, Rural AOIs | Pending | Pending | Domain packs: Cadastre, Geodesy, 3D LiDAR, Remote Sensing |

---

## 4. Current Project Identity & Platform Position

### Current Identity: GeoAI Platform
StratumRO is being developed as an **AI-powered geospatial platform (GeoAI platform)**.
* It is **NOT** merely a single cadastral building extraction script.
* It is **NOT YET** a fully autonomous universal geospatial operating system.
* Pre-cadastral building extraction remains an essential, battle-tested existing domain capability.
* QGIS remains the primary client, control surface, and human visual inspection environment.

The platform architecture is evolving toward full lifecycle capability:
```text
UNDERSTAND → GENERATE → SIMULATE → ANALYZE → TRANSFORM → PREDICT → VALIDATE → ADAPT → TRACE
```

### Architectural Tiers: Core vs Clients
```text
                          STRATUMRO CORE
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
[ QGIS Desktop Client ]  [ Headless MCP / API ]   [ Future Clients ]
- Current Primary Surface - Automation & Agents   - Desktop / Standalone
- PyQGIS 3.40 Integration - FastMCP Server        - Web Spectator
- Visual Layer Inspection - CLI Pipelines         (Planned / Deferred)
- TopoLT CAD / PAD Export - REST Endpoints
```
*Current Implementation Note:* StratumRO is currently primarily QGIS-centered. Future standalone clients remain architectural targets, not claimed implementations.

### Providers Are Capabilities, Not The Product
StratumRO is not a wrapper around external AI APIs. Providers are interchangeable external capabilities:
```text
TASK → UNDERSTAND → CAPABILITY SELECTION → TOOL / MODEL SELECTION → EXECUTION → VALIDATION → EVIDENCE
```
External LLM/VLM providers can change or fail without altering deterministic task definitions or mathematical GIS integrity.

---

## 5. Permanent Visual Product Policy

Every meaningful geospatial or QGIS product in StratumRO must be visually inspectable. Textual logs and Markdown tables alone are strictly insufficient.

```text
CODE → REAL EXECUTION → REAL GEOSPATIAL PRODUCT → QGIS VISUALIZATION → STATIC VISUAL EVIDENCE → DOCUMENTATION
```

* **QGIS Inspection Project:** Real data loaded in Romania Stereo 70 (`EPSG:3844`), pre-zoomed to the active AOI bounding box with readable symbology.
* **Static Visual Export:** Minimum one high-resolution inspection map containing canvas, legend, graphic scale, north arrow, and verified metric panel.
* **Applies to all products:** Orthophoto processing, LiDAR/nDSM, segmentation, cadastre, 3D reconstruction, simulation, synthetic data, and change detection.

---

## 6. Phase-by-Phase Evolution: Phase 2 $\to$ Phase 3 Transition

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

PHASE 3 OPTIMIZATION (RECONCILED & FROZEN CHECKPOINT)
=====================================================
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

## 7. Verified Products & Visual Evidence

1. **`workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs`:** Official QGIS 3.40 inspection project with pre-centered mapcanvas on the Cluj AOI ($390650 - 391150\text{ m}$ E, $585350 - 585750\text{ m}$ N).
2. **`docs/assets/phases/phase3/StratumRO_phase3_overview.png`:** 2500×2000 px (2.5 MB) technical inspection map showing 0.20m RGB orthophoto, cyan Ground Truth, neon green E9 predictions, scale bar, and verified metrics panel.
3. **`docs/assets/phases/phase3/StratumRO_cluj_full_campus_ortho.png`:** 2500×2500 px (5.2 MB) full USAMV Cluj Campus mosaic (1.05 km × 1.05 km, 110 ha) showing all 150 cadastral buildings, 0.15m GSD RGB orthophoto, and Phase 3 active crop bounding box.
4. **`workspace/phase3/predictions/EXP_009_integrated_pipeline_reg.geojson`:** 26 regularized building footprints in Stereo 70.
5. **`workspace/phase3/derived/cluj_lidar_classes_1m.tif`:** Rasterized 1.0m ASPRS classification grid.
6. **`reports/cluj/phase3/PHASE3_RECONCILIATION.md`:** Authoritative 10-question reconciliation document.
7. **`reports/cluj/phase3/KILO_PHASE4_ARCHITECTURE_REVIEW.md`:** Independent adversarial review.
8. **`reports/cluj/phase3/KILO_PHASE3_INDEPENDENT_AUDIT.md`:** 19-section independent forensic audit.

---

## 8. Provider Ecosystem & Cross-Model Governance

The repository contains an empirical, smoke-tested provider/model inventory ([`docs/MODEL_PROVIDER_INVENTORY.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/MODEL_PROVIDER_INVENTORY.md), [`docs/MODEL_PROVIDER_INVENTORY.json`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/MODEL_PROVIDER_INVENTORY.json)):

* **Provider Status Hierarchy:** `DISCOVERED` $\to$ `CONFIGURED` $\to$ `AVAILABLE` $\to$ `CONNECTED` $\to$ `SMOKE_TESTED` $\to$ `BENCHMARKED` (or `UNAVAILABLE`, `NOT_CONFIGURED`, `DEFERRED`).
* **OpenRouter / Kilo (`openrouter_kilo`):** CONNECTED & TESTED. Model `meta-llama/llama-3.3-70b-instruct` verified in 722 ms for independent adversarial reviews and architectural reasoning.
* **NVIDIA NIM (`nvidia_nim`):** CONNECTED & TESTED. Model `meta/llama-3.2-11b-vision-instruct` verified in 652 ms with image chip payload for multimodal vision QA. `meta/llama-3.3-70b-instruct` is retired (HTTP 410 EOL).
* **Local SAM 2 (`local_sam2`):** LOADED & BENCHMARKED. PyTorch CUDA 12.4 runtime with `models/sam2/sam2_hiera_tiny.pt` (155.9 MB) and ONNX models.
* **Local Mock Engine (`local_mock`):** AVAILABLE & TESTED (0.0 ms, zero token cost).
* **OpenAI Direct (`openai`):** NOT_CONFIGURED (`OPENAI_API_KEY` missing).
* **Ollama (`ollama`):** UNAVAILABLE (Local daemon offline).

### External AI Collaboration Standards:
The repository preserves shared instructions for external AI models:
* [`.kilorules`](file:///c:/Users/lefpa/Downloads/QGIS-AI/.kilorules) — Model routing, Stereo 70 local math restrictions, and subagent settings.
* [`CLAUDE.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/CLAUDE.md) — Claude Code guidelines and deterministic testing commands.
* [`KILO_CONFIGURATION_AUDIT.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/KILO_CONFIGURATION_AUDIT.md) — System and VS Code extension audit report.

---

## 9. Future Simulation Direction (Architectural Target)

Future platform evolution includes procedural and physics-based GeoSimulation:
* `Synthetic Data Generation`: Procedural Stereo 70 parcels, cadastre, and roof geometries.
* `Sensor Simulation`: Orthophoto flight-line simulation, lighting variation, and LiDAR point-density attenuation.
* `Error & Scenario Simulation`: Disputed boundary simulations, cadastre overlap injection, tree canopy occlusion.
* `Synthetic-to-Real Validation`: Training on procedural Romanian scenes and evaluating on real Cluj ground truth.
* *Status:* **PLANNED / ARCHITECTURAL DIRECTION** (Not yet implemented).

---

## 10. Phase 4 Entry Criteria & Status

### Status: PLANNED / BLUEPRINTED / NOT STARTED
Phase 4 architecture is documented in [`docs/architecture/ADAPTIVE_GEOAI_CORE_MAP.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/architecture/ADAPTIVE_GEOAI_CORE_MAP.md), covering:
* `TaskSpec` formal schema
* `WorkflowModeRegistry` with 11 adaptive modes
* Multi-Level Data Validation (L0–L5)
* Evidence Graph & Cryptographic Provenance

### Entry Criteria: SATISFIED
1. Phase 3 reconciled, audited, and committed: **YES (`766ac04`)**
2. Visual evidence verified and inspectable in QGIS: **YES (`StratumRO_phase3_overview.png`)**
3. Provider and model inventory empirical and verified: **YES (`docs/MODEL_PROVIDER_INVENTORY.md`)**
4. Cross-model consulting instructions established: **YES (`.kilorules`, `CLAUDE.md`)**
5. Remote GitHub synchronization complete: **YES (`origin/main`)**

> **CRITICAL RULE:** Phase 4 is **NOT** automatically started by this documentation synchronization. Phase 4 Step 1 will begin as a separate, authorized development task.
