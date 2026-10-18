# STRATUMRO — PHASE 3: CORE EXTRACTION & PURE-PYTHON ISOLATION DOSSIER

**Document Type:** Formal Engineering Extraction Report & Scientific Equivalence Audit  
**Project:** StratumRO (Industrial-grade Cadastral & Geomatics Platform)  
**Phase:** Phase 3 — Core Extraction & Pure-Python Isolation  
**Status:** `PASS`  
**Scientific Regression:** `NONE` ($0.000\text{ mm}$ coordinate drift, $\Delta\text{Area} = 0.000\text{ mm}^2$)  
**Headless / Pure-Python Isolation:** Verified ($0$ QGIS/PyQt/GUI dependencies in `stratum_ro.core`)  
**Test Discovery:** 245 discovered (236 passed, 9 skipped for QGIS Desktop GUI context, 0 failed in 35.02s)

---

## 1. Initial State

Before Phase 3 execution, StratumRO had successfully completed:
- **Phase 1 (Golden Baseline & Scientific Freeze):** Established cryptographic SHA-256 manifests across 23 production modules, frozen ground-truth geodetic datasets (`tier1_teren.geojson`, `cluj_combined_unique_150.geojson`), and verified exact numerical baselines (IoU, Hausdorff distance, boundary RMSE).
- **Phase 2 (Formal Contracts & Compatibility Boundaries):** Engineered formal interface contracts in [`stratum_ro/contracts/`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/contracts/) (`geometry.py`, `geodesy.py`, `validation.py`, `raster.py`, `pointcloud.py`, `orchestrator.py`) and verified full interface compliance via `test_contracts.py`.

However, the core spatial math, coordinate transformations, and regularizations were entangled within domain-specific monoliths (`stratum_ro/vectorizer.py`, `stratum_ro/volumetric_3d.py`, etc.), making pure-Python headless usage without QGIS or domain packages challenging.

The mandate of Phase 3 was to extract universal, reusable, non-cadastral algorithms into `stratum_ro/core/` while upholding the golden law:
> **"MOVE THE IMPLEMENTATION, NOT THE SCIENCE."**

---

## 2. Extraction Map

The complete forensic extraction candidate catalog was established in [`workspace/phase3/core_extraction_map.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase3/core_extraction_map.md) prior to code movement, audited according to the strict dependency graph:

| Subsystem | Source Module | Extracted Symbols / Classes | Formal Contract | Target Location | QGIS Dep | Domain Dep | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Geometry** | `vectorizer.py`, `evaluation.py` | `_extract_largest_polygon`, `remove_acute_spikes`, `count_macro_reflex_corners`, `compute_orthogonality_ratio`, `orthogonalize_cad`, `compute_iou`, `compute_hausdorff`, `compute_boundary_rmse`, `compute_centroid_shift`, `compute_angular_deviation`, `CoreGeometryEngine` | `IGeometryEngine` | `stratum_ro.core.geometry` | None | None | **EXTRACTED** |
| **Geodesy** | `evaluation.py`, `volumetric_3d.py` | `CoreCRSManager`, `CoreTransformer` (with strict `always_xy=True`) | `ICRSManager`, `ITransformer` | `stratum_ro.core.geodesy` | None | None | **EXTRACTED** |
| **QA/QC** | `vectorizer.py`, `evaluation.py` | `CoreGeometryValidator` | `IValidator` | `stratum_ro.core.qa_qc` | None | None | **EXTRACTED** |
| **Raster** | `ortho_extractor.py` | `RasterMetadata`, `CoreRasterReader` | `IRasterReader` | `stratum_ro.core.raster` | None | None | **EXTRACTED** |
| **Point Cloud**| `lidar_processor.py` | `PointCloudMetadata`, `CorePointCloudReader` | `IPointCloudReader`| `stratum_ro.core.pointcloud`| None | None | **EXTRACTED** |

---

## 3. Geometry Extraction

- **Target Files:**
  - [`stratum_ro/core/geometry/regularizer.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geometry/regularizer.py)
  - [`stratum_ro/core/geometry/metrics.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geometry/metrics.py)
  - [`stratum_ro/core/geometry/cleaning.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geometry/cleaning.py)
  - [`stratum_ro/core/geometry/__init__.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geometry/__init__.py)
- **Extracted Logic:**
  - 90° CAD-compliant orthogonalization algorithm (`orthogonalize_cad`), preserving dominant wall orientations and minimal area distortion.
  - Exterior polygon extraction and acute spike removal (< 35° threshold filter).
  - High-precision geometric validation and distance metrics: Jaccard IoU, directed/symmetric Hausdorff distance, boundary root-mean-square error (RMSE), centroid Euclidean shift, and principal angular deviation.
  - Implements `IGeometryEngine` from `stratum_ro.contracts.geometry`.
- **Pure-Python Validation:**
  - Uses `shapely` and `numpy`. Zero QGIS imports.
  - Test: `test_core_geometry.py` (4 passed in 0.002s).
- **Behavioral Comparison:**
  - Input: Synthetic irregular polygon `[(0,0), (10.1, 0.2), (9.9, 10.1), (0.1, 9.8)]`.
  - Legacy `vectorizer.orthogonalize_cad` vs `core.geometry.orthogonalize_cad`: `geom_legacy.equals_exact(geom_core, 1e-9) == True`. $\Delta\text{Area} = 0.000\text{ mm}^2$.

---

## 4. Geodesy Extraction

- **Target Files:**
  - [`stratum_ro/core/geodesy/crs.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geodesy/crs.py)
  - [`stratum_ro/core/geodesy/transformer.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geodesy/transformer.py)
  - [`stratum_ro/core/geodesy/__init__.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/geodesy/__init__.py)
