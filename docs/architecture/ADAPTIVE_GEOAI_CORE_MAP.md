# ADAPTIVE_GEOAI_CORE_MAP.md — StratumRO GeoAI Platform Architecture

**Document:** `docs/architecture/ADAPTIVE_GEOAI_CORE_MAP.md`  
**Status:** ARCHITECTURAL SPECIFICATION & MIGRATION BLUEPRINT  
**Version:** 4.0.0-draft  
**Platform Identity:** GeoAI Orchestration + Geospatial Intelligence + Simulation + Experimentation Platform  

---

## 1. Architectural Topology: End-to-End Execution Flow

```text
                                [ User / Client Request ]
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │   Task Understanding  │  (Creates structured TaskSpec)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │     ContextEngine     │  (Workspace, QGIS canvas, CRS, layers)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │     DataProfiler      │  (L0–L5 Multi-level validation, suitability)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │   Resource Snapshot   │  (CPU, RAM, GPU, VRAM, CUDA/DirectML, APIs)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │      RiskEngine       │  (LOW, MEDIUM, HIGH, CRITICAL gates)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │  WorkflowModeEngine   │  (Selects optimal workflow mode from registry)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │    WorkflowPlanner    │  (Decomposes into TaskGraph DAG)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │     AgentSelector     │  (Selects scoped agents & MCP tools)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │     TaskExecutor      │  (Asynchronous DAG execution via EventBus)
                                └───────────┬───────────┘
                                            │
                  ┌─────────────────────────┴─────────────────────────┐
                  ▼                                                   ▼
      [ Deterministic GIS Math ]                            [ AI Provider Inference ]
      - GEOS, GDAL, Shapely                                 - Frontier / OpenRouter
      - pyproj, Stereo 70 (EPSG:3844)                       - NVIDIA NIM / Local SAM2
      - 90° CAD Orthogonalization                           - Ollama / Local Fallback
      (Zero LLM Tokens)                                     (Reasoning, Vision, Synthesis)
                  │                                                   │
                  └─────────────────────────┬─────────────────────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │   Validation & QA     │  (Pass / Retry / Replan / Human Review)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │ Provenance & Evidence │  (Multi-source Evidence Graph)
                                └───────────┬───────────┘
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │  Final Result & Export│  (GeoPackage, TopoLT DXF, .CP, CityJSON)
                                └───────────────────────┘
```

---

## 2. Registry-Driven Workflow Modes

Rather than a hardcoded monolithic decision tree, workflows are defined as modular plugins registered in the `WorkflowModeRegistry`:

| Workflow Mode | Pipeline Stages & Selected Agents | Human Approval Gate | Primary Target |
|:---|:---|:---:|:---|
| **`FAST_DETERMINISTIC`** | `GIS Engineer → Vectorizer → CAD Exporter` | None | Geometry transforms, CRS projection, PAD tables |
| **`GIS_ANALYSIS`** | `Planner → GIS Engineer → Spatial Validator → Tester` | On commit | Planar partitioning, cadastral parcel topology |
| **`LIDAR_3D`** | `GIS Specialist → LidarProcessor → Volumetric3D → Validator` | None | nDSM, LoD1 solid shells, RANSAC roof planes |
| **`VISION_SEGMENTATION`** | `Vision Engineer → SAM2 Predictor → Vectorizer → Validator` | Review mask | Aerial building boundary extraction |
| **`MULTIMODAL_GEOAI`** | `Vision Researcher → Sensor Fusion → SAM2 → VLM Verifier` | Review mask | Ortho + LiDAR + ExG composite segmentation |
| **`GEODESY_SURVEY`** | `Planner → Geodesy Specialist → Independent Validator → Tester` | **REQUIRED (ASK)** | TopoLT DXF export, .CP interchange files |
| **`CADASTRAL_PRECADASTRAL`** | `Candidate Gen → Veg Filter → SAM2 → Fusion → Regularizer` | **REQUIRED (ASK)** | Ordinul 600/2023 pre-cadastral building footprints |
| **`RESEARCH`** | `Researcher → Evidence Check → Synthesizer → Reviewer` | None | Model evaluations, literature, ANCPI legislation |
| **`DATA_ACQUISITION`** | `Data Researcher → License Check → Downloader → Profiler` | On write | Orthophoto VRT, airborne LiDAR ingest |
| **`BENCHMARK_EXPERIMENT`**| `Experimenter → Pipeline Runner → Evaluator → Auditor` | None | Ablation studies, IoU, Boundary RMSE, Wilson CI |
| **`SIMULATION`** | `Scenario Engine → Sensor Simulator → Perturbation → Evaluator`| None | Robustness stress tests, domain gap analysis |

