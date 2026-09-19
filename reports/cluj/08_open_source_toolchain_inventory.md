# 08. OPEN-SOURCE GEOSPATIAL TOOLCHAIN INVENTORY

**Audit Date:** 2026-09-19  
**Host Machine:** Windows 11 Pro (x64)  
**Verification Method:** Direct Windows CLI execution, binary version extraction, and library probe  
**Machine-Readable Spec:** [`reports/cluj/toolchain_versions.json`](file:///c:/Users/lefpa/Downloads/QGIS-AI/reports/cluj/toolchain_versions.json)  
**Status:** Verified on Windows Host Environment via Direct CLI Execution

---

## 1. Installed Software Inventory Table

| Tool Name | Exact Version | Executable / Batch Path | Installation Type | Automation Capability | Verified Purpose in StratumRO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **QGIS Desktop** | 3.40.0-Bratislava | `C:\Program Files\QGIS 3.40.0\bin\qgis-bin.exe` | Standalone MSI | GUI / Scriptable | Master orchestration, live visual spectator, layer visualization |
| **QGIS Process** | 3.40.0 | `C:\Program Files\QGIS 3.40.0\bin\qgis_process-qgis.bat` | QGIS Built-in | Headless CLI | Batch execution of native QGIS processing algorithms |
| **QGIS Python** | Python 3.12.7 | `C:\Program Files\QGIS 3.40.0\bin\python-qgis.bat` | QGIS Built-in | Python CLI | PyQGIS runtime with `qgis.core`, `qgis.gui`, and GDAL MrSID driver |
| **GDAL CLI** | 3.9.3 | `C:\Program Files\QGIS 3.40.0\bin\gdalinfo.exe` | QGIS Built-in | Full CLI | Raster inspection, VRT generation, tiling, GDAL MrSID support |
| **PROJ CLI** | PROJ 9.x | `C:\Program Files\QGIS 3.40.0\bin\projinfo.exe`, `cs2cs.exe` | QGIS Built-in | Full CLI | Geodetic transformation inspection, Stereo 70 parameter verification |
| **PDAL** | 2.8.1 (git a06325)| `C:\Program Files\QGIS 3.40.0\bin\pdal.exe` | QGIS Built-in | Full CLI / Pipelines | Native LiDAR processing, ground classification filtering, DTM/DSM grids |
| **GRASS GIS** | GRASS 8.4 | `C:\Program Files\QGIS 3.40.0\apps\grass\` | QGIS Provider | CLI / Python | Advanced morphological operations, hydrology, high-precision vectorization |
| **SAGA GIS** | SAGA LTR | `C:\Program Files\QGIS 3.40.0\apps\saga\` | QGIS Provider | CLI / QGIS | Terrain analysis, slope, aspect, relief visualization |
| **ESA SNAP** | 11.0.0 | `C:\Program Files\esa-snap\bin\snap64.exe`, `gpt.exe` | Standalone Installer | Java Graph CLI (`gpt`)| Sentinel-1/2 EO processing, SAR interferometry (Reserved for future SAR phase) |
| **Python Venv** | Python 3.10.10 | `c:\Users\lefpa\Downloads\QGIS-AI\venv\Scripts\python.exe` | Local Virtualenv | Full Python | Core StratumRO runtime: PyTorch CUDA, ONNX DirectML, Shapely, GeoPandas |
| **FastMCP** | 2.x | `c:\Users\lefpa\Downloads\QGIS-AI\venv\Scripts\fastmcp.exe`| Python Script | Stdio MCP | Model Context Protocol servers: `stratumro`, `filesystem`, `dataset_manager` |
| **GitHub CLI** | 2.96.0 | `C:\Program Files\GitHub CLI\gh.exe` | Standalone MSI | Full CLI | Keyring authenticated Git/GitHub synchronization |
| **CloudCompare**| **NOT INSTALLED** | N/A | Missing | N/A | Not found in Program Files or AppData |

---

## 2. Key Tool Evaluation & Guardrails

### ESA SNAP Evaluation (AGENTS.md Compliance)
- **Status:** **INSTALLED (v11.0.0)** at `C:\Program Files\esa-snap\bin\`.
- **Capability:** Powerful for Sentinel-1 Synthetic Aperture Radar (SAR) and Sentinel-2 multispectral MSI data.
- **Decision for Cluj Phase 2:** **DO NOT INSERT INTO CLUJ BENCHMARK.**  
  The Cluj source dataset consists strictly of **1.16 cm UAV RGB imagery** and **airborne LiDAR**. Inserting SNAP into this RGB/LiDAR pipeline would introduce unnecessary Java JVM overhead without providing any scientific or resolution benefit. SNAP is preserved for the future satellite/multispectral expansion phase.

### PDAL Evaluation
- **Status:** **INSTALLED (v2.8.1)** in QGIS bin.
- **Capability:** Industrial-grade C++ point cloud processing.
- **Decision for Cluj Phase 2:** **ADOPT FOR REPRODUCIBLE nDSM PIPELINE.**  
  PDAL can read `NorPuncte_St70_S42.laz`, isolate Class 2 (Ground) and Class 6 (Buildings), and rasterize ground/surface grids with zero Python GIL bottlenecks.