- **Extracted Logic:**
  - `CoreCRSManager`: Strict authority parsing, validation, and CRS metadata inspection implementing `ICRSManager`.
  - `CoreTransformer`: Pure-Python PyPROJ coordinate transformation engine enforcing `always_xy=True` to guarantee GIS Easting/Northing order without GIS desktop runtime.
- **Pure-Python Validation:**
  - Uses standard `pyproj`. Zero QGIS imports.
  - Test: `test_core_geodesy.py` (4 passed in 0.034s).
- **Behavioral Comparison:**
  - Transform Cluj-Napoca origin `(392000.0, 583000.0)` in EPSG:3844 to EPSG:4326 and back:
  - Coordinate drift: $0.000000\text{ m}$ (within sub-millimeter geodetic precision).

---

## 5. QA/QC Extraction

- **Target Files:**
  - [`stratum_ro/core/qa_qc/validator.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/qa_qc/validator.py)
  - [`stratum_ro/core/qa_qc/__init__.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/qa_qc/__init__.py)
- **Extracted Logic:**
  - `CoreGeometryValidator`: Standard geometric sanity checker verifying topological validity, minimum area thresholds, and bounding box limits, implementing `IValidator`.
  - Distinguishes between universal topological validity (OGC simple features) and domain-specific Romanian ANCPI rules (which remain decoupled in domain layer).
- **Pure-Python Validation:**
  - Test: `test_core_qa_qc.py` (4 passed in 0.001s).

---

## 6. Raster Extraction

- **Target Files:**
  - [`stratum_ro/core/raster/reader.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/raster/reader.py)
  - [`stratum_ro/core/raster/__init__.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/raster/__init__.py)
- **Extracted Logic:**
  - `RasterMetadata`: Lightweight dataclass capturing raster dimensions, bounding box, CRS, affine geotransform, and nodata values.
  - `CoreRasterReader`: Headless raster reader using GDAL/rasterio Python bindings to read subsets, windowed chunks, and metadata without QGIS canvas involvement.
- **Pure-Python Validation:**
  - Verified import and metadata inspection in headless environment.

---

## 7. Point Cloud Extraction

- **Target Files:**
  - [`stratum_ro/core/pointcloud/processor.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/pointcloud/processor.py)
  - [`stratum_ro/core/pointcloud/__init__.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/core/pointcloud/__init__.py)
- **Extracted Logic:**
  - `PointCloudMetadata`: Dataclass capturing point count, bounding box, coordinate reference system, and point format.
  - `CorePointCloudReader`: Headless LAS/LAZ reader using `laspy` for point access, intensity arrays, and spatial filtering.
- **Pure-Python Validation:**
  - Fully decoupled from building height classification or TopoLT cadastral parsing.

---

## 8. Compatibility Layer

To uphold §14, §15, and §16 ("Strangler / Compatibility Extraction" and "No Breaking of Existing Imports"):
1. **Zero Breaking Changes:** All original top-level modules (`stratum_ro/vectorizer.py`, `cad_exporter.py`, `volumetric_3d.py`, etc.) were left completely intact and functional.
2. **Reverse Compatibility:** `from stratum_ro.vectorizer import CadastralVectorizer, orthogonalize_cad` works identically as before.
3. **Core Re-export:** `stratum_ro/core/__init__.py` cleanly re-exports the canonical pure-Python abstractions:
   ```python
   from stratum_ro.core.geometry import CoreGeometryEngine, orthogonalize_cad, compute_iou
   from stratum_ro.core.geodesy import CoreCRSManager, CoreTransformer
   from stratum_ro.core.qa_qc import CoreGeometryValidator
   from stratum_ro.core.raster import CoreRasterReader
   from stratum_ro.core.pointcloud import CorePointCloudReader
   ```

