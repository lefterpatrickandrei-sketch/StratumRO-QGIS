# STRATUMRO — REPOSITORY ARCHITECTURE MAP

**Document Type:** Architecture / Forensic Repository Map  
**Project:** StratumRO  
**Repository:** `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS`  
**Commit:** `c976864` (Branch: `main`)  
**Audit Standard:** Strict Forensic Mode (Analysis Only — Zero Code Modification)  
**Date:** 2026-09-20  

---

## 1. EXECUTIVE SUMMARY & FORENSIC SCOPE

This document provides an exhaustive, empirical architectural map of the **StratumRO** repository. It serves as the baseline forensic audit required before executing any migration, refactoring, or reorganization.

### Core Audit Findings:
1. **Repository Composition**: The repository contains **611 total tracked and recognized assets**, including **201 active Python modules**, 35 test modules (214 tests: 205 passed, 9 skipped, 0 failed), 65 operational tooling scripts, 119 documentation files, 96 validation reports, and 3 local deep learning model weights/ONNX files.
2. **Deterministic Math Supremacy**: Zero coordinate hallucination. Geodetic transformations, Helmert 2D adjustments, 90° CAD orthogonalization, eave retraction offsets, polygon areas, perimeters, and PAD tables execute exclusively via deterministic local math (PROJ, GEOS, Shapely 2.0, GDAL).
3. **Cluj–USAMV True Role**: The Cluj–USAMV work is **NOT** obsolete legacy code. It represents the **First Integrated Multidomain Demonstrator of StratumRO**, uniting Photogrammetry, LiDAR, Computer Vision (SAM 2), Geodesy (Stereo 70), CAD Regularization, ANCPI Cadastre, and 3D LoD1 CityJSON.
4. **Primary Architectural Gaps**:
   - **Monolithic UI Coupling**: [`stratum_ro/stratum_ro_dockwidget.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/stratum_ro_dockwidget.py) (1300 lines) mixes PyQGIS GUI widgets with execution threads, business logic, and API calls.
   - **Hardcoded Local Paths**: [`dataset_resolver.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/dataset_resolver.py) and [`config.yaml`](file:///c:/Users/lefpa/Downloads/QGIS-AI/config.yaml) reference specific Windows user directories (`C:\Users\lefpa\Desktop\date\Z_VladP\...`).
   - **Universal vs Domain Entanglement**: [`vectorizer.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/vectorizer.py) (977 lines) couples generic polygon topology and orthogonalization with ANCPI-specific cadastral rules (`1CC`, `2CC`, eave retraction).

---

## 2. REPOSITORY SNAPSHOT

| Metric | Measured Value | Evidence |
| :--- | :--- | :--- |
| **Repository Root** | `c:\Users\lefpa\Downloads\QGIS-AI` | Filesystem inspection |
| **Active Branch & Commit** | `main` (`c976864`) | `git rev-parse HEAD` |
| **Python Runtime** | Python 3.10.11 (Virtualenv `venv/`) | `venv/Scripts/python -V` |
| **QGIS Desktop Runtime** | QGIS 3.40 LTR (OSGeo4W / MSVC) | Socket probe `127.0.0.1:9876` |
| **Total Tracked Assets** | 611 assets | AST Scanner Index |
| **Total Python Modules** | 201 active modules (excluding `.kilo/` worktrees) | AST Scanner Index |
| **Automated Test Count** | **214 discovered: 205 passed, 9 skipped, 0 failed** | `unittest discover stratum_ro/test` |
| **Skipped Tests Analysis** | Exactly 9 tests skipped due to missing PyQGIS GUI context in pure venv | `@unittest.skipIf(not HAS_QGIS)` |
| **Authoritative CRS** | Romania Stereo 70 (`EPSG:3844`), Cota Marea Neagră 1975 (`EPSG:5781`) | Geodetic math registry |
| **Primary AI Models** | Meta SAM 2 Hiera (Local ONNX/Torch), Llama 3.2 11B Vision (NIM), Llama 3.3 70B (OpenRouter) | Model registry |

---

## 3. ACTUAL REPOSITORY TREE

```text
c:\Users\lefpa\Downloads\QGIS-AI
├── .agents/                        # Agent configurations, rules, and plugins
│   ├── plugin.json
│   ├── rules/                      # System rules: evidence.md, geometry.md, qgis_runtime.md
│   └── skills/                     # Domain skills: gsd-cadastre, huashu-design, qgis-live
├── .github/
│   └── workflows/                  # CI/CD: ci.yml (Python 3.10/3.11), test-llm-orchestrator.yml
├── .kilo/                          # Adversarial reviewer worktrees & agent configs
├── config.yaml                     # Central project configuration & sensor thresholds
├── data/
│   ├── derived_reference/          # Intermediate verification references
│   ├── fixtures/                   # Golden geometry test fixtures
│   └── ground_truth/               # Frozen authoritative reference data (Tier 1: 29 bldgs, Tier 2: 150 bldgs)
├── datasets/                       # Local dataset placeholders (lidar, orthophotos, osm)
├── docs/                           # Documentation, architectural maps, historical audit resolutions
│   ├── architecture/               # Visual system maps, adaptive core blueprints
│   └── legislation_2026/           # ANCPI Ordinul 600/2023, MDLPA 904/2023 regulations
├── engine/                         # Core Geodetic Evaluation & Ablation Subsystem
│   ├── ablation_study.py           # 5-stage ablation framework (Configs A through E)
│   ├── benchmark_v2.py             # Automated benchmark execution harness
│   ├── evaluation.py               # 1134 lines: IoU, Hausdorff, Boundary RMSE, Centroid Shift, Wilson CI
│   ├── extended_evaluation.py      # Multi-crop evaluation
│   └── time_study_benchmark.py     # Cadastral time-efficiency analysis (89% acceleration)
├── mcp/                            # Model Context Protocol Subsystem
│   ├── stratumro_server.py         # FastMCP Server exposing 21 deterministic tools
│   └── dataset_manager/            # Semantic dataset cataloging
├── models/
│   └── sam2/                       # Local model artifacts: sam2_encoder.onnx, sam2_decoder.onnx, sam2_hiera_tiny.pt
├── reports/                        # Milestone reports, reconciliation audits, time studies
│   └── cluj/phase3/                # Phase 3 reconciliation reports & Kilo reviews
├── scratch/                        # Ad-hoc experimental scripts (non-production)
├── scripts/                        # Project validation and benchmark scripts
├── start_platform.py               # One-command Geospatial Platform launcher (Port 8000)
├── stratum_ro/                     # Primary Python Package & QGIS Plugin
│   ├── ai/                         # Phase 4 Adaptive GeoAI Control Plane
│   │   ├── closed_loop.py          # ClosedLoopOrchestrator (Tests <-> QGIS <-> NIM <-> Kilo)
│   │   ├── context.py              # ResourceSnapshot & QGIS MCP socket probe
│   │   ├── data_profiler.py        # L0-L5 Geodetic Validation Pipeline
│   │   ├── events.py               # Async SSE Event Stream
│   │   ├── executor.py             # Graph execution engine
│   │   ├── memory/                 # Session memory & secret scrubber
│   │   ├── provenance.py           # ProvenanceChain & Surveyor Sign-Off Lineage
│   │   ├── providers/              # Base, NvidiaNIM, UnionAlpha, OpenAI, Ollama, LocalMock
│   │   ├── registry.py             # CapabilityRegistry (deterministic bypass)
│   │   ├── risk.py                 # RiskEngine (ground truth immutability, command guardrails)
│   │   ├── router.py               # AIRouter (task dispatch)
│   │   ├── task_graph.py           # Directed Acyclic Graph orchestrator
│   │   ├── task_spec.py            # Typed TaskSpec & RiskTolerance
│   │   ├── tools/                  # FastMCP tool implementations
│   │   └── vlm_verifier.py         # Visual Language Model verification via NVIDIA NIM
│   ├── api/                        # Geospatial Platform REST/SSE Backend (FastAPI)
│   │   ├── app.py                  # FastAPI Application (Health, Layers, Canvas, Workflow, Export)
│   │   └── service.py              # PlatformService (Stereo 70 -> WGS84 transformers, QGIS socket)
│   ├── simulation/                 # Simulation Subsystem
│   │   └── perturbation.py         # PerturbationEngine (controlled jitter, scale, rotation stress)
│   ├── test/                       # Automated Test Suite (32 test files, 214 tests)
│   ├── web/                        # StratumRO Web Cockpit (Single Page Application)
│   │   ├── index.html              # Dark Luxury Geomatics Studio UI
│   │   ├── css/app.css             # Glassmorphic Geomatics Design System
│   │   └── js/app.js               # Leaflet Web Map, Live QGIS Mirror, Telemetry, Kilo Audit
│   ├── cad_exporter.py             # TopoLT CAD (.DXF), .CP, and PAD table generator
│   ├── cadastral_algorithm.py      # QGIS Processing Framework Algorithm
│   ├── cadastral_product.py        # Cadastral deliverable dataclasses
│   ├── candidate_generator.py      # Morphological closing & hole filling
│   ├── dataset_resolver.py         # Multimodal sensor dataset discovery
│   ├── geometric_reconstruction_v2.py # Geometry repair & RDP polygonization
│   ├── geometry_utils.py           # Shapely geometric primitives
│   ├── landuse_ancpi.py            # ANCPI land use category classifier
│   ├── lidar_processor.py          # Laspy point cloud height normalization
│   ├── lidar_quality_gate.py       # Point density & vertical error gate
│   ├── logic_handler.py            # Desktop orchestrator bridge
│   ├── mask_fusion.py              # Adjacency graph unary union mask merger
│   ├── onnx_engine.py              # ONNX DirectML / CPU inference wrapper
│   ├── orchestrator.py             # High-level task coordinator
│   ├── orientation_regularizer.py  # Facade angle detection & 90° snapping
│   ├── ortho_extractor.py          # Windowed GeoTIFF/VRT extractor
│   ├── processing_provider.py      # QGIS Processing Provider registration
│   ├── prompt_generator.py         # nDSM box & grid prompt generator
│   ├── pug_product.py              # Urbanism regulation validator
│   ├── regulatory_consensus.py     # ANCPI regulatory consensus checker
│   ├── sam2_engine.py              # Meta SAM 2 optical segmentation engine
│   ├── stratum_ro.py               # Main QGIS Plugin Class
│   ├── stratum_ro_dockwidget.py    # PyQGIS Interactive DockWidget GUI
│   ├── vectorizer.py               # 977 lines: 90° regularization, topology cleanup, planar partition
│   ├── vegetation_filter.py        # Optical ExG + LiDAR vegetation filter
│   └── volumetric_3d.py            # LoD1 solid extrusion & CityJSON v1.1
├── tools/                          # 65 Operational scripts (Analysis, Pipelines, Renders, Audits)
└── workspace/                      # Generated deliverables, e2e evidence, live canvas captures
```

---

## 4. MASTER COMPONENT INVENTORY TABLE

| Path | Current Function | Primary Class | Domain | Target Layer | Status | Action | Dependencies | Risk | Scientific Risk | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `stratum_ro/vectorizer.py` | 90° CAD regularization, 4-vertex rectangle fitting, planar partition | `DOMAIN` | Cadastre & Geometry | `DOMAIN / Cadastre & Geometry` | Active Production | `SPLIT` | Shapely, NumPy, SciPy | `CRITICAL` | `CRITICAL` | Tested (19 unit tests) |
| `stratum_ro/cad_exporter.py` | TopoLT DXF export (`1CC`, `2CC`, `CP`, `VARFURI`), PAD tables, `.CP` export | `DOMAIN` | Cadastre | `DOMAIN / Cadastre` | Active Production | `KEEP` | ezdxf, Shapely | `HIGH` | `CRITICAL` | Tested (14 unit tests) |
| `stratum_ro/volumetric_3d.py` | True 3D LoD1 solid extrusion (`MultiPolygonZ`), RANSAC roof planes, CityJSON | `DOMAIN` | 3D / City | `DOMAIN / 3D & City` | Active Production | `KEEP` | Shapely, NumPy, json | `MEDIUM` | `HIGH` | Tested (3 unit tests) |
| `stratum_ro/lidar_processor.py` | Laspy point cloud reader, ground filtering, nDSM derivation | `DOMAIN` | LiDAR | `DOMAIN / LiDAR` | Active Production | `KEEP` | laspy, numpy, scipy | `HIGH` | `HIGH` | Tested on Cluj LAZ |
| `stratum_ro/lidar_quality_gate.py` | ASPRS point density, pulse return count, vertical error check | `DOMAIN` | LiDAR | `DOMAIN / LiDAR` | Active Production | `KEEP` | laspy, numpy | `MEDIUM` | `HIGH` | Verified in Phase 2 |
| `stratum_ro/ortho_extractor.py` | Windowed chip extraction from large orthophoto VRT/GeoTIFF | `DOMAIN` | Photogrammetry | `DOMAIN / Photogrammetry` | Active Production | `KEEP` | rasterio, numpy | `MEDIUM` | `MEDIUM` | Verified on Cluj VRT |
| `stratum_ro/vegetation_filter.py` | Excess Green (ExG) index + LiDAR roughness filtering | `DOMAIN` | Remote Sensing | `DOMAIN / Remote Sensing` | Active Production | `KEEP` | numpy, rasterio | `MEDIUM` | `HIGH` | Tested (Phase 3 tests) |
| `stratum_ro/sam2_engine.py` | Meta SAM 2 Hiera inference wrapper (PyTorch / ONNX) | `AI` | Computer Vision | `AI / vision / SAM2` | Active Production | `WRAP` | torch, onnxruntime, numpy | `HIGH` | `HIGH` | Benchmarked (0.35s) |
| `stratum_ro/onnx_engine.py` | DirectML DirectX 12 & CPU ONNX Runtime executor | `AI` | Computer Vision | `AI / models / ONNX` | Active Production | `WRAP` | onnxruntime, numpy | `MEDIUM` | `LOW` | Tested (DirectML verified) |
| `stratum_ro/prompt_generator.py` | nDSM height thresholding to bounding box and point grid prompts | `AI` | Computer Vision | `AI / vision / Prompts` | Active Production | `WRAP` | numpy, scipy | `MEDIUM` | `MEDIUM` | Tested (Phase 3 tests) |
| `stratum_ro/candidate_generator.py`| Morphological closing 5x5 + hole filling on binary masks | `AI` | Computer Vision | `AI / vision / Postproc` | Active Production | `WRAP` | scipy.ndimage, numpy | `MEDIUM` | `MEDIUM` | Tested (Phase 3 tests) |
| `stratum_ro/mask_fusion.py` | Unary union and adjacency graph fusion of candidate masks | `AI` | Computer Vision | `AI / vision / Fusion` | Active Production | `WRAP` | shapely, networkx/numpy | `MEDIUM` | `MEDIUM` | Tested (Phase 3 tests) |
| `stratum_ro/orientation_regularizer.py` | Principal facade angle detection and 90° rotation snapping | `DOMAIN` | Cadastre & Geometry | `DOMAIN / Geometry` | Active Production | `KEEP` | shapely, numpy, math | `HIGH` | `CRITICAL` | Tested (Phase 3 tests) |
| `stratum_ro/dataset_resolver.py` | Authority resolution for LiDAR LAZ, DTM, Ortho, Ground Truth | `CORE` | Geospatial Data | `CORE / data` | Active Production | `REFACTOR` | os, hashlib, laspy, rasterio | `HIGH` | `HIGH` | Tested (Resolver tests) |
| `stratum_ro/cadastral_product.py` | ANCPI Ordinul 600 deliverable schemas and area validation | `DOMAIN` | Cadastre | `DOMAIN / Cadastre` | Active Production | `KEEP` | dataclasses, shapely | `MEDIUM` | `CRITICAL` | Tested |
| `stratum_ro/landuse_ancpi.py` | Land use destination classification (`1CC`, `2CC`, `DA`) | `DOMAIN` | Cadastre | `DOMAIN / Cadastre` | Active Production | `KEEP` | dataclasses | `LOW` | `HIGH` | Tested |
| `stratum_ro/pug_product.py` | Urban General Plan (PUG) zoning and setback compliance | `DOMAIN` | Urbanism | `DOMAIN / Urbanism` | Active Production | `KEEP` | shapely, dataclasses | `LOW` | `MEDIUM` | Tested |
| `stratum_ro/regulatory_consensus.py` | ANCPI geometry rules consensus check | `DOMAIN` | Cadastre | `DOMAIN / Cadastre` | Active Production | `KEEP` | shapely, numpy | `LOW` | `HIGH` | Tested |
| `stratum_ro/stratum_ro_dockwidget.py` | PyQGIS interactive dockwidget GUI (1300 lines) | `CLIENT` | QGIS Desktop GUI | `CLIENTS / QGIS / UI` | Active Production | `SPLIT` | qgis.core, qgis.gui, PyQt5 | `HIGH` | `LOW` | Live Verified |
| `stratum_ro/stratum_ro.py` | QGIS Plugin entrypoint, menus, toolbars | `CLIENT` | QGIS Desktop Core | `CLIENTS / QGIS / Plugin` | Active Production | `KEEP` | qgis.core, qgis.gui, PyQt5 | `MEDIUM` | `LOW` | Live Verified |
| `stratum_ro/processing_provider.py`| QGIS Processing Framework provider registration | `CLIENT` | QGIS Processing | `CLIENTS / QGIS / Processing`| Active Production | `KEEP` | qgis.core | `LOW` | `LOW` | Tested |
| `stratum_ro/cadastral_algorithm.py` | Native QGIS Processing algorithm implementation | `CLIENT` | QGIS Processing | `CLIENTS / QGIS / Processing`| Active Production | `WRAP` | qgis.core | `MEDIUM` | `LOW` | Tested |
| `stratum_ro/api/app.py` | FastAPI server (REST, SSE, layers, canvas, export) | `CLIENT` | Web API | `CLIENTS / API` | Active Production | `KEEP` | fastapi, uvicorn, pydantic | `MEDIUM` | `LOW` | Tested (8 unit tests) |
| `stratum_ro/api/service.py` | Platform service: QGIS TCP socket wire protocol, Stereo 70 transform | `CORE` | Geospatial Engine | `CORE / execution` | Active Production | `KEEP` | pyproj, shapely, socket | `MEDIUM` | `HIGH` | Tested |
| `stratum_ro/web/index.html` | Dark Luxury Geomatics Web Cockpit single-page app | `CLIENT` | Web Frontend | `CLIENTS / Web` | Active Production | `KEEP` | HTML5, Leaflet, CSS, JS | `LOW` | `LOW` | Live Verified |
| `stratum_ro/ai/closed_loop.py` | ClosedLoopOrchestrator: Tests <-> QGIS <-> NIM <-> Kilo | `CORE` | Workflow Governance | `CORE / workflow` | Active Production | `KEEP` | subprocess, socket, requests | `LOW` | `LOW` | Tested & Executed |
| `stratum_ro/ai/task_spec.py` | Declarative TaskSpec, WorkflowMode, RiskTolerance | `CORE` | Capability Framework | `CORE / workflow` | Active Production | `KEEP` | dataclasses, enum | `LOW` | `LOW` | Tested (13 unit tests) |
| `stratum_ro/ai/context.py` | ResourceSnapshot, hardware profiler, QGIS MCP socket probe | `CORE` | Execution Context | `CORE / execution` | Active Production | `KEEP` | psutil, socket, platform | `MEDIUM` | `LOW` | Tested |
| `stratum_ro/ai/data_profiler.py` | L0–L5 geodetic validation pipeline & spatial agreement | `CORE` | Geodesy & Validation | `CORE / validation` | Active Production | `KEEP` | pyproj, shapely | `HIGH` | `CRITICAL` | Tested |
| `stratum_ro/ai/risk.py` | RiskEngine, ground truth freeze, command guardrails | `CORE` | Governance & Security | `CORE / governance` | Active Production | `KEEP` | re, pathlib, dataclasses | `HIGH` | `CRITICAL` | Tested |
| `stratum_ro/ai/provenance.py` | ProvenanceChain, 8 evidence classes, surveyor sign-off | `CORE` | Provenance & Lineage | `CORE / provenance` | Active Production | `KEEP` | hashlib, time, json | `MEDIUM` | `HIGH` | Tested |
| `stratum_ro/ai/registry.py` | CapabilityRegistry with strict deterministic bypass | `CORE` | Capability Framework | `CORE / capability` | Active Production | `KEEP` | dataclasses, typing | `MEDIUM` | `HIGH` | Tested |
| `stratum_ro/ai/router.py` | AIRouter directing reasoning/vision to verified providers | `AI` | Model Routing | `AI / routing` | Active Production | `KEEP` | typing, dataclasses | `MEDIUM` | `LOW` | Tested |
| `stratum_ro/ai/task_graph.py` | Directed Acyclic Graph execution engine | `CORE` | Workflow Orchestration | `CORE / execution` | Active Production | `KEEP` | graphlib, concurrent.futures | `MEDIUM` | `LOW` | Tested |
| `stratum_ro/ai/vlm_verifier.py` | Vision Language Model inspection via NVIDIA NIM | `AI` | Multimodal Vision | `AI / vision` | Active Production | `KEEP` | base64, requests | `LOW` | `LOW` | Tested |
| `stratum_ro/simulation/perturbation.py` | PerturbationEngine: translation, rotation, scale, vertex jitter | `CORE` | Simulation & Stress | `CORE / simulation` | Active Production | `KEEP` | random, math, shapely | `LOW` | `HIGH` | Tested |
| `engine/evaluation.py` | Geodetic metrics: IoU, Hausdorff, Boundary RMSE, Centroid RMSE, Wilson CI | `CORE` | Evaluation & Metrics | `CORE / validation` | Active Production | `KEEP` | shapely, numpy, scipy | `CRITICAL` | `CRITICAL` | Tested (15 unit tests) |
| `engine/ablation_study.py` | 5-configuration formal ablation harness (Configs A through E) | `EXPERIMENT` | Scientific Benchmark | `CORE / simulation` | Active Production | `REFACTOR` | engine.evaluation | `MEDIUM` | `HIGH` | Verified in Phase 2 |
| `mcp/stratumro_server.py` | FastMCP server exposing 21 deterministic tools to AI agents | `MCP` | MCP Tool Gateway | `MCP / stratumro_server` | Active Production | `WRAP` | fastmcp, stratum_ro | `LOW` | `LOW` | Live Verified |
| `tools/phase3_experiment_runner.py` | Reconciled E0–E9 experiment runner for Cluj benchmark | `CASE_STUDY` | Demonstrator Runner | `CASE_STUDY / Cluj–USAMV` | Active Production | `WRAP` | stratum_ro, engine | `HIGH` | `HIGH` | Executed & Verified |
| `tools/run_closed_loop.py` | CLI runner for continuous closed-loop development cycle | `WORKFLOW` | Development Tooling | `WORKFLOW / Scripts` | Active Production | `KEEP` | stratum_ro.ai.closed_loop | `LOW` | `LOW` | Executed & Verified |
| `start_platform.py` | One-command launcher for FastAPI + QGIS Bridge + Web Cockpit | `CLIENT` | Platform Launcher | `CLIENTS / Launcher` | Active Production | `KEEP` | uvicorn, socket, webbrowser | `LOW` | `LOW` | Live Verified |

---

## 5. REQUIRED DOMAIN MATRIX

Evaluates existing code modules against the 13 target geospatial specializations:
* `✓` = directly used in active code
* `~` = indirectly relevant / partial
* `○` = potentially reusable / planned interface
* `—` = unrelated / absent

| Component | Geodesy | Topography | Cadastre | Photogrammetry | LiDAR | Remote Sensing | GIS | Cartography | GNSS | 3D/BIM | Urbanism | Hydrography | Monitoring |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `vectorizer.py` | ~ | ✓ | ✓ | — | ~ | — | ✓ | ✓ | — | ~ | ✓ | — | — |
| `cad_exporter.py` | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | — | — | ~ | — | — |
| `volumetric_3d.py` | ✓ | ~ | ~ | ~ | ✓ | ~ | ✓ | ~ | — | ✓ | ✓ | — | — |
| `lidar_processor.py` | ✓ | ✓ | ~ | ~ | ✓ | ~ | ✓ | ~ | — | ✓ | ~ | — | — |
| `lidar_quality_gate.py` | ✓ | ✓ | — | — | ✓ | — | ~ | — | — | — | — | — | — |
| `ortho_extractor.py` | ✓ | ~ | ~ | ✓ | — | ✓ | ✓ | ~ | — | — | ~ | — | — |
| `vegetation_filter.py` | — | — | — | ✓ | ✓ | ✓ | ✓ | — | — | — | ~ | — | — |
| `sam2_engine.py` | — | — | ~ | ✓ | — | ✓ | ~ | — | — | — | — | — | — |
| `dataset_resolver.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | — | ~ | ~ | — | — |
| `evaluation.py` | ✓ | ✓ | ✓ | ~ | ~ | ~ | ✓ | ✓ | — | ~ | ✓ | — | ~ |
| `data_profiler.py` | ✓ | ✓ | ✓ | ~ | ~ | ~ | ✓ | ~ | — | — | ~ | — | — |
| `provenance.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stratum_ro_dockwidget.py`| ✓ | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | — | ✓ | ✓ | — | — |
| `api/app.py` | ✓ | ~ | ✓ | ~ | ~ | ~ | ✓ | ~ | — | ~ | ~ | — | — |
| `mcp/stratumro_server.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — |

---

## 6. REQUIRED CAPABILITY MATRIX

| Capability | Current Implementation | Architectural Layer | Reusable? | Domain-Specific? | Case-Specific? | AI? | Deterministic? | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **CRS Transformation** | `api/service.py`, `pyproj` (EPSG:3844 <-> EPSG:4326) | `CORE / CRS` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |
| **LiDAR Height Normalization** | `lidar_processor.py` (laspy DTM ground subtraction) | `DOMAIN / LiDAR` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **Optical Building Segmentation**| `sam2_engine.py` + `onnx_engine.py` (Hiera Tiny ONNX) | `AI / vision` | **YES** | NO | NO | **YES** | NO | `OPERATIONAL` |
| **Optical Greenness Index** | `vegetation_filter.py` (Excess Green ExG formula) | `DOMAIN / Remote Sensing` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **90° CAD Orthogonalization** | `vectorizer.py` (collinear edge snapping, 90° angle fit)| `DOMAIN / Cadastre & Geom`| **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **Adaptive Eave Retraction** | `vectorizer.py` (`apply_eave_offset` buffer formula) | `DOMAIN / Cadastre` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **Planar Cadastral Partitioning**| `vectorizer.py` (`create_planar_partition` gap/overlap) | `DOMAIN / Cadastre` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **TopoLT CAD Deliverables** | `cad_exporter.py` (DXF `1CC`, `2CC`, `CP`, `VARFURI`, `.CP`) | `DOMAIN / Cadastre` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **Automated PAD Table** | `cad_exporter.py` (Ordinul 600/2023 inventory coordinate table)| `DOMAIN / Cadastre` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **True 3D LoD1 Solid Shell** | `volumetric_3d.py` (`MultiPolygonZ` GPKG + CityJSON v1.1)| `DOMAIN / 3D & City` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **RANSAC Roof Plane Fitting** | `volumetric_3d.py` (3D LiDAR point plane segmentation) | `DOMAIN / 3D & City` | **YES** | **YES** | NO | NO | **YES** | `OPERATIONAL` |
| **Geodetic Polygon Evaluation** | `engine/evaluation.py` (IoU, Hausdorff, Boundary RMSE, Wilson)| `CORE / validation` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |
| **L0–L5 Validation Profiler** | `ai/data_profiler.py` (spatial consistency & agreement) | `CORE / validation` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |
| **Immutable Lineage & Provenance**| `ai/provenance.py` (DAG tracking 8 evidence classes) | `CORE / provenance` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |
| **Least-Privilege Risk Engine**| `ai/risk.py` (ground truth protection, secret redaction) | `CORE / governance` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |
| **Geometric Stress Simulation** | `simulation/perturbation.py` (jitter, rotation, scale) | `CORE / simulation` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |
| **Multimodal Vision Inspection**| `ai/vlm_verifier.py` (NVIDIA NIM Llama 3.2 11B Vision) | `AI / vision` | **YES** | NO | NO | **YES** | NO | `OPERATIONAL` |
| **Adversarial Code Review** | `ai/closed_loop.py` (OpenRouter Llama 3.3 70B Kilo) | `CORE / workflow` | **YES** | NO | NO | **YES** | NO | `OPERATIONAL` |
| **QGIS Live TCP Socket Bridge** | `api/service.py` (TCP port 9876 framed wire protocol) | `CLIENTS / QGIS` | **YES** | NO | NO | NO | **YES** | `OPERATIONAL` |

---

## 7. REQUIRED WORKFLOW MATRIX

| Workflow Pipeline | Inputs | Outputs | Primary Domains | AI Components | Deterministic Components | Validation Standard | Uncertainty Model | Human Sign-Off | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **Cluj–USAMV Benchmark (E0–E9)** | Ortho (0.20m), LiDAR (LAZ), DTM (3m), Ground Truth | GeoJSON, GPKG, Metrics JSON, Visual Evidence | Photogrammetry, LiDAR, Cadastre, RS | SAM 2, Prompt Gen, Mask Fusion | ExG, nDSM, 90° Regularize, TopoLT | IoU, Hausdorff, Boundary RMSE | Wilson Score 95% CI | Required | `REPRODUCED` |
| **Assisted Pre-Cadastre (Ord. 600)** | AOI polygon, Orthophoto, LiDAR nDSM | TopoLT DXF, `.CP` file, PAD Table, GPKG | Cadastre, Topography, Geodesy | SAM 2 candidate delineation | 90° regularize, eave offset, PAD table | L0–L4 Geodetic Profiler | Residual RMSE (cm) | **MANDATORY** | `OPERATIONAL` |
| **LiDAR Feature Extraction** | Airborne LAS/LAZ point cloud | DTM raster, nDSM raster, Building Height Mask | LiDAR, Geodesy | None (pure math) | Ground classification, IDW / TIN interp | ASPRS Vertical Error | Grid cell $\sigma_z$ | Optional | `OPERATIONAL` |
| **Urban 3D LoD1 Extrusion** | Building 2D footprints, LiDAR nDSM | CityJSON v1.1, `MultiPolygonZ` GPKG, OBJ | 3D / BIM, Urbanism, LiDAR | None (pure math) | 90th percentile height, RANSAC planes | OGC CityJSON Schema | RANSAC residual | Optional | `OPERATIONAL` |
| **Discrepancy & Anomaly Audit**| AI Building Candidates, Official ANCPI Cadastre | Discrepancy Map, Hausdorff Residuals, Report | Cadastre, Cartography, QA/QC | Llama 3.2 Vision anomaly check | Hausdorff distance, symmetric difference | PASCAL VOC IoU $\ge 0.50$ | Matching confidence | Required | `OPERATIONAL` |
| **Closed-Loop Development Cycle**| Code diff, Test suite results, QGIS socket probe | Milestone Report, Kilo Review Markdown | System Governance | Llama 3.3 70B Kilo, NIM Vision | 214 Unit tests, TCP wire protocol | AGENTS.md 8 Scientific Rules | Pass / Fail binary | **MANDATORY** | `OPERATIONAL` |

---

## 8. REQUIRED EXECUTION-MODE MATRIX

Assesses current implementation capability across the 3 target execution modes:
* `✓` = fully implemented and operational
* `~` = partially implemented / requires manual trigger
* `—` = absent / unsupported

| Capability Subsystem | Human Only Mode | Hybrid (Human + AI) Mode | Autonomous AI Mode | Current Operating Reality |
| :--- | :---: | :---: | :---: | :--- |
| **Data Ingestion** | `✓` | `✓` | `~` | User or script selects input paths; auto-resolution via `dataset_resolver.py`. |
| **CRS Transformation** | `✓` | `✓` | `✓` | Strictly deterministic PROJ transformations (EPSG:3844 <-> EPSG:4326). Autonomous valid. |
| **Raster Processing** | `✓` | `✓` | `~` | Windowed chip slicing and ExG calculation run deterministically via parameters. |
| **LiDAR Processing** | `✓` | `✓` | `~` | Laspy ground filtering and nDSM rasterization run deterministically. |
| **Building Segmentation**| `—` | `✓` | `~` | SAM 2 requires bounding box or grid prompts generated from nDSM height. |
| **Geometry Regularization**| `✓` | `✓` | `✓` | Deterministic 90° snapping and minimum bounding rectangle algorithms. |
| **Validation & Profiling**| `✓` | `✓` | `✓` | L0–L4 profiling and geodetic metrics evaluate autonomously without human prompting. |
| **CAD / PAD Export** | `✓` | `✓` | `—` | TopoLT layers and PAD tables generate deterministically; **Legal sign-off requires licensed surveyor**. |
| **Workflow Planning** | `✓` | `~` | `~` | TaskGraph and TaskSpec support programmatic dependency walk; dynamic LLM planning guarded. |

---

## 9. CLUJ–USAMV DEMONSTRATOR MATRIX & DATA LINEAGE

### A. Cluj–USAMV Component Breakdown
| Asset / Component | Physical Location | Function in Demonstrator | Generalizable? | Target Architectural Layer | Migration Action |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Airborne LiDAR LAZ** | `Z_VladP\...\NorPuncte_St70_S42.laz` | Raw point cloud (Stereo 70) | **YES** | `DATA / Cluj–USAMV` | `KEEP` |
| **Digital Terrain Model (DTM)**| `Z_VladP\...\DTM3m\DTM3m.tif` | Bare-earth elevation raster | **YES** | `DATA / Cluj–USAMV` | `KEEP` |
| **Orthophoto Mosaic** | `workspace/output/ortofoto_cluj_usamv_rgb.vrt` | 0.20m GSD RGB optical raster | **YES** | `DATA / Cluj–USAMV` | `KEEP` |
| **Normalized DSM (nDSM)** | `workspace/derived/cluj_ndsm_1m.tif` | 1.0m above-ground height raster | **YES** | `DATA / Cluj–USAMV / Derived` | `KEEP` |
| **Tier 1 Ground Truth** | `data/ground_truth/tier1_teren.geojson` | 29 official surveyed buildings | NO | `DATA / Reference / Tier 1` | `KEEP (FROZEN)` |
| **Cluj Benchmark (150 Bldgs)**| `data/ground_truth/cluj_combined_unique_150.geojson`| 150 unique reference buildings | NO | `DATA / Reference / Tier 2` | `KEEP (FROZEN)` |
| **Phase 3 Experiment Runner** | `tools/phase3_experiment_runner.py` | Runs E0 to E9 ablation cycles | **YES** | `CASE_STUDY / Cluj–USAMV` | `WRAP` |
| **Desktop Operator** | `tools/run_e2e_desktop_operator.py` | End-to-end QGIS live automation | **YES** | `CASE_STUDY / Cluj–USAMV` | `WRAP` |
| **Spectator QGIS Projects** | `StratumRO_Inspectie_Vizuala.qgz` | Pre-styled visual verification canvas | NO | `CASE_STUDY / Cluj–USAMV / QGIS` | `KEEP` |
| **E2E Evidence Deliverables** | `workspace/e2e/evidence/` | PNG canvas screenshots and logs | NO | `CASE_STUDY / Cluj–USAMV / Outputs`| `ARCHIVE` |

### B. End-to-End Cluj Data Lineage Flow
```text
[RAW SENSORS]
├── Orthophoto RGB (0.20m GSD) ────────┐
└── Airborne LiDAR LAZ (Class 2/6) ──┐ │
                                     │ │
[DERIVED DATA PREPARATION]          │ │
├── DTM Interpolation (IDW/TIN) <────┘ │  (stratum_ro/lidar_processor.py)
├── nDSM Generation (DSM - DTM) ───────┤  (stratum_ro/lidar_processor.py)
├── Optical Vegetation Index (ExG) <───┘  (stratum_ro/vegetation_filter.py)
│
[AI & COMPUTER VISION]
├── nDSM Prompts (Box & Grid) ─────────┐  (stratum_ro/prompt_generator.py)
├── SAM 2 Hiera Segmentation <─────────┤  (stratum_ro/sam2_engine.py / onnx_engine.py)
├── Morphological Closing (5x5) <──────┤  (stratum_ro/candidate_generator.py)
└── Multi-Scale Adjacency Fusion <─────┘  (stratum_ro/mask_fusion.py)
│
[DETERMINISTIC GEOMETRIC PROCESSING]
├── Vectorization & RDP Simplification ┐  (stratum_ro/geometric_reconstruction_v2.py)
├── Principal Facade 90° Snapping ─────┤  (stratum_ro/orientation_regularizer.py)
├── Adaptive Eave Retraction (-0.4m) ──┤  (stratum_ro/vectorizer.py)
└── Planar Partitioning (Zero Overlap) ┘  (stratum_ro/vectorizer.py)
│
[EVALUATION & VALIDATION]
├── L0-L4 Data Profiler Check ─────────┐  (stratum_ro/ai/data_profiler.py)
├── Ground Truth Comparison (IoU, RMSE)┤  (engine/evaluation.py)
└── Visual Inspection (Llama 3.2 Vision)  (stratum_ro/ai/vlm_verifier.py)
│
[DELIVERABLES GENERATION]
├── TopoLT CAD DWG/DXF (1CC, 2CC, CP) ──┐ (stratum_ro/cad_exporter.py)
├── ANCPI Coordinate Table (PAD) ──────┤ (stratum_ro/cad_exporter.py)
├── Official Interchange File (.CP) ────┤ (stratum_ro/cad_exporter.py)
└── OGC CityJSON v1.1 3D LoD1 Solid ───┘ (stratum_ro/volumetric_3d.py)
```

---

## 10. PRIORITIZED PROBLEM LIST

### P0 — Blocking Architecture / Scientific Issues
1. **Recall Bottleneck in Complex Canopies (6.15%)**: In the reconciled E9 benchmark on Cluj, 4 true physical buildings are detected out of 65 reference structures. The current prompt generation and vegetation thresholding filter out occluded structures.
2. **Hardcoded User Windows Paths**: [`dataset_resolver.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/dataset_resolver.py) and [`config.yaml`](file:///c:/Users/lefpa/Downloads/QGIS-AI/config.yaml) contain literal paths (`C:\Users\lefpa\Desktop\date\Z_VladP\...`). On any other machine or CI runner without these exact files, resolution falls back or fails.
3. **Monolithic PyQGIS DockWidget (1300 lines)**: [`stratum_ro_dockwidget.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/stratum_ro_dockwidget.py) mixes UI controls, background QThread management, raw socket communication, and business logic into a single class.

### P1 — High-Priority Architecture Problems
1. **Coupling in `vectorizer.py`**: Generic geometric operations (minimum bounding rectangle, Ramer-Douglas-Peucker simplification, polygon union) are entangled with Romanian cadastral business rules (`1CC`, `2CC`, roof-to-foundation eave buffer offsets).
2. **PyQGIS Import Guards in Test Suite**: 9 unit tests skip in standard Python environments because they import GUI elements directly rather than mocking QGIS interfaces.
3. **Formal Domain Pack Interfaces**: Domain algorithms (LiDAR ground filtering, ANCPI cadastre, CityJSON 3D) are grouped under the single `stratum_ro/` flat package rather than modular domain packages.

### P2 — Important Cleanup
1. **Transient Files in `scratch/`**: 12 experimental scripts exist in `scratch/` that should be cataloged or archived.
2. **Redundant Visualization Tools**: Multiple tools in `tools/` (`update_dual_product_viewer.py`, `build_clean_dual_viewer.py`, `update_hybrid_viewer.py`) perform overlapping HTML/Leaflet generation and should be unified.

### P3 — Optional Improvements
1. **3D Web Viewer Integration**: Integration of Three.js or Cesium in the Web Cockpit for interactive 3D LoD1 CityJSON rotation.
2. **Additional Local AI Providers**: Connecting Ollama or local Llama.cpp when GPU hardware permits.

---

## 11. MISSING-CAPABILITY LIST (TARGET VS REALITY)

| Target Architecture Capability | Target Layer | Current State | Missing Scope |
| :--- | :--- | :---: | :--- |
| **Universal Geospatial Data Model (Common Geo Object)** | `CORE / data` | `PARTIAL` | Features currently passed as raw Shapely dicts / GeoPandas DataFrames. Needs unified Typed Dataset interface. |
| **Geodesy & Coordinate Transformations** | `CORE / CRS` | `OPERATIONAL` | Stereo 70 (`EPSG:3844`), WGS84 (`EPSG:4326`), Marea Neagră 1975 (`EPSG:5781`) active and tested. |
| **Statistical & Measurement Uncertainty** | `CORE / uncertainty`| `PARTIAL` | Wilson score confidence intervals and RMSE implemented; covariance propagation across Helmert transforms missing. |
| **Sensor Simulation Framework** | `CORE / simulation` | `PARTIAL` | `PerturbationEngine` (translation, rotation, scale, jitter) operational; full synthetic LiDAR sensor beam simulation missing. |
| **Domain Pack Contract (BaseDomainPack)** | `DOMAIN / Base` | `ABSENT` | Domain logic currently exposed as flat functions rather than pluggable, discoverable Domain Packs. |
| **Autonomous Workflow Planner** | `AI / agents` | `PARTIAL` | Static `TaskGraph` and `TaskSpec` operational; dynamic heuristic planning with human approval gate partial. |
| **Multi-Client API Gateway** | `CLIENTS / API` | `OPERATIONAL` | FastAPI backend operational with REST, SSE streams, and QGIS live socket bridge. |
