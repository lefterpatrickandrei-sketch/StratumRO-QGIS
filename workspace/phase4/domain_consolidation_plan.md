# Domain Consolidation Plan — StratumRO Phase 4.2

**Actionable Pre-Consolidation Roadmap for Safe Domain Migration without Scientific Regressions**  
*Status as of 2026-09-20 — Pre-Execution Design Document (§36, §38, §39)*

---

## 1. Guiding Principles for Safe Domain Consolidation

1. **Single Source of Implementation (§8, §50):**  
   Every domain feature will have exactly ONE canonical implementation file located in `stratum_ro/domain/<domain>/`.
2. **Backward-Compatible Legacy Forwarders (§38, §39):**  
   Root-level modules (`cad_exporter.py`, `volumetric_3d.py`, etc.) will NOT be deleted. Instead, they will become lightweight forwarders that re-export canonical classes, functions, and constants. This ensures that existing QGIS Desktop installations, CLI scripts, and third-party consumers continue functioning with zero breakage.
3. **Zero Scientific Regression (§40):**  
   Consolidation is strictly a packaging refactoring. It must NOT change geodetic coordinates, CRS validation, CAD layer formatting, or 3D extrusion heights.
4. **Step-by-Step Isolation (§49):**  
   Domains will be migrated one by one in Phase 4.3+, prioritized by lowest dependency coupling and verified by running the test suite after each migration.

---

## 2. Per-Domain Consolidation Specifications

### 2.1. Domain: `cadastre_ro`
* **Current Implementation:**
  - Root: `stratum_ro/cad_exporter.py` (19,485 B) & `stratum_ro/cadastral_product.py` (7,461 B)
  - Domain: `stratum_ro/domain/cadastre_ro/exporter.py` (19,485 B) & `product.py` (7,467 B)
* **Canonical Target:** `stratum_ro/domain/cadastre_ro/` (`exporter.py`, `product.py`)
* **Legacy Compatibility Strategy:**
  - `stratum_ro/cad_exporter.py` forwarder:
    ```python
    # stratum_ro/cad_exporter.py
    from stratum_ro.domain.cadastre_ro.exporter import CadastralDxfExporter, _extract_polygons
    __all__ = ["CadastralDxfExporter", "_extract_polygons"]
    ```
  - `stratum_ro/cadastral_product.py` forwarder:
    ```python
    # stratum_ro/cadastral_product.py
    from stratum_ro.domain.cadastre_ro.product import CadastralProductGenerator
    __all__ = ["CadastralProductGenerator"]
    ```
* **Consumers:** `stratum_ro/cadastral_algorithm.py`, `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/ai/tools/cadastral_tools.py`, `run_hybrid_full_aoi.py`.
* **Test Suite:** `stratum_ro/test/test_cad_exporter.py`, `stratum_ro/test/test_cp_export_real_coords.py`.
* **Scientific Risks:** Inversion of X/Y (Stereo 70 North/East), PAD table format deviation, `.CP` point number indexing errors.
* **Migration Risk:** **LOW** (pure wrapper, no external dependencies outside `core.geometry` and `core.geodesy`).
* **Blocked By:** Awaiting Phase 4.2 audit gate approval.

---

### 2.2. Domain: `city_3d`
* **Current Implementation:**
  - Root: `stratum_ro/volumetric_3d.py` (9,350 B)
  - Domain: `stratum_ro/domain/city_3d/builder.py` (9,350 B)
* **Canonical Target:** `stratum_ro/domain/city_3d/builder.py`
* **Legacy Compatibility Strategy:**
  - `stratum_ro/volumetric_3d.py` forwarder:
    ```python
    # stratum_ro/volumetric_3d.py
    from stratum_ro.domain.city_3d.builder import Volumetric3DBuilder
    __all__ = ["Volumetric3DBuilder"]
    ```
* **Consumers:** `stratum_ro/ai/tools/vector_tools.py`, `stratum_ro/pug_product.py`.
* **Test Suite:** `stratum_ro/test/test_volumetric_3d.py`.
* **Scientific Risks:** OGC CityJSON v1.1 syntax deviation, GeoPackage MultiPolygonZ polygon winding order inversion.
* **Migration Risk:** **LOW** (pure self-contained 3D geometry builder).
* **Blocked By:** Awaiting Phase 4.2 audit gate approval.

