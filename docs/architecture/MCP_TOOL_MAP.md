# MCP_TOOL_MAP.md — StratumRO MCP Tool Interfaces & Security Contracts

> **Standard:** FastMCP / Model Context Protocol (JSON-RPC 2.0)  
> **Host Environment:** Antigravity Control Plane & Local QGIS Worker  
> **Security Model:** Principle of Least Privilege (ALLOW / ASK / DENY)

---

## 1. Overview & Strategy

The Model Context Protocol (MCP) serves as the primary bridge connecting the **Antigravity AI Control Plane** to the deterministic **StratumRO geospatial engines**.

Rather than granting an LLM raw terminal access or arbitrary Python execution rights inside QGIS, StratumRO exposes **curated, deterministic tool interfaces** with strictly typed inputs, bounded execution sandboxes, and human-in-the-loop approval gates for state-altering actions.

---

## 2. Reusable Existing MCP Functionality

The repository already contains two functional FastMCP servers:

| MCP Server | Location | Existing Tools | Reuse Strategy |
| :--- | :--- | :--- | :--- |
| **Filesystem** | `mcp/filesystem/server.py` | `create_folder(name)`<br>`list_files(subpath)` | Retain as the project's sandboxed storage tool. All operations are strictly bound within `workspace/` via `_safe_resolve()`. |
| **Dataset Manager** | `mcp/dataset_manager/server.py` | `download_geospatial_data(url, filename, layer_type)` | Retain for downloading external geodata (TIF rasters, LAZ point clouds) with automatic structural validation. |

---

## 3. StratumRO Domain Engine MCP Tool Catalog

The proposed `stratumro_mcp_server.py` groups tools by functional domain and links directly to existing implementations without rewriting core algorithms.

### 3.1 Project & QGIS Context (`project.*`, `layers.*`)

| Tool Identifier | Description | Parameters | Underlying Module | Permission |
| :--- | :--- | :--- | :--- | :--- |
| `project.get_context` | Inspects active QGIS project CRS, extent, loaded layers, and hardware status. | *None* | `stratum_ro/stratum_ro_dockwidget.py` | `ALLOW` (Read-only) |
| `project.get_aoi` | Retrieves current map canvas extent or selected polygon in Stereo 70 (EPSG:3844). | `format: str = "wkt"` | `qgis.gui.QgsMapCanvas` | `ALLOW` (Read-only) |
| `layers.list` | Returns all available layers in active workspace/QGIS canvas. | *None* | `qgis.core.QgsProject` | `ALLOW` (Read-only) |
| `layers.inspect` | Returns attribute schema, feature count, CRS, and sample geometries. | `layer_name: str` | `qgis.core.QgsVectorLayer` | `ALLOW` (Read-only) |

### 3.2 LiDAR & Raster Analysis (`lidar.*`, `raster.*`)

| Tool Identifier | Description | Parameters | Underlying Module | Permission |
| :--- | :--- | :--- | :--- | :--- |
| `lidar.inspect` | Analyzes header, bounding box, density ($pts/m^2$), and class distribution of a `.laz` file. | `laz_path: str` | `stratum_ro/lidar_processor.py` (`laspy`) | `ALLOW` (Read-only) |
| `lidar.generate_ndsm` | Derives normalized Digital Surface Model (nDSM) and generates building/outbuilding/tree candidate grids. | `laz_path: str`, `dtm_path: str`, `resolution_m: float = 1.0` | `LidarProcessor.process_multicategory()` | `SAFE_WRITE` (ALLOW) |
| `raster.inspect` | Reads resolution, transform, CRS, band stats, and NoData value. | `raster_path: str` | `stratum_ro/ortho_extractor.py` (`rasterio`) | `ALLOW` (Read-only) |

### 3.3 Semantic Segmentation (`segmentation.*`)

| Tool Identifier | Description | Parameters | Underlying Module | Permission |
| :--- | :--- | :--- | :--- | :--- |
| `segmentation.run_sam2` | Executes Meta SAM2 Hiera inference on orthophoto chips using LiDAR centroid/bounding box prompts. | `aoi_bbox: list[float]`, `candidate_grid_path: str`, `device: str = "auto"` | `stratum_ro/sam2_engine.py` (`SAM2BuildingSegmenter`) | `SAFE_WRITE` (ALLOW) |
| `segmentation.inspect_mask` | Calculates mask area, perimeter, edge compactness, and confidence score. | `mask_id: str` | `stratum_ro/sam2_engine.py` | `ALLOW` (Read-only) |

### 3.4 Vectorization, Regularization & Partitioning (`vector.*`)