---

## 3. Multi-Level Data Validation Hierarchy

StratumRO evaluates datasets across 6 explicit, non-binary levels of validation:

```
[ L5: FIELD-VALIDATED ]     Verified against ground-truth GNSS RTK / Total Station logs
          ▲
[ L4: PURPOSE-SUITABLE ]    Assessed as technically sufficient for specific use case
          ▲
[ L3: CROSS-SOURCE AGREED ] Optical footprints agree with LiDAR elevation profiles
          ▲
[ L2: SPATIALLY CONSISTENT] Valid topology, no self-intersections, valid Stereo 70 bounds
          ▲
[ L1: DATASET VALID ]       Valid GDAL/Laspy format, valid headers, non-empty geometries
          ▲
[ L0: FILE VALID ]          Physical file exists on disk, valid SHA-256, uncorrupted
```

---

## 4. Multi-Source Evidence Classification

Every building footprint, parcel, and cadastral deliverable is mapped to a multi-source **Evidence Graph**, preventing the reduction of uncertainty to a single arbitrary percentage:

* `OBSERVED`: Ground measurements, raw aerial orthophoto pixels, LiDAR point returns.
* `DERIVED`: Morphological nDSM height models, Excess Green Index (ExG), surface roughness $\sigma_Z$.
* `MODEL_PREDICTION`: SAM2 binary logits, ONNX DirectML mask inference.
* `HEURISTIC`: 90° Minimum Rotated Rectangle orthogonalization, eave retraction offset ($-0.40\text{ m}$).
* `HUMAN_DECISION`: Surveyor preview inspection, manual node adjustment, ANCPI sign-off.
* `EXTERNAL_REFERENCE`: ANCPI eTerra registered parcel boundary, official ground truth.
* `SYNTHETIC`: Procedurally generated building geometries or perturbed sensor returns.
* `SIMULATED`: Controlled error injections (spatial drift, LiDAR noise, vegetation occlusion).

---

## 5. Simulation & Experiment Engine Blueprint

The simulation engine enables synthetic data generation and robustness testing without contaminating real benchmarks:

```text
                         SIMULATION ENGINE
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
[ Procedural GeoScene ]   [ Sensor Simulation ]   [ Error Perturbation ]
 - Road networks           - Synthetic RGB Ortho   - Horizontal / Vertical drift
 - Parcel topologies       - Synthetic LiDAR LAS   - Point cloud sparsification
 - Parametric roofs        - Synthetic nDSM Depth  - Vegetation overgrowth
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                     [ Domain Gap Evaluator ]
                     - Real held-out evaluation
                     - Hard-case failure clustering
                     - Active learning refinement
```

---

## 6. Implementation Phasing Strategy

* **Step 1:** Reconcile & freeze Phase 3 (`PHASE3_RECONCILIATION.md`).
* **Step 2:** Implement `TaskSpec` and `WorkflowModeRegistry` in `stratum_ro/ai/`.
* **Step 3:** Implement `DataProfiler` and `RiskEngine` to enforce Least Privilege execution.
* **Step 4:** Integrate `EvidenceGraph` into GeoPackage output schemas.
* **Step 5:** Build Minimal Simulation MVP (parametric building footprint perturbation).
