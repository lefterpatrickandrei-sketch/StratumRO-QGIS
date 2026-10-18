# STRATUMRO — PRODUCT ARCHITECTURE SPECIFICATION
**Authoritative Architectural Specification for the StratumRO Scientific & Geospatial Platform**  
*Document Version: 1.0.0 — Established under Master Reorientation Governance*

---

## 1. Executive Identity & Purpose

**StratumRO** is an industrial-grade geomatics, remote sensing, and MLOps platform engineered specifically for Romanian pre-cadastral digitization and spatial deliverable generation. It operates strictly under the legal and technical requirements of **ANCPI Ordinul nr. 600/2023**, TopoLT drafting standards, and the Romanian National Projection System (**Stereo 70, EPSG:3844**).

### Defensible Scientific & Legal Positioning
- **Assisted Pre-Cadastral Workflow (Human-in-the-Loop):** StratumRO accelerates manual cadastral footprint digitization and 3D modeling by ~89%. It generates high-precision candidate footprints and technical deliverables.
- **NOT an Autonomous Legal Registration System:** StratumRO does NOT grant autonomous legal certification. Generating valid CAD layers (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`), PAD tables, and `.CP` files does not substitute for the legally mandated field verification, signature, and stamp of a licensed geodetic surveyor (*persoană autorizată ANCPI* conform Legii cadastrului și publicității imobiliare nr. 7/1996).

### Autonomous Runtime Guarantee
StratumRO Product is an independent scientific software platform. It is fully decoupled from the development infrastructure:
- **Product runs independently** of the Antigravity IDE, agentic coding environments, and Dev SDK orchestrators.
- **Product never imports** Dev SDK packages, coding LLMs, or agent development frameworks.
- **Product Core runs 100% locally and deterministically** without requiring any external cloud AI API keys.

---

## 2. High-Level Product Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             STRATUMRO CLIENT PLANE                               │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌──────────────────────┐  │
│  │   QGIS Desktop GUI    │  │ QGIS Processing Model │  │ CLI Pipeline Runner  │  │
│  │  (DockWidget / PyQGIS)│  │ (Cadastral Algorithm) │  │ (Headless / Batch)   │  │
│  └───────────┬───────────┘  └───────────┬───────────┘  └──────────┬───────────┘  │
└──────────────┼──────────────────────────┼─────────────────────────┼──────────────┘
               ▼                          ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW & EXECUTION PLANE                               │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │ Capability Matcher & TaskSpec Engine (Closed-Loop Deterministic Execution) │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────┬────────────────────────────────────┬──────────────────────┘
                       │                                    │
        ┌──────────────┴─────────────┐        ┌─────────────┴──────────────┐
        ▼                            ▼        ▼                            ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌────────────────┐
│       SCIENTIFIC CORE        │ │       GEOSPATIAL CORE        │ │   AI RUNTIME   │
│  • EPSG:3844 Stereo 70 Math  │ │  • Raster VRT / Slicing      │ │  • SAM2 Hiera  │
│  • 90° CAD Orthogonalization │ │  • LiDAR LAS/LAZ Point Cloud │ │  • ONNX DirectML│
│  • Canonical 4-Vertex Fitting│ │  • Planar Partitioning (GEOS)│ │  • CV Engine   │
│  • ANCPI Geodetic Tolerances │ │  • Spatial Indexing (R-tree) │ │  (Ollama: NONE)│
└──────────────┬───────────────┘ └──────────────┬───────────────┘ └────────┬───────┘
               │                                │                          │
               └───────────────────────┬────────┴──────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            DOMAIN SPECIALIZATION PACKS                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Cadastre RO  │  │   LiDAR 3D   │  │  City 3D     │  │ Computer Vis │  ...     │
│  │ (ANCPI 600,  │  │ (nDSM 1m,    │  │ (LoD1 Shell, │  │ (Candidate   │          │
│  │  TopoLT CAD) │  │  QualityGate)│  │  CityJSON)   │  │  Prompting)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION, QA & PROVENANCE                              │
│  ┌───────────────────────────────┐        ┌───────────────────────────────────┐  │
│  │     RiskEngine & QualityGate  │        │       Scientific Provenance       │  │
│  │ • 5-Factor Confidence Score   │        │ • Dataset -> Params -> Model ->   │  │
│  │ • Topology & Geometric Audit  │        │   Output -> Validation (SHA-256)  │  │
│  └───────────────────────────────┘        └───────────────────────────────────┘  │
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           DELIVERABLES & EXPORTS                                 │
│    • TopoLT DXF (1CC, 2CC, CP, VARFURI, NUMERE_PCT, TABEL_PAD)                   │
│    • Official ANCPI .CP Point Interchange File                                   │
│    • OGC CityJSON v1.1 (LoD1 3D MultiPolygonZ)                                   │
│    • Multi-layer GeoPackage (EPSG:3844)                                          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Breakdown

### 3.1. Scientific Core (`stratum_ro/core/`)
The Scientific Core is the mathematical bedrock of StratumRO. It enforces the **Deterministic Geomatics Invariant**:
- **Zero LLM Hallucinations:** All coordinate transformations, geometric simplifications, 90° angle regularizations, and PAD coordinate tables are computed exclusively via deterministic local Python/GEOS/GDAL math. No generative language model is ever permitted in the coordinate pathway.
- **Sub-modules:**
  - `core.geodesy`: Strict EPSG:3844 (Pulkovo 1942(58) / Stereo 70) validation, metric units, Krasovsky 1940 ellipsoid parameters, 2D conformal Helmert transformations.
  - `core.geometry`: 90° CAD orthogonalization, minimum bounding rectangle fitting, eave retraction offsets, polygon area/perimeter computation, topology cleaning (snapping, sliver removal, hole closure).
  - `core.qa_qc`: Geodetic validation rules, vertex density limits, minimum area constraints ($A \ge 8.0\,\text{m}^2$), self-intersection detection.

### 3.2. Geospatial Core
Provides hardware-efficient raster and point cloud primitives:
- `core.raster`: High-performance windowed reads of large orthophotos via `rasterio` and GDAL VRTs. Coordinate geotransforms and affine math.
- `core.pointcloud`: Airborne LiDAR ingestion via `laspy`, ground classification filtering (ASPRS class 2 vs 6), and normalized Digital Surface Model (nDSM) rasterization at 1.0m resolution.

### 3.3. Domain Specialization Packs (`stratum_ro/domain/` or root domain modules)
Domain logic is organized into specialized, decoupled capability units. Following the **Roadmap $\neq$ Code Directory** rule (§17), only mature domains with real code, real data, and real tests exist:

1. **`cadastre_ro` (Mature):**
   - **ANCPI Ordinul 600/2023:** Legal classification of constructions (C1 Clădire Principală, C2 Anexă Gospodărească).
   - **TopoLT Standard CAD Layers:** Strict AutoCAD layer structure with standard color indices:
     - `1CC` (Red, Color 1): Main residential / commercial buildings.
     - `2CC` (Yellow, Color 2): Outbuildings, garages, sheds.
     - `CP` (Green, Color 3): Property boundary / cadastral parcel limit.
     - `VARFURI` (Cyan, Color 4): Individual boundary point nodes.
     - `NUMERE_PCT` (Yellow, Color 2 / White): Sequential clockwise vertex numbering (1..N).
     - `TABEL_PAD` (White, Color 7): Fully drafted Plan de Amplasament și Delimitare (PAD) coordinate inventory table with X (North), Y (East), and segment lengths $D(i, i+1)$.
     - `TEXTE` (White, Color 7): Footprint codes and surface annotations (e.g., `C1`, `Sc=142.50 mp`).
   - **`.CP` Exchange File:** Official ANCPI ASCII point interchange file generator.
   - **Strict Physical Rule:** Zero trees on building roofs. Spatial exclusion buffer (0.8m) eliminating vegetation artifacts.

2. **`city_3d` (Mature):**
   - **LoD1 Extrusion:** Height-driven extrusion of 2D regularized footprints using nDSM statistics ($Z_{\text{ground}}$ from DTM, $Z_{\text{eave}} = \text{median}(H)$, $Z_{\text{ridge}} = \text{percentile}_{95}(H)$).
   - **OGC CityJSON v1.1:** Standards-compliant CityJSON export for municipal GIS.
   - **GeoPackage MultiPolygonZ:** True 3D closed solid shell geometries.
   - **RANSAC Roof Plane Fitting:** Deterministic 3D planar segmentation of complex roof structures.

3. **`lidar` (Mature):**
   - **LiDAR Processing:** End-to-end pipeline converting raw airborne point clouds (`.laz`/`.las`) to 1.0m nDSM GeoTIFFs.
   - **`LidarQualityGate` Active 3D Auditor:** Multi-factor confidence validator evaluating:
     - Transversal facade height drop ($\Delta Z \ge 1.8\,\text{m}$).
     - Roof elevation dispersion ($\sigma_{\text{roof}} \le 1.2\,\text{m}$).
     - Overhanging canopy detection.
     - 5-factor composite confidence score ($0.0 \dots 1.0$) with operational traffic-light thresholds:
       - 🟢 **VERDE ($\ge 0.85$):** Auto-admitted to pre-cadastral review.
       - 🟡 **GALBEN ($0.65 - 0.85$):** Flagged for manual surveyor inspection (calcan, complex roof).
       - 🔴 **ROȘU ($< 0.65$):** Rejected artifact (bushes, tall vehicles, terrain noise).

4. **`vision` (Mature):**
   - **SAM2 Hiera Segmentation:** Deep learning foundation vision model generating binary building masks from point prompts.
   - **LiDAR-Prompted Candidate Generation:** Automated prompt generation placing foreground positive clicks on nDSM local elevation maxima ($H \ge 2.5\,\text{m}$).
   - **Multimodal Mask Fusion:** Intersection and majority voting combining SAM2 optical boundaries with LiDAR height boundaries.
   - **NDVI & Vegetation Filtering:** Elimination of false positives caused by dense tree crowns.

5. **`topography` (Partial):**
   - Deterministic 3x3 Horn finite-difference slope and aspect calculation from DTM/nDSM.

### 3.4. AI Runtime Architecture
The AI Runtime within StratumRO Product is strictly specialized for **geospatial computer vision and automated quality estimation**:
- **Computer Vision Runtime:** Meta SAM 2 Hiera executed via ONNX Runtime with DirectML hardware acceleration on Windows, falling back to multithreaded CPU inference.
- **Decoupled from Coding LLMs:** Coding models (Anthropic, OpenAI, OpenRouter) are NEVER runtime dependencies of StratumRO Product.
- **Strict Ollama Exclusion (§13, §80):** Ollama is permanently excluded from StratumRO Product. It is not an active provider, not a fallback, and not a supported daemon.
- **Runtime VLM Verification:** Optional multimodal visual inspection using cloud VLM (e.g. NVIDIA NIM `meta/llama-3.2-11b-vision-instruct`) for automated anomaly tagging. If offline, the runtime operates seamlessly via deterministic local validation gates.

### 3.5. Scientific Provenance Engine
Scientific provenance tracks the full physical and mathematical lineage of every output feature:
$$\text{Lineage} = \{\text{Dataset Hashing}\} \xrightarrow{\text{Params}} \{\text{Algorithm}\} \xrightarrow{\text{Model Weights}} \{\text{Output Geometries}\} \xrightarrow{\text{Tolerance Audit}} \{\text{Deliverable}\}$$
- Every generated DXF, GeoPackage layer, and CityJSON file includes cryptographic metadata recording:
  - Input orthophoto and LiDAR file SHA-256 hashes.
  - Coordinate reference system validation (`EPSG:3844`).
  - Regularization parameters and tolerances used.
  - Quality score distribution and surveyor inspection status.

### 3.6. Product Data & Benchmark Demonstrator
- **Cluj-USAMV Benchmark (§18):** Serves as the canonical multi-domain integrated benchmark demonstrator (10cm GSD orthophoto, 1m nDSM LiDAR, 150 ground-truth cadastral reference buildings). It is Product Scientific Data, not Dev SDK property.
- **Ground Truth Cadastral References:** `tier1_teren.geojson` (29 real cadastral buildings in Stereo 70) and `cluj_combined_unique_150.geojson`.

### 3.7. Product Clients
1. **QGIS Desktop Plugin:** Standard PyQGIS dockwidget (`StratumRODockWidget`) and interactive canvas canvas tools.
2. **QGIS Processing Algorithm:** `StratumROCadastralAlgorithm` registered in the QGIS Processing Toolbox for batch modeling.
3. **Headless CLI:** `scripts/run_pipeline.py` for headless batch processing.

---

## 4. Product Invariants (Non-Negotiable)

1. **Deterministic Geometry:** No LLM is ever used to invent or modify geodetic coordinates.
2. **Stereo 70 Strictness:** Coordinates must conform to EPSG:3844; invalid coordinate ranges are rejected at the gate.
3. **TopoLT Layer Integrity:** CAD files must contain valid `1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`, and `TABEL_PAD` layers.
4. **Human-in-the-Loop Sign-off:** All outputs are pre-cadastral candidates requiring licensed surveyor sign-off.
5. **Air-Gapped Operational Capability:** The core product operates 100% offline without internet access.
