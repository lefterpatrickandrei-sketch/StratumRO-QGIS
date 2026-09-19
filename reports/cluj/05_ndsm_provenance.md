# 05. nDSM RECONSTRUCTION & PROVENANCE REPORT

**Audit Date:** 2026-09-19  
**Scope:** Normalized Digital Surface Model ($\text{nDSM}$) Provenance, Validation, and Deterministic Reconstruction  
**Generated File:** [`workspace/derived/cluj_ndsm_1m.tif`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/derived/cluj_ndsm_1m.tif)  
**Standard:** 100% Traceable Mathematical Derivation (AGENTS.md)

---

## 1. Provenance Trace of Existing Cached nDSM
An audit of `workspace/e2e/03_ndsm/ndsm_stereo70.tif` was conducted:
- **Spatial Resolution:** $1.0\text{ m} \times 1.0\text{ m}$ ($1044 \times 897\text{ pixels}$).
- **CRS:** `EPSG:3844` (Stereo 70).
- **Bounding Box:** $X \in [390478.54, 391522.54]$, $Y \in [584980.66, 585877.66]$.
- **Origin:** Traced to `stratum_ro.lidar_processor.LidarProcessor`.
- **Status:** Valid, but previously lacked formal machine-readable provenance.

---

## 2. Deterministic Reconstruction Workflow
To eliminate incomplete provenance, the nDSM was cleanly re-derived from raw inputs using `stratum_ro/lidar_processor.py`:

```text
NorPuncte_St70_S42.laz (LiDAR Point Cloud)
   ├── ASPRS Class 2 (Ground) ───────────────┐
   └── Maximum Z per 1.0m cell (DSM) ────────┼──> nDSM = DSM - DTM ──> workspace/derived/cluj_ndsm_1m.tif
                                             │
DTM3m.tif (Bare-Earth Elevation Grid) ───────┘ (Bilinear Resampling 3m -> 1m)
```

### Mathematical Formulation:
1. **Digital Surface Model ($\text{DSM}$):**
   $$\text{DSM}(x, y) = \max_{p_i \in \text{Cell}(x, y)} Z_i$$
   where $p_i$ represents **all valid LiDAR returns** (all $4,624,905$ points in `NorPuncte_St70_S42.laz`) within the $1.0\text{ m} \times 1.0\text{ m}$ horizontal grid cell. Using all returns guarantees maximum envelope capture regardless of return number metadata. Void cells inherit the local DTM bare-earth elevation ($\text{DSM} = \text{DTM}$), ensuring $\text{nDSM} = 0.0\text{ m}$ over un-sampled terrain.
2. **Digital Terrain Model ($\text{DTM}$):**
   Derived by bilinear interpolation of `DTM3m.tif` to the $1.0\text{ m}$ cell centers.
3. **Normalized Height Model ($\text{nDSM}$):**
   $$\text{nDSM}(x, y) = \max\left(0.0, \, \text{DSM}(x, y) - \text{DTM}(x, y)\right)$$

---

## 3. Physical Validation & Statistical Properties
- **Raster Dimensions:** $1044\text{ columns} \times 897\text{ rows}$.
- **Cell Size:** Exactly $1.000\text{ m} \times 1.000\text{ m}$.
- **Coordinate Extent:** Left=$390478.54$, Bottom=$584980.66$, Right=$391522.54$, Top=$585877.66$.
- **Height Threshold Distribution:**
  - Above-ground pixels ($h \ge 2.5\text{ m}$): **349,523 cells** ($37.3\%$ of AOI).
  - Ground / sub-threshold pixels ($h < 2.5\text{ m}$): **586,945 cells** ($62.7\%$).
  - Maximum detected structure height: $170.1\text{ m}$ (tall communication mast/tower).
- **Physical Plausibility:** Building roof plateaus exhibit characteristic flat/pitched signatures between $6.0\text{ m}$ and $25.0\text{ m}$ above local ground level, aligning with campus building heights.

---

## 4. Operational Role in Candidate Generation
The reconstructed `workspace/derived/cluj_ndsm_1m.tif` serves as the primary **unbiased candidate generator**:
- Identifies potential building locations based strictly on physical height above ground ($h \ge 2.5\text{ m}$, area $25.0\text{ m²} \le \text{Area} \le 8000.0\text{ m²}$).
- Supplies bounding box and centroid prompts to the Meta SAM 2 optical segmentation engine **without reading or leaking Ground Truth vectors**.
