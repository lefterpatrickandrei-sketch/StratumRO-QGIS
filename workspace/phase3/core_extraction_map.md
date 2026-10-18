# STRATUMRO — CORE EXTRACTION FORENSIC MAP

**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Phase:** Phase 3 — Core Extraction & Pure-Python Isolation  
**Audit Standard:** 8 Evidence-First Scientific Rules (AGENTS.md §3)  
**Date:** 2026-09-20  

---

## 1. SUBSYSTEM EXTRACTION CANDIDATES MATRIX

În conformitate cu Secțiunea 5 din mandatul Fazei 3, fiecare modul candidat a fost auditat la nivel de simbol, dependențe, contracte asociate și riscuri:

| Fișier Curent | Simboluri Vizate | Dependențe Tehnice | Contract Core Asignat | Locație Țintă Core | Dependență QGIS | Dependență Domeniu | Risc Științific |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| `stratum_ro/vectorizer.py` | `_extract_largest_polygon`, `remove_acute_spikes`, `count_macro_reflex_corners`, `compute_orthogonality_ratio`, `orthogonalize_cad` | Shapely, NumPy, SciPy, math | `IGeometryEngine` (`contracts/geometry.py`) | `stratum_ro/core/geometry/regularizer.py` | **ZERO** (Pure Python) | **ZERO** (Matematică pură 2D) | `HIGH` (Invarianță coordonate) |
| `stratum_ro/vectorizer.py` | `CadastralVectorizer.clean_cad_polygon`, `orthogonalize_polygon`, `build_planar_partition` | Shapely, NumPy | `IGeometryEngine` (`contracts/geometry.py`) | `stratum_ro/core/geometry/cleaning.py` | **ZERO** (Pure Python) | **ZERO** (Topologie generică) | `HIGH` (Arii analitice) |
| `engine/evaluation.py` | `calculate_iou`, `calculate_hausdorff_distance`, `calculate_boundary_rmse`, `calculate_centroid_shift` | Shapely, SciPy, NumPy | `IGeometryEngine` (`contracts/geometry.py`) | `stratum_ro/core/geometry/metrics.py` | **ZERO** (Pure Python) | **ZERO** (Metrice spațiale) | `MEDIUM` (Denumiri metrice) |
| `stratum_ro/api/service.py` | `TRANSFORMER_3844_TO_4326`, `TRANSFORMER_4326_TO_3844`, Transformări coordonate | pyproj, PROJ | `ITransformer`, `ICRSManager` (`contracts/geodesy.py`) | `stratum_ro/core/geodesy/transformer.py` | **ZERO** (Pure Python) | **ZERO** (PROJ geodetic) | `CRITICAL` (Axe & datume) |
| `stratum_ro/ai/data_profiler.py` | `QualityReport`, `QualityLevel`, reguli L0-L2 | Pydantic / dataclasses, Shapely | `IValidator`, `ValidationReport` (`contracts/validation.py`) | `stratum_ro/core/qa_qc/validator.py` | **ZERO** (Pure Python) | **ZERO** (Validare structurală) | `LOW` |
| `stratum_ro/ortho_extractor.py` | Windowed reading, VRT slicing, resampling, nodata | rasterio, NumPy | `IGeoProcessor` (`contracts/geo.py`) | `stratum_ro/core/raster/reader.py` | **ZERO** (Pure Python) | **ZERO** (I/O Raster) | `LOW` |
| `stratum_ro/lidar_processor.py` | Citire LAS/LAZ, filtrare puncte sol vs nDSM | laspy, NumPy | `IGeoProcessor` (`contracts/geo.py`) | `stratum_ro/core/pointcloud/processor.py` | **ZERO** (Pure Python) | **ZERO** (I/O Point Cloud) | `LOW` |

---

## 2. COMPONENTE EXCLUSE STRICT DIN FAZA 3 (RĂMÂN ÎN DOMAIN / CLIENT)

1. **`stratum_ro/cad_exporter.py`**: Conține standarde specifice României (Ordinul ANCPI 600/2023, straturi TopoLT `1CC`/`2CC`, tabele PAD, format `.CP`). **NU aparține Core-ului universal.** Va fi extras în Faza 4 în `stratum_ro/domains/cadastre_ro/`.
2. **`stratum_ro/vectorizer.py` (`compute_adaptive_eave_offset`, `format_hybrid_buildings`)**: Conține reguli constructive locale privind retragerea streșinilor. Rămâne în stratul de domeniu.
3. **`stratum_ro/volumetric_3d.py`**: Modelarea LoD1 și exportul CityJSON v1.1 vor merge în `domains/city_3d/` în Faza 4.
4. **`stratum_ro/stratum_ro_dockwidget.py`**: Client UI QGIS. Rămâne la nivel de client.
5. **AI Orchestration (`router.py`, `task_graph.py`, `executor.py`)**: Rămân în `stratum_ro/ai/` fără modificări în această etapă.

---

## 3. STRUCTURA MINIMALĂ ȚINTĂ PENTRU `stratum_ro/core/`

```text
stratum_ro/core/
├── __init__.py
├── geometry/
│   ├── __init__.py
│   ├── regularizer.py     # 90° orthogonalization, spike removal, macro reflex
│   ├── cleaning.py        # clean_cad_polygon, planar partition
│   └── metrics.py         # IoU, Hausdorff, Boundary RMSE, Centroid shift
├── geodesy/
│   ├── __init__.py
│   ├── crs.py             # CRS metadata & validation (Stereo 70, ETRS89)
│   └── transformer.py     # PROJ deterministic coordinate transformations
├── qa_qc/
│   ├── __init__.py
│   └── validator.py       # Deterministic geometric & attribute QA/QC
├── raster/
│   ├── __init__.py
│   └── reader.py          # Windowed rasterio reading & slicing
└── pointcloud/
    ├── __init__.py
    └── processor.py       # laspy point cloud reading & filtering
```

---

## 4. SECVENȚA DE EXTRAGERE SIGURĂ (ONE SUBSYSTEM AT A TIME)

```text
SUBSYSTEM 1: GEOMETRY (regularizer, cleaning, metrics)
      ↓
TEST & GOLDEN VERIFY
      ↓
SUBSYSTEM 2: GEODESY & CRS (crs, transformer)
      ↓
TEST & GOLDEN VERIFY
      ↓
SUBSYSTEM 3: QA/QC (validator)
      ↓
TEST & GOLDEN VERIFY
      ↓
SUBSYSTEM 4: RASTER & POINT CLOUD (reader, processor)
      ↓
TEST & GOLDEN VERIFY
```
