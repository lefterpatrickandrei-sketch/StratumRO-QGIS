# 09. TOOL SELECTION MATRIX & ROLE MAPPING

**Audit Date:** 2026-09-19  
**Principle:** Use the Best Verified Open-Source Tool, Not Just the Most Familiar

---

## Processing Task to Tool Mapping Matrix

| Processing Task | Primary Verified Tool | Fallback / Alternative | Input Data | Output Data | Justification & Execution Route |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MrSID Orthophoto Access** | **QGIS GDAL (v3.9.3)** | Dedicated VRT tiles | 8 `Orto Cluj-*.sid` files | Virtual Raster (`.vrt`) | QGIS contains the only verified LizardTech MrSID driver (`gdal_MrSID.dll`). |
| **Virtual Mosaic (VRT)** | **`gdalbuildvrt.exe`** | QGIS Virtual Raster | 8 MrSID tiles | `cluj_ortho_mosaic.vrt` | Fast, zero-disk duplication, preserves native 1.165 cm GSD without uncompressing 7.2 GB. |
| **LiDAR Inspection** | **`laspy 2.7.0`** | `pdal info` | `NorPuncte_St70_S42.laz` | Header / VLR metadata | Native Python integration with millimetric precision and ASPRS class breakdown. |
| **Point Cloud Filtering** | **PDAL 2.8.1 (`pdal.exe`)**| `laspy` + numpy | `NorPuncte_St70_S42.laz` | Filtered ground / building LAS | Multi-threaded C++ execution, memory-mapped I/O, proven ASPRS filtering. |
| **DTM Generation (3.0m)** | **Existing Verified DTM** | `pdal writers.gdal` | `DTM3m.tif` / Class 2 LiDAR | Bare-earth GeoTIFF | Original DTM3m is verified and geodetically aligned with LiDAR. |
| **DSM Generation (1.0m)** | **PDAL 2.8.1 (`writers.gdal`)**| `laspy` binning | First-return / Class 6 points | Surface GeoTIFF (1.0m) | Generates top-of-canopy and building roof envelope. |
| **nDSM Generation (1.0m)** | **Deterministic Math (GDAL/NumPy)**| `gdal_calc.py` | `DSM - DTM` | `cluj_ndsm_1m.tif` | Pure deterministic height difference: $\text{nDSM} = \text{DSM} - \text{DTM}$. |
| **Candidate Detection** | **StratumRO Candidate Engine**| Thresholding + Morphology | `cluj_ndsm_1m.tif` ($h > 2.5\text{ m}$) | Candidate BBoxes / Centroids | Generates AI prompts independently from Ground Truth. |
| **Optical Segmentation** | **Meta SAM 2 Hiera** | ONNX DirectML Runtime | Ortho crop + candidate prompts | Raw binary building masks | State-of-the-art vision model for building contour delineation. |
| **Mask Vectorization** | **`rasterio.features.shapes`**| `cv2.findContours` | Raw binary masks | Raw shapely Polygons | Exact pixel-to-coordinate mapping in Stereo 70. |
| **90° CAD Regularization** | **`stratum_ro/vectorizer.py`**| Canonical 4-vertex fit | Raw shapely Polygons | Regularized 90° Footprints | Deterministic local GEOS orthogonalization (ANCPI 600/2023 compliant). |
| **CAD Layer Export** | **`stratum_ro/cad_exporter.py`**| `ezdxf` | Regularized Polygons | TopoLT DXF (`1CC`, `CP`) | Produces standard Romanian cadastral CAD layers and PAD tables. |
| **Validation Metrics** | **`engine/evaluation.py`** | `scipy.spatial` | Prediction vs Reference | IoU, RMSE, $\Delta X, \Delta Y$, P95 | Independent mathematical scoring with Wilson score confidence intervals. |
| **Live QGIS Visualization**| **`qgis-bin.exe` / PyQGIS** | Standalone viewer | QGS project + real layers | Live visual display | Allows geodetic surveyor to inspect predictions directly in desktop QGIS. |