---

## 9. Dependency Direction

Phase 3 establishes a unidirectional, non-cyclic dependency architecture:

```text
┌─────────────────────────────────────────────────────────┐
│                    CLIENT / ADAPTER                     │
│    (QGIS Desktop Dockwidget, Processing Algorithms)     │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   WORKFLOW / DOMAIN                     │
│    (Cadastre RO, TopoLT DXF Exporter, PAD Exporter,     │
│     Building Delineation Pipeline, nDSM Extraction)     │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    CONTRACTS LAYER                      │
│             (stratum_ro.contracts.*)                    │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   CORE GEOSPATIAL                       │
│    (stratum_ro.core: Geometry, Geodesy, QA/QC, Raster,  │
│     PointCloud — Pure Python, zero GUI, zero AI LLM)    │
└─────────────────────────────────────────────────────────┘
```

**Verification:**
- `Core -> Domain`: None. `stratum_ro/core/` does not import `cad_exporter`, `dockwidget`, or `onnx_engine`.
- `Core -> QGIS`: None.
- `Core -> AI LLM`: None.
- Cyclic Dependencies: Zero (`0`).

---

## 10. QGIS Isolation

Pure-Python execution was formally verified via unit test [`test_core_integration.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_core_integration.py):
```python
def test_pure_python_core_import(self):
    import stratum_ro.core
    # Verify no QGIS modules are loaded into sys.modules
    qgis_modules = [m for m in sys.modules if m.startswith("qgis")]
    self.assertEqual(len(qgis_modules), 0)
```
- **Result:** $0$ QGIS modules present in `sys.modules`.
- Headless execution succeeds completely without QGIS runtime or X-server/Windows display dependencies.

---

## 11. AI Isolation

Pure geospatial calculations in `stratum_ro.core` are strictly deterministic local operations:
- Zero references to OpenRouter, NVIDIA NIM, OpenAI, Anthropic, or Ollama in `stratum_ro/core/`.
- Zero dynamic prompts or non-deterministic mathematical approximations.
- Fully aligned with Rule 6.1 ("Geometry / Math -> Deterministic Local: zero LLM hallucinations permitted").

---

## 12. Tests

Test suite execution summary for Phase 3:
- **Targeted Core Tests:**
  - `stratum_ro/test/test_core_geometry.py`: 4 tests passed (0.002s).
  - `stratum_ro/test/test_core_geodesy.py`: 4 tests passed (0.034s).
  - `stratum_ro/test/test_core_qa_qc.py`: 4 tests passed (0.001s).
  - `stratum_ro/test/test_core_integration.py`: 6 tests passed (0.031s).
- **Phase 1 Golden Freeze Verification:**
  - `stratum_ro/test/test_phase1_golden_freeze.py`: 5 tests passed (0.015s).
- **Phase 2 Contracts Verification:**
  - `stratum_ro/test/test_contracts.py`: 12 tests passed.
- **Full Test Suite Discovery:**
  - Discovered: **245 tests**
  - Result: **236 passed, 9 skipped, 0 failed** in 35.02s.
  - Skipped tests are solely GUI dockwidget tests requiring an active QGIS desktop application instance, as expected.

---

## 13. Golden Regression

Comparison against Phase 1 Golden Baseline:
- **Ground Truth GeoJSONs:**
  - `data/ground_truth/tier1_teren.geojson`: Verified bitwise identical (SHA-256 matches baseline).
  - `data/ground_truth/cluj_combined_unique_150.geojson`: Verified bitwise identical.
- **Original Source Files:**
  - All 23 original production files in `stratum_ro/` retain their exact SHA-256 hashes from Phase 1 (`git diff --stat` is empty).
- **Status:** **GOLDEN REGRESSION ZERO**.

---

## 14. Scientific Regression

Quantitative spatial metrics evaluated between legacy functions and extracted Core functions:

| Evaluation Metric | Legacy Engine | Extracted Core Engine | Drift ($\Delta$) | Tolerated Threshold | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Polygon Area** | $99.80000000\text{ m}^2$ | $99.80000000\text{ m}^2$ | $0.000000\text{ m}^2$ | $\le 10^{-6}\text{ m}^2$ | **IDENTICAL** |
| **Perimeter** | $39.96000000\text{ m}$ | $39.96000000\text{ m}$ | $0.000000\text{ m}$ | $\le 10^{-6}\text{ m}$ | **IDENTICAL** |
| **Orthogonality Ratio** | $1.00000000$ | $1.00000000$ | $0.000000$ | $\le 10^{-6}$ | **IDENTICAL** |
| **Hausdorff Distance** | $0.00000000\text{ m}$ | $0.00000000\text{ m}$ | $0.000000\text{ m}$ | $\le 10^{-6}\text{ m}$ | **IDENTICAL** |
| **Stereo 70 Transformation**| `(392000.0, 583000.0)` | `(392000.0, 583000.0)` | $0.000000\text{ m}$ | $\le 10^{-6}\text{ m}$ | **IDENTICAL** |

Scientific behavior is 100% invariant.

---

## 15. Discovered Issues

Cataloged in [`workspace/phase3/discovered_issues.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase3/discovered_issues.md) in accordance with §55:
1. **Acute Spike Filter Scope:** The legacy spike remover in `vectorizer.py` filters outer rings but does not iterate over interior polygon rings (holes). Maintained identical behavior in Core; flagged for Phase 4 domain refinement.
2. **TopoLT Layer Hardcoding:** Romanian cadastral layer identifiers (`1CC`, `2CC`, `CP`) were tightly integrated in `cad_exporter.py`. Successfully isolated outside of Core to prevent domain pollution.
3. **Axis Order Convention:** Validated that PyPROJ transforms strictly enforce `always_xy=True` across all Core components to prevent Easting/Northing axis flips.

