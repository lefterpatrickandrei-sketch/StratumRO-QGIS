# 11. Known Limitations & Forensic Risk Register (Cluj AOI)

**Document ID:** `REPORT-CLUJ-11-KNOWN-LIMITATIONS`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 2 Benchmark  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (UNBIASED, VERIFIED, DEFENSIBLE)

---

## 1. Executive Summary

A core principle of StratumRO's engineering governance is **intellectual honesty**: never mask technical deficiencies or operational limitations behind marketing claims.

This report establishes the complete register of physical, geodetic, computational, and data limitations discovered during the Phase 2 Cluj benchmark audit.

---

## 2. Sensor & Radiometric Limitations

### 2.1 Absence of Near-Infrared (NIR) Band (RGB-Only Constraint)
- **Finding:** The Cluj MrSID orthophoto contains exactly 3 spectral channels (Red, Green, Blue). It does not include an 800–900 nm Near-Infrared (NIR) band.
- **Consequence:** It is impossible to compute the standard Normalized Difference Vegetation Index:
  $$\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}$$
- **Operational Impact:** Dense tree canopies in the USAMV arboretum and Someș river corridor have high elevations ($h > 2.5\,\text{m}$) in the LiDAR nDSM. Without NIR, optical candidate selection produces false positives on tree clumps where green leaves mimic green metal or asphalt roof textures.

### 2.2 Proprietary MrSID Encoding & Driver Dependency
- **Finding:** The original $7.2\,\text{Gigapixel}$ imagery is compressed in LizardTech MrSID Generation 3/4 (`.sid`).
- **Consequence:** Open-source Python wheels (`pip install gdal`) lack the proprietary MrSID DSDK decode library. Access is only possible via QGIS's bundled GDAL runtime (`C:\Program Files\QGIS 3.40.0\bin\gdal_MrSID.dll`).
- **Mitigation:** Production pipelines must either run inside PyQGIS / QGIS Processing or pre-transcode `.sid` rasters into open Cloud-Optimized GeoTIFF (COG) with Deflate or ZSTD compression.

### 2.3 Flight Acquisition Coverage Gap (Missing Tile 2-2)
- **Finding:** The Cluj delivery folder contains 8 tiles (`1-1, 1-2, 1-3, 2-1, 2-3, 3-1, 3-2, 3-3`). Tile `2-2` is physically missing.
- **Consequence:** The central urban strip in row 2 contains a data void. Any pipeline assuming a complete $3 \times 3$ mosaic grid will fail if tile `2-2` is requested.

---

## 3. Computer Vision & Model Architecture Limitations

### 3.1 Single-Point Prompt Failure on Sprawling Multi-Wing Complexes
- **Finding:** The USAMV campus features interconnected architectural complexes (e.g. main university palace, veterinary clinics) spanning $50\text{--}150\,\text{m}$ with varying roof pitches, zinc sheets, and glass atriums.
- **Consequence:** A single point prompt placed at the mass centroid of an elevated nDSM cluster prompts zero-shot SAM 2 to segment only the homogeneous local roof facet containing that pixel.
- **Benchmark Impact:** The segmented mask covers only $25\%\text{--}40\%$ of the massive ground truth cadastral polygon, causing the IoU to drop below the $0.50$ PASCAL VOC threshold, falsely registering as a False Negative + False Positive pair.
- **Phase 3 Resolution:** Implement multi-point prompt grids and LiDAR 2D bounding box prompts.

### 3.2 Glasshouse LiDAR Penetration
- **Finding:** University research greenhouses exhibit low or noisy elevation in `NorPuncte_St70_S42.laz` because laser pulses transmit through glass panes or reflect off internal plant beds.
- **Consequence:** Greenhouses fail the $h \ge 2.5\,\text{m}$ nDSM threshold and are omitted from candidate generation.

---

## 4. Geodetic & Cadastral Discrepancies

### 4.1 Roof Eave Centroid vs. Cadastral Foundation Parcel Divergence
- **Physical Reality:** Remote sensing (aerial photography and LiDAR) observes the **roof envelope** (eaves, overhangs, gutters, and cantilevers).
- **Legal Cadastre:** ANCPI Cadastral plans (`1CC`) represent the **building foundation wall footprint** at ground contact or the boundary of the land parcel.
- **Measured Discrepancy ($N = 26$):**
  - Residential and compact buildings exhibit $0.13\text{--}0.72\,\text{m}$ physical overhang offsets.
  - Large historic university structures with multi-story porticos, sloped mansards, and stepped entrances exhibit $5\text{--}17\,\text{m}$ centroid divergence between legal cadastral land parcels and 3D roof centers.
  - Three buildings (`REF_TIER1_022`, `023`, `024`) had zero returns classified as ASPRS Class 6 (Building) in the source flight and could not be evaluated for roof centroid.
- **Governance Mandate:** A machine learning model predicting roof eaves can never achieve $0.00\,\text{cm}$ cadastral foundation agreement without a deterministic eave-retraction algorithm.

### 4.2 Unregistered Physical Structures ("Cadastral Incompleteness")
- **Finding:** Visual inspection confirmed that multiple "False Positives" identified by SAM 2 are real physical buildings (detached garages, metal storage sheds, security booths, transformer enclosures).
- **Consequence:** The official cadastral reference dataset is not an exhaustive physical building census; it is a legal property register. Evaluating physical vision models against legal registers naturally depresses nominal precision.

### 4.3 Filesystem Timestamp Interpretation (US vs. European Date Format)
- **Forensic Finding:** Third-party inspection noted file modification dates for `tier1_teren.geojson` (`9/10/2026`) and `tier2_extended_gt.geojson` (`9/11/2026`) as seemingly appearing in October/November 2026.
- **Technical Resolution:** Windows PowerShell outputs timestamps in standard US format (`M/D/YYYY`):
  - `9/10/2026` represents **September 10, 2026** (8 days prior to audit).
  - `9/11/2026` represents **September 11, 2026** (7 days prior to audit).
  Neither file carries future timestamps. Both files remain strictly immutable with identical byte lengths and verified cryptographic SHA-256 hashes.

---

## 5. Operational Positioning & Legal Scope

### 5.1 No Autonomous Legal Registration
- **Strict Limitation:** StratumRO is an **assisted pre-cadastral digitization and quality-control tool**. It does **NOT** constitute an autonomous legal cadastral registration engine.
- Under Romanian legislation (**ANCPI Ordinul nr. 600/2023**), cadastral documentations (PAD) require verification, field check, and digital signature by a certified geodetic engineer (*persoană fizică/juridică autorizată*).
- Outputs from StratumRO must be treated as digitized drafting proposals subject to licensed surveyor review.
