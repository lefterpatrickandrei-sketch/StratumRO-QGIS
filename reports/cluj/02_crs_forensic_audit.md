# 02. CRS FORENSIC AUDIT REPORT

**Audit Date:** 2026-09-19  
**Scope:** Geodetic Reference Resolution & Ambiguity Elimination (Cluj AOI)  
**Standard:** Rigorous Mathematical Geodesy — Evidence-First Standard (AGENTS.md)

---

## 1. Executive Determination: The EPSG:4284 vs EPSG:3844 Resolution

### Critical Finding
The statement `"Stereo70 (EPSG:4284/S42)"` in previous informal documentation is **GEODETICALLY ERRONEOUS** and is hereby formally corrected.

- **`EPSG:4284` is a GEOGRAPHIC 2D COORDINATE REFERENCE SYSTEM:**
  - Name: `Pulkovo 1942`
  - Units: **Angular Degrees** (Latitude, Longitude)
  - Datum: `Pulkovo 1942` (Krassowsky 1940 ellipsoid)
  - Projection: **NONE** (unprojected ellipsoidal coordinates)
- **`EPSG:3844` is a PROJECTED 2D COORDINATE REFERENCE SYSTEM:**
  - Name: `Pulkovo 1942(58) / Stereo70`
  - Units: **Linear Metres** (Easting, Northing)
  - Projection: Oblique Stereographic (Stereo 70)
  - Parameters: Latitude of Origin $46^\circ\text{N}$, Central Meridian $25^\circ\text{E}$, Scale Factor $0.99975$, False Easting $500,000\text{ m}$, False Northing $500,000\text{ m}$.

### Root Cause of Previous Tool Misidentification
When inspecting `NorPuncte_St70_S42.laz` with Python `laspy`, the library reported `EPSG:4284`. Forensic byte inspection of VLR record `34735` (GeoKeyDirectoryTag) revealed the exact reason:
1. `GeoKey 1024 (GTModelTypeGeoKey) = 1` $\rightarrow$ **`ModelTypeProjected`** (Projected metric system).
2. `GeoKey 2048 (GeographicTypeGeoKey) = 4284` $\rightarrow$ Specifies the underlying geodetic datum (`GCS_Pulkovo_1942`).
3. `GeoKey 3072 (ProjectedCSTypeGeoKey) = 32767` $\rightarrow$ **`User-Defined Projection`**.
4. `GeoKey 3076 (ProjLinearUnitsGeoKey) = 9001` $\rightarrow$ **`Linear_Meter`**.
5. `GeoAsciiParamsTag (VLR 34737)` explicitly stores the projection definition:
   ```text
   ESRI PE String = Projection STEREO70
   Datum          S-42_ROMANIA
   Zunits         NO
   Units          METERS
   Xshift         0.000000
   Yshift         0.000000
   Parameters
   ```

Because legacy ESRI software wrote `GeoKey 3072 = 32767` instead of standard EPSG code `3844`, naive LAS readers ignore the projected ASCII string and fall back to reporting `GeoKey 2048` (`EPSG:4284`).

**Final Scientific Conclusion:**  
The coordinates stored in `NorPuncte_St70_S42.laz` are linear metric values ($X \approx 390,500\text{ m}$, $Y \approx 585,000\text{ m}$) projected in **Romania Stereo 70 (`EPSG:3844`)** on the Pulkovo 1942 / S-42 datum. **They are NOT degrees.**

---

## 2. Product-by-Product CRS Matrix

| Product | File Tested | Header CRS String | Detected Datum | Ellipsoid | Coordinate Units | Authoritative Projected CRS |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Airborne LiDAR** | `NorPuncte_St70_S42.laz` | `ModelTypeProjected`, `GeoKey 2048=4284`, `ESRI PE STEREO70` | S-42 / Pulkovo 1942 | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |
| **DTM Grid** | `DTM3m.tif` | `LOCAL_CS["ESRI PE String = Projection STEREO70, Datum S-42_ROMANIA"]` | S-42 / Pulkovo 1942 | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |
| **MrSID Orthophoto**| `Orto Cluj-*.sid` + `.sdw` | World files: origin `390529.38 m`, pixel size `0.011651 m` | S-42 / Pulkovo 1942 | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |
| **CAD Breaklines** | `Somes_dtm_*.dwg` | Kilometer grid coordinates `390_585` | S-42 / Pulkovo 1942 | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |
| **Global Mapper** | `COAJE LUCRU DATE.gmw` | `Projection STEREO70, Datum S-42_ROMANIA, Units METERS` | S-42 / Pulkovo 1942 | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |
| **Ground Truth Tier 1**| `tier1_teren.geojson` | `urn:ogc:def:crs:EPSG::3844` | Pulkovo 1942(58) | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |
| **Ground Truth Tier 2**| `tier2_extended_gt.geojson` | `urn:ogc:def:crs:EPSG::3844` | Pulkovo 1942(58) | Krassowsky 1940 | Metres | **EPSG:3844 (Stereo 70)** |

---

## 3. Geodetic Datum & Transformation Parameters

In Romanian geodetic engineering (ANCPI regulations):
- **Datum:** S-42 (Romania) / Pulkovo 1942(58)
- **Ellipsoid:** Krassowsky 1940 ($a = 6,378,245.0\text{ m}$, $1/f = 298.3$)
- **Official Projection:** Oblique Stereographic (Stereo 70)
- **EPSG Code:** `EPSG:3844`
- **Official 7-parameter Helmert transformation to WGS84 / ETRS89 (`EPSG:4937`):**
  - $\Delta X = +2.3290\text{ m}$
  - $\Delta Y = -147.0416\text{ m}$
  - $\Delta Z = -92.0802\text{ m}$
  - $R_X = +0.3092483''$
  - $R_Y = -0.3248219''$
  - $R_Z = +0.4972993''$
  - Scale factor $S = +5.689062\text{ ppm}$

**Audit Outcome:** All primary input files in the Cluj development benchmark are inherently in the **same projected metric coordinate system (`EPSG:3844`)**. No on-the-fly datum reprojection is required or permitted between the orthophoto, LiDAR, DTM, and reference GeoJSON.
