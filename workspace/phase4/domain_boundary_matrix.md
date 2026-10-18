# Domain Boundary Matrix — StratumRO Phase 4

This matrix defines the symbol-level architectural classification for candidate domain logic across the StratumRO repository, strictly distinguishing between generic Core capabilities, Domain-specific packs, AI infrastructure, and QGIS client adapters.

---

## 1. Symbol-Level Classification Matrix

| Symbol / Class | Current File | Domain Area | Core? | Domain? | AI? | QGIS? | Risk | Target Package |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CadastralDxfExporter` | `cad_exporter.py` | Cadastre RO | No | **Yes** | No | No | Low | `stratum_ro.domain.cadastre_ro` |
| `_setup_layers` (TopoLT) | `cad_exporter.py` | Cadastre RO | No | **Yes** | No | No | Low | `stratum_ro.domain.cadastre_ro` |
| `_draw_pad_coordinate_table` | `cad_exporter.py` | Cadastre RO | No | **Yes** | No | No | Low | `stratum_ro.domain.cadastre_ro` |
| `export_cp_file` | `cad_exporter.py` | Cadastre RO | No | **Yes** | No | No | Low | `stratum_ro.domain.cadastre_ro` |
| `CadastralProduct` | `cadastral_product.py` | Cadastre RO | No | **Yes** | No | No | Low | `stratum_ro.domain.cadastre_ro` |
| `Volumetric3DBuilder` | `volumetric_3d.py` | 3D / City | No | **Yes** | No | No | Low | `stratum_ro.domain.city_3d` |
| `extrude_lod1_solid` | `volumetric_3d.py` | 3D / City | No | **Yes** | No | No | Low | `stratum_ro.domain.city_3d` |
| `export_cityjson_lod1` | `volumetric_3d.py` | 3D / City | No | **Yes** | No | No | Low | `stratum_ro.domain.city_3d` |
| `fit_roof_planes_ransac` | `volumetric_3d.py` | 3D / City | No | **Yes** | No | No | Low | `stratum_ro.domain.city_3d` |
| `LidarProcessor` | `lidar_processor.py` | LiDAR | No | **Yes** | No | No | Low | `stratum_ro.domain.lidar` |
| `LidarQualityGate` | `lidar_quality_gate.py`| LiDAR | No | **Yes** | No | No | Low | `stratum_ro.domain.lidar` |
| `CandidateGenerator` | `candidate_generator.py` | Vision | No | **Yes** | Yes | No | Low | `stratum_ro.domain.vision` |
| `ONNXSegmentationEngine` | `onnx_engine.py` | Vision | No | **Yes** | Yes | No | Low | `stratum_ro.domain.vision` |
| `MaskFusionEngine` | `mask_fusion.py` | Vision | No | **Yes** | Yes | No | Low | `stratum_ro.domain.vision` |
| `MultimodalVegetationFilter` | `vegetation_filter.py` | Vision / LiDAR | No | **Yes** | No | No | Low | `stratum_ro.domain.vision` |
| `StratumROCadastralAlgorithm`| `cadastral_algorithm.py`| QGIS Adapter | No | No | No | **Yes**| Medium| `stratum_ro.client.qgis` |
| `StratumRODockWidget` | `stratum_ro_dockwidget.py`| QGIS Client | No | No | No | **Yes**| High | `stratum_ro.client.qgis` |

---

## 2. Domain Maturity Assessment (§3)

| Domain Candidate | Real Code | Real Data | Real Workflow | Real Tests | Real Output | Maturity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Cadastre RO** | `cad_exporter.py`, `cadastral_product.py` | `tier1_teren.geojson` (29 ref) | Assisted ANCPI pre-cadastre | `test_cad_exporter.py` | DXF TopoLT, `.CP`, PAD | **MATURE** |
| **3D / City** | `volumetric_3d.py` | `cluj_ndsm_1m.tif` | LoD1 extrusion + CityJSON | `test_volumetric_3d.py` | CityJSON v1.1, GPKG MultiPolygonZ | **MATURE** |
| **LiDAR** | `lidar_processor.py`, `lidar_quality_gate.py`| Airborne LAS/LAZ + nDSM | Height filtering + nDSM raster | `test_lidar_quality_gate.py` | nDSM 1m GeoTIFF, h_mean | **MATURE** |
| **Vision** | `candidate_generator.py`, `onnx_engine.py`, `mask_fusion.py` | USAMV Cluj orthophoto | SAM2 prompt -> mask -> polygon | `test_onnx_directml.py` | Binary masks, candidate footprints | **MATURE** |
| **Topography** | Slope/aspect helpers in filters | nDSM raster | Slope filtering | Partial | Slope array | **PARTIAL** |
| **Urbanism / Hydro** | `pug_product.py` (adapter) | PUG layers | Landuse PUG styling | None | Styling layer | **FUTURE** |

---

## 3. Migration Dependency Ordering (§4, §29)

Dependency order determined from import graph:
1. **`cadastre_ro`**: Pure consumer of `core.geometry` and `core.geodesy`. Zero 3D or LiDAR coupling.
2. **`city_3d`**: Consumes `core.geometry` and `core.geodesy`. Exports OGC CityJSON and 3D solids.
3. **`lidar`**: Consumes `core.pointcloud` and `core.raster`. Generates nDSM.
4. **`vision`**: Consumes `core.geometry` and `core.raster`. Runs SAM2 ONNX and mask fusion.
5. **`topography`**: Declared as `PARTIAL` capability adapter.