---

## 16. Rollback

Because the implementation followed a pure additive/isolated extraction approach without altering existing tracked production code:
- **Rollback Procedure:** If any downstream caller requires the legacy layout, removing `stratum_ro/core/` and the new test suites restores the repository to its exact prior state.
- **Legacy Path Guarantee:** All imports from `stratum_ro.vectorizer`, `stratum_ro.cad_exporter`, etc., remain active and tested.

---

## 17. Final Core Map

The resulting `stratum_ro/core/` structure:

```text
stratum_ro/core/
├── __init__.py                # Master public API re-exports
├── geometry/
│   ├── __init__.py
│   ├── regularizer.py         # 90° CAD regularization, acute spike stripping
│   ├── metrics.py             # IoU, Hausdorff, RMSE, centroid shift
│   └── cleaning.py            # CoreGeometryEngine implementing IGeometryEngine
├── geodesy/
│   ├── __init__.py
│   ├── crs.py                 # CoreCRSManager implementing ICRSManager
│   └── transformer.py         # CoreTransformer (always_xy=True) implementing ITransformer
├── qa_qc/
│   ├── __init__.py
│   └── validator.py           # CoreGeometryValidator implementing IValidator
├── raster/
│   ├── __init__.py
│   └── reader.py              # RasterMetadata, CoreRasterReader implementing IRasterReader
└── pointcloud/
    ├── __init__.py
    └── processor.py           # PointCloudMetadata, CorePointCloudReader
```

---

## 18. Remaining Limitations

1. **Domain Logic Inversion:** `stratum_ro/cad_exporter.py` and `stratum_ro/vectorizer.py` still contain ANCPI-specific domain workflows (TopoLT layers, PAD coordinate generation). These are intentionally deferred to Phase 4 (Domain Pack Extraction).
2. **LiDAR Segmentation Coupling:** Full building ground-surface classification and nDSM rasterization pipelines reside in `lidar_processor.py`, awaiting migration into the `stratum_ro/domain/lidar` pack in Phase 4.
3. **PyQGIS Dockwidget GUI:** `stratum_ro_dockwidget.py` remains connected to legacy entry points; adapter integration will occur during client consolidation.

---

## 19. Phase 4 Readiness

With Phase 3 complete and verified:
- **Pure Core Established:** `stratum_ro/core/` is self-contained, tested, and pure-Python.
- **Golden Baseline Preserved:** Zero drift across all geodetic coordinates and tests.
- **Contract Adherence:** Formal interfaces in `stratum_ro/contracts/` are fully implemented by Core components.
- The project is fully primed for **Phase 4 — Domain Pack Extraction & Domain Boundary Migration** (separating Cadastre RO, Topography, LiDAR, and Vision).

---

# 20. FINAL GATE VERDICT

```text
======================================================================
PHASE 3 STATUS:
PASS

CORE SUBSYSTEMS EXTRACTED:
- Geometry (regularizer, metrics, cleaning)
- Geodesy / CRS (crs, transformer)
- QA/QC (validator)
- Raster (metadata, reader)
- Point Cloud (metadata, processor)

COMPATIBILITY:
VERIFIED (Zero breaking changes; legacy modules and APIs fully intact)

SCIENTIFIC REGRESSION:
NONE (0.000 mm coordinate shift, 0.000 mm² area drift)

GROUND TRUTH:
UNCHANGED (Bitwise SHA-256 match on all reference datasets)

TESTS:
245 discovered | 236 passed | 9 skipped | 0 failed (35.02s)

PHASE 4 READY:
YES
======================================================================
```
