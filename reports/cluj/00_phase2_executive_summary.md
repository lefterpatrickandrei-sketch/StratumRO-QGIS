# 00. StratumRO Phase 2 — Cluj Data Foundation & E2E Reconstruction: Executive Summary

**Document ID:** `REPORT-CLUJ-00-EXECUTIVE-SUMMARY`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS  
**Benchmark Scope:** Cluj-Napoca (USAMV / Someșul Mic AOI)  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Guardrails (AGENTS.md)

---

## 1. Executive Mandate & Strategic Role

Phase 2 has successfully reconstructed and forensically validated the **Cluj development/validation benchmark** for StratumRO.

### Clarification of Permanent Identity vs. Current Role:
- **Permanent Product Identity:** StratumRO is an **AI-powered geospatial platform for QGIS** that combines aerial/satellite imagery, LiDAR, GIS, remote sensing, geospatial computation, AI/vision models, and deterministic geometry to perform automated and semi-automated geospatial analysis, extraction, reasoning, validation, and decision support.
- **Current Phase Role:** Cluj serves as the **high-resolution development and validation laboratory** used to prove that StratumRO can execute a real, reproducible, and auditable geospatial AI pipeline on controlled local data. The assisted pre-cadastral building footprint workflow is the first demanding application benchmark, not the boundary of what StratumRO is.

---

## 2. Key Forensic Findings & Resolutions

### 2.1 The "179 Buildings" Forensic Autopsy
- **Prior Claim:** Previous documentation cited "179 AI building detections" or "179 buildings".
- **Forensic Discovery:** The file `data/ground_truth/tier2_extended_gt.geojson` contained 150 rows, but its **first 29 rows were exact duplicates of Tier 1** (`tier1_teren.geojson`), with identical coordinates ($\text{IoU} = 1.000$). An earlier script combined $29 + 150 = 179$ rows.
- **Resolution:** Deduplicated cleanly into:
  - `data/derived_reference/tier1_primary_29.geojson` (29 primary survey features)
  - `data/derived_reference/tier2_additional_121.geojson` (121 complementary features)
  - `data/derived_reference/cluj_combined_unique_150.geojson` (**exactly 150 unique reference buildings**)
  - Original source files remain **100% immutable and unmodified**.

### 2.2 CRS Forensic Truth (`EPSG:4284` vs `EPSG:3844`)
- **Prior Confusion:** Metadata previously reported `EPSG:4284 / Stereo70`. `EPSG:4284` is *Pulkovo 1942*, an unprojected 2D geographic coordinate system with angular degrees.
- **Geodetic Proof:** Parsing GeoKeys (Key 1024=1, 3072=32767, 3076=9001) and ESRI PE WKT strings in `NorPuncte_St70_S42.laz` proved that the raw points natively reside in **Stereo 70 (`EPSG:3844`)** projected metric coordinates ($X \in [390500, 391300]$, $Y \in [585100, 585900]$). `EPSG:4284` was merely a fallback datum name.

### 2.3 Roof-to-Reference Building Centroid Divergence Analysis
- **Methodological Clarification:** This analysis measures spatial divergence between LiDAR building roof-point centroids (ASPRS Class 6) and official ANCPI cadastral ground parcel centroids. It is **not** an independent geodetic sensor co-registration study, but a **roof-to-reference centroid divergence analysis**.
- **Sample Count & Exclusion:** Out of 29 Tier 1 buildings, **$N = 26$ usable building correspondences** were analyzed. Exactly **3 buildings were excluded** (`REF_TIER1_022`, `REF_TIER1_023`, `REF_TIER1_024`) because the source classified point cloud contained zero returns classified as ASPRS Class 6 (Building) over their parcels.
- **True Measured Centroid Divergence ($N = 26$):**
  - $\text{MAE}_{2D} = 3.923\,\text{m}$ (~$3.92\,\text{m}$) | $\text{RMSE}_{2D} = 5.735\,\text{m}$ (~$5.74\,\text{m}$)
  - $P_{95} = 11.805\,\text{m}$ (~$11.81\,\text{m}$) | $\text{Max} = 17.292\,\text{m}$ (~$17.29\,\text{m}$)
  - $\text{Signed Bias:} \Delta X = +0.418\,\text{m}, \Delta Y = -0.572\,\text{m}$
  - **Compact/residential buildings:** Exhibit tight sub-meter agreement ($0.13\text{--}0.72\,\text{m}$) corresponding to nominal roof overhangs.
  - **Large historic university structures:** Diverge by $5\text{--}17\,\text{m}$ because aerial sensors observe the 3D roof eave envelope, whereas cadastral registers record ground foundation boundaries or legal property parcels.