| Tool Identifier | Description | Parameters | Underlying Module | Permission |
| :--- | :--- | :--- | :--- | :--- |
| `vector.regularize` | Applies 90° orthogonal regularization: MRR 4-vertex rectangle fitting or `buildingregulariser`. | `input_mask_path: str`, `mrr_trigger: float = 0.70` | `stratum_ro/vectorizer.py` (`CadastralVectorizer`) | `SAFE_WRITE` (ALLOW) |
| `vector.apply_eave_offset` | Retracts roofline contour by eave offset (default $-0.40\text{ m}$) to produce ANCPI ground footprint. | `polygons: list`, `offset_m: float = -0.40` | `stratum_ro/vectorizer.py` | `SAFE_WRITE` (ALLOW) |
| `vector.planar_partition` | Eliminates overlaps and generates gap-free planar partition for parcel sector. | `buildings_layer: str`, `sector_boundary: str` | `stratum_ro/vectorizer.py` & `landuse_ancpi.py` | `SAFE_WRITE` (ALLOW) |

### 3.5 Geodetic & Cadastral Validation (`cadastral.*`, `evaluation.*`)

| Tool Identifier | Description | Parameters | Underlying Module | Permission |
| :--- | :--- | :--- | :--- | :--- |
| `geometry.validate_topology` | Checks for self-intersections, duplicate nodes, spike angles ($< 40^\circ$), and sliver gaps. | `layer_path: str` | `stratum_ro/vectorizer.py` (`shapely`) | `ALLOW` (Read-only) |
| `cadastral.validate_ancpi` | Validates minimum area thresholds ($\ge 45\text{ m}^2$ main, $\ge 8\text{ m}^2$ annex) according to Ordinul 600/2023. | `layer_path: str` | `stratum_ro/cadastral_product.py` | `ALLOW` (Read-only) |
| `evaluation.compare_ground_truth` | Calculates IoU, 95% Hausdorff Distance, Boundary RMSE, and Wilson score CI against reference data. | `pred_gpkg: str`, `gt_geojson: str` | `engine/evaluation.py` (`Evaluator`) | `ALLOW` (Read-only) |

### 3.6 Visualization, Approval & Export (`results.*`, `export.*`)

| Tool Identifier | Description | Parameters | Underlying Module | Permission |
| :--- | :--- | :--- | :--- | :--- |
| `results.create_preview` | Creates temporary in-memory QGIS vector layer with color-coded confidence symbology for visual review. | `geometry_geojson: dict`, `layer_title: str` | `stratum_ro/stratum_ro_dockwidget.py` | `SAFE_WRITE` (ALLOW) |
| `results.commit_to_project` | Merges user-approved preview geometries into the official project layers. | `preview_layer_name: str` | `qgis.core.QgsVectorLayer` | `ASK` (User confirmation) |
| `export.export_gpkg` | Writes official multi-layer GeoPackage in Stereo 70 (EPSG:3844). | `output_path: str`, `layers: list[str]` | `pyogrio` / `geopandas` | `SAFE_WRITE` (ALLOW) |
| `export.export_topolt_dxf` | Exports TopoLT-standard DXF (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`) and PAD coordinate table. | `output_dxf_path: str`, `parcels: list`, `buildings: list` | `stratum_ro/cad_exporter.py` (`CadastralDxfExporter`) | `ASK` (User confirmation) |
| `export.export_cp` | Exports official `.CP` text interchange file for ANCPI eTerra. | `output_cp_path: str`, `points: list` | `stratum_ro/cad_exporter.py` | `ASK` (User confirmation) |
| `export.export_cityjson` | Exports LoD1 solid building shell in CityJSON v1.1. | `output_json_path: str` | `stratum_ro/volumetric_3d.py` | `SAFE_WRITE` (ALLOW) |

---

## 4. MCP Security & Sandbox Policy

```
                    ┌───────────────────────────────┐
                    │       ANTIGRAVITY AGENT       │
                    └───────────────┬───────────────┘
                                    │
                       Tool Request (JSON-RPC 2.0)
                                    ▼
                    ┌───────────────────────────────┐
                    │      MCP PERMISSION GATE      │
                    ├───────────────────────────────┤
                    │ • ALLOW: Read-only queries    │
                    │ • ALLOW: Temporary previews   │
                    │ • ASK: Commit / Export / CAD  │
                    │ • DENY: Arbitrary OS/Python   │
                    └───────────────┬───────────────┘
                                    │ Authorized call
                                    ▼
                    ┌───────────────────────────────┐
                    │    STRATUMRO DOMAIN ENGINE    │
                    │ (Deterministic Math / PyQGIS) │
                    └───────────────────────────────┘
```

1. **No Raw Code Execution:** Tools like `eval()` or arbitrary bash commands are strictly prohibited in the MCP server.
2. **Preview-First Pattern:** Modifying or generating geometry always writes first to a temporary memory layer (`preview_buildings_temp`). The user inspects the preview and approves before `results.commit_to_project` executes.
3. **Evidence Integrity:** Tools returning confidence metrics must compute them from physical sensor signals (nDSM elevation agreement, boundary sharpness), never from LLM hallucination.