---

### 2.3. Domain: `lidar`
* **Current Implementation:**
  - Root: `stratum_ro/lidar_processor.py` (9,824 B) & `stratum_ro/lidar_quality_gate.py` (10,271 B)
  - Domain: `stratum_ro/domain/lidar/processor.py` (9,824 B) & `quality_gate.py` (10,271 B)
* **Canonical Target:** `stratum_ro/domain/lidar/` (`processor.py`, `quality_gate.py`)
* **Legacy Compatibility Strategy:**
  - `stratum_ro/lidar_processor.py` forwarder:
    ```python
    # stratum_ro/lidar_processor.py
    from stratum_ro.domain.lidar.processor import LidarProcessor
    __all__ = ["LidarProcessor"]
    ```
  - `stratum_ro/lidar_quality_gate.py` forwarder:
    ```python
    # stratum_ro/lidar_quality_gate.py
    from stratum_ro.domain.lidar.quality_gate import LidarQualityGate
    __all__ = ["LidarQualityGate"]
    ```
* **Consumers:** `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/ai/tools/lidar_tools.py`, `stratum_ro/vectorizer.py`, `run_hybrid_full_aoi.py`.
* **Test Suite:** `stratum_ro/test/test_geometric_reconstruction_v2.py`.
* **Scientific Risks:** GeoTIFF affine transform georeferencing offset, nDSM height sampling miscalculation.
* **Migration Risk:** **LOW-MEDIUM**.
* **Blocked By:** Awaiting Phase 4.2 audit gate approval.

---

### 2.4. Domain: `vision`
* **Current Implementation:**
  - Root: `candidate_generator.py` (5,714 B), `onnx_engine.py` (8,972 B), `mask_fusion.py` (5,866 B), `vegetation_filter.py` (7,160 B)
  - Domain: `stratum_ro/domain/vision/` (`candidates.py`, `engine.py`, `fusion.py`, `vegetation.py`)
* **Canonical Target:** `stratum_ro/domain/vision/`
* **Legacy Compatibility Strategy:**
  - Root files become clean forwarders re-exporting canonical classes (`CandidateGenerator`, `ONNXSegmentationEngine`, `MaskFusionEngine`, `MultimodalVegetationFilter`).
* **Consumers:** `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/ai/tools/segmentation_tools.py`.
* **Test Suite:** `stratum_ro/test/test_onnx_engine.py`, `stratum_ro/test/test_phase3_modules.py`.
* **Scientific Risks:** DirectML ONNX inference session invalidation, prompt pixel coordinate offset relative to raster affine transform.
* **Migration Risk:** **MEDIUM**.
* **Blocked By:** Awaiting Phase 4.2 audit gate approval.

---

### 2.5. Domain: `topography`
* **Current Implementation:** `stratum_ro/domain/topography/adapter.py` (40-line stub, Horn method).
* **Canonical Target:** `stratum_ro/domain/topography/adapter.py`
* **Legacy Compatibility Strategy:** No root counterpart exists.
* **Action:** **RETAIN AS PARTIAL ADAPTER**. Do NOT expand prematurely (§11, §17).
* **Migration Risk:** **NONE**.
* **Blocked By:** Future topography development.

---

## 3. Recommended Migration Sequence for Phase 4.3+

Based on the import and dependency graph, the optimal migration order with minimal cascading risk is:

$$\text{Domain Migration Priority}: \mathbf{city\_3d} \longrightarrow \mathbf{cadastre\_ro} \longrightarrow \mathbf{lidar} \longrightarrow \mathbf{vision} \longrightarrow \mathbf{topography}$$

1. **`city_3d` (First):** Pure leaf node in dependency graph. Consumes only core geometry. Zero QGIS GUI direct coupling.
2. **`cadastre_ro` (Second):** Consumes core geometry/geodesy. Provides canonical ANCPI DXF/.CP outputs.
3. **`lidar` (Third):** Point cloud to nDSM raster pipeline.
4. **`vision` (Fourth):** Deep learning ONNX DirectML model execution.
5. **`topography` (Fifth/Future):** Reserved until additional terrain surface algorithms are implemented.