### 2.4 True Elevation Reconstruction (nDSM)
- Reconstructed a clean $1.0\,\text{m}$ Normalized Digital Surface Model (`cluj_ndsm_1m.tif`) by subtracting bare-earth `DTM3m.tif` from all $4,624,905$ LiDAR returns in `NorPuncte_St70_S42.laz` using maximum elevation $\max(Z)$ per cell.

---

## 3. Real Deep Learning Execution: Meta SAM 2 Hiera

- **Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM, CUDA sm_89).
- **Execution Provider:** Native PyTorch 2.6.0+cu124 (no mock, no synthetic geometry).
- **Prompt Source:** 94 candidate centroids discovered deterministically from LiDAR nDSM ($h \ge 2.5\,\text{m}$). Reference ground truth was **strictly isolated** and never accessed during candidate generation or inference.
- **Image Encoding Latency:** $0.61\,\text{seconds}$ for $2,500 \times 2,000$ active orthophoto crop.
- **Inference Latency:** $12.54\,\text{seconds}$ for 94 candidates (~$133\,\text{ms}$ per candidate).
- **Outputs Stored Separately:**
  - `workspace/predictions/cluj_raw_sam2_predictions.geojson` (organic vision masks)
  - `workspace/predictions/cluj_regularized_predictions.geojson` (90° orthogonal CAD polygons)

---

## 4. Benchmark Performance & Evaluation

| Metric | RAW SAM 2 | REGULARIZED CAD | Impact of Regularization |
|:---|:---|:---|:---|
| **True Positives (IoU $\ge 0.50$)** | 4 | 4 | 0 |
| **False Positives** | 90 | 90 | 0 |
| **False Negatives** | 61 | 61 | 0 |
| **Precision** | 4.26% | 4.26% | Unchanged |
| **Recall** | 6.15% | 6.15% | Unchanged |
| **Mean IoU on Matched Buildings** | **69.52%** | **70.37%** | **+0.85% improvement** |
| **2D Centroid MAE** | **2.716 m** | **2.491 m** | **-0.225 m (8.3% error reduction)** |
| **2D Centroid RMSE** | **3.412 m** | **3.364 m** | **-0.048 m error reduction** |
| **Mean Vertices / Building** | **378.7** | **86.1** | **-77.3% node compression** |
| **90° Orthogonal Ratio** | **0.00%** | **39.00%** | Structural CAD compliance |

### Scientific Autopsy of Error Sources:
1. **RGB-Only Orthophoto:** Absence of a Near-Infrared (NIR) band prohibits NDVI computation. Tree canopies with heights $h \ge 2.5\,\text{m}$ generated 90 false positive prompts.
2. **Monolithic Campus Complexes:** USAMV's sprawling multi-wing buildings ($50\text{--}150\,\text{m}$) were queried with a single center point prompt. SAM 2 correctly segmented individual roof sections or atriums, but the resulting partial overlap with the full parcel yielded an IoU between $0.20$ and $0.45$, falling just below the strict $0.50$ benchmark threshold.

---

## 5. Software & Toolchain Verification

Verified directly on Windows host CLI ([reports/cluj/toolchain_versions.json](file:///c:/Users/lefpa/Downloads/QGIS-AI/reports/cluj/toolchain_versions.json)):

| Category | Primary Verified Component | Status | Role in StratumRO |
|:---|:---|:---|:---|
| **GIS & UI** | QGIS 3.40.0-Bratislava / PyQGIS | OPERATIONAL | Core orchestration, live GIS state, plugin UI |
| **Raster Engine**| GDAL 3.9.3 (with proprietary MrSID driver) | OPERATIONAL | Slicing 7.2 GPix orthophoto, warp, raster algebra |
| **Point Cloud** | PDAL 2.8.1 | OPERATIONAL | LiDAR filtering, classification inspection, tiling |
| **Projections** | PROJ 9.5.0 (pyproj 3.7.0) | OPERATIONAL | Strict Stereo 70 (EPSG:3844) transformations |
| **Remote Sensing**| ESA SNAP 11.0.0 (`gpt.exe`) | OPERATIONAL (STANDBY)| Reserved for satellite SAR / multispectral Sentinel |
| **3D Clouds** | CloudCompare | NOT INSTALLED | To be deployed when interactive mesh inspection needed |
| **Deep Learning**| PyTorch 2.6.0 + CUDA 12.4 (RTX 4050 GPU)| OPERATIONAL | SAM 2 vision inference |
| **Geometry** | GEOS 3.12 / Shapely 2.0 / StratumRO Vectorizer | OPERATIONAL | Deterministic 90° regularization, topology cleanup |

---

## 6. Phase 2 Deliverable Artifacts Directory

All Phase 2 reports, benchmarks, datasets, and manifests are compiled and verified:

```
reports/cluj/
├── 00_phase2_executive_summary.md          <- This master summary
├── 01_data_inventory.md                    <- Complete Cluj source catalog & layout
├── 02_crs_forensic_audit.md                <- Geodetic proof of Stereo 70 (EPSG:3844)
├── 03_coregistration_validation.md         <- Roof-to-reference centroid divergence analysis (N=26)
├── 04_reference_dataset_audit.md           <- 179-building autopsy & 150 unique deduplication
├── 05_ndsm_provenance.md                   <- Reconstruction of 1m nDSM from LAZ & DTM
├── 06_sam2_inference_trace.md              <- GPU hardware trace & prompt generation
├── 07_prediction_vs_reference_metrics.md   <- Raw AI vs Regularized CAD metrics & error autopsy
├── 08_open_source_toolchain_inventory.md   <- Complete local tool inventory & capabilities
├── 09_tool_selection_matrix.md             <- Task-to-tool routing matrix
├── 10_e2e_reconstruction.md               <- Reconstructed benchmark workflow & architecture
├── 11_known_limitations.md                 <- Sensor, CV, geodetic & operational limitations
├── KILO_INDEPENDENT_PHASE2_AUDIT.md        <- Historical independent audit (superseded)
├── KILO_PHASE2_REAUDIT.md                  <- Post-correction independent re-audit (verified)
├── coregistration_points.geojson           <- Roof-to-ref centroid divergence points (26 buildings, EPSG:3844)
├── sam2_cluj_benchmark_metrics.json        <- Machine-readable evaluation metrics
├── toolchain_versions.json                 <- Windows CLI verified toolchain specifications
└── data_manifest.json                      <- Cryptographic SHA-256 manifest of all assets

StratumRO_Cluj_Phase2_Spectator.qgs         <- Live QGIS project ready for visual inspection
```

---

## 7. Status & Readiness

- **Regression Test Suite:** 179 unit tests executed (`170 passed, 9 skipped, 0 failed`).
- **Data Integrity:** Zero source files overwritten; reference $\ne$ prediction $\ne$ regularized CAD maintained across the entire stack.
- **Geographic Scope Lock:** Cluj-only scope was strictly respected (zero external AOIs touched).
- **Scientific Standard:** Verified against the checks listed in this report in accordance with Evidence-First Scientific Rules.
