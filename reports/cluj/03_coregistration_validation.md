# 03. Roof-to-Reference Building Centroid Divergence Analysis

**Audit Date:** 2026-09-19  
**Scope:** Spatial Centroid Divergence Analysis (LiDAR Roof Returns ↔ Official ANCPI Cadastral Footprints)  
**Standard:** Evidence-First Scientific Assessment — Methodological Precision & Error Decomposition  
**Output GeoJSON:** [`reports/cluj/coregistration_points.geojson`](file:///c:/Users/lefpa/Downloads/QGIS-AI/reports/cluj/coregistration_points.geojson) (Native CRS: `EPSG:3844`)

---

## 1. Executive Methodological Clarification

### Centroid Divergence vs. Geodetic Co-Registration
This analysis evaluates the spatial divergence between **LiDAR building roof-point centroids** (computed from ASPRS Class 6 returns) and **official cadastral reference building polygon centroids** (from ANCPI Tier 1 survey polygons).

> **Critical Methodological Distinction:**  
> This test is **NOT** an independent, survey-grade geodetic sensor-to-sensor co-registration test (which would require surveyed ground control targets, roof ridge intersection lines, or planar patch fitting). It is an empirical **roof-to-reference building centroid divergence analysis**.

Previous informal descriptions claimed "near-perfect alignment ($\Delta X \approx +6\text{ cm}$, $\Delta Y \approx -8\text{ cm}$)" based on signed mean cancellation. In signed averaging, positive and negative offsets cancel out, creating a misleading appearance of near-zero error.

---

## 2. Sample Filtering & Exclusion Criteria

Out of the **29 primary survey buildings** in `data/ground_truth/tier1_teren.geojson`:
- **Usable Correspondences Analyzed:** **$N = 26$ buildings**
- **Excluded Buildings:** **$3$ buildings** (`REF_TIER1_022`, `REF_TIER1_023`, `REF_TIER1_024`)

### Reason for Exclusion:
Direct binary inspection of `NorPuncte_St70_S42.laz` reveals that the bounding boxes of these three buildings contained **zero points classified as ASPRS Class 6 (Building)**:
1. `REF_TIER1_022` ($104.6\text{ m²}$): 1,205 total returns; classified as Ground (648), Low Veg (216), Med Veg (85), High Veg (254). **Class 6 = 0**.
2. `REF_TIER1_023` ($819.8\text{ m²}$): 9,299 total returns; classified as Ground (5,163), Low Veg (1,518), Med Veg (322), High Veg (2,295). **Class 6 = 0**.
3. `REF_TIER1_024` ($2,992.5\text{ m²}$): 44,431 total returns; classified as Ground (22,285), Low Veg (14,651), Med Veg (925), High Veg (6,563). **Class 6 = 0**.

Because the source flight classified points over these three parcels exclusively as ground and vegetation, no LiDAR roof returns existed to compute a valid roof centroid. They were therefore excluded from the centroid divergence calculation.

---

## 3. Authoritative Centroid Divergence Statistics ($N = 26$)

| Error Metric | Easting ($\Delta X$) | Northing ($\Delta Y$) | Planar 2D ($\Delta XY$) |
| :--- | :--- | :--- | :--- |
| **Sample Count ($N$)** | 26 usable buildings | 26 usable buildings | 26 usable buildings |
| **Signed Mean** | $+0.418\text{ m}$ | $-0.572\text{ m}$ | N/A |
| **Standard Deviation** | $3.056\text{ m}$ | $4.937\text{ m}$ | $3.978\text{ m}$ |
| **Mean Absolute Error (MAE)** | $2.167\text{ m}$ | $2.971\text{ m}$ | $\mathbf{3.923\text{ m}}$ (~$3.92\text{ m}$) |
| **Root Mean Square Error (RMSE)**| $3.025\text{ m}$ | $4.872\text{ m}$ | $\mathbf{5.735\text{ m}}$ (~$5.74\text{ m}$) |
| **Median (50th Percentile)** | $+0.121\text{ m}$ | $-0.136\text{ m}$ | $2.751\text{ m}$ (~$2.75\text{ m}$) |
| **95th Percentile ($P_{95}$)** | $6.485\text{ m}$ | $10.828\text{ m}$ | $\mathbf{11.805\text{ m}}$ (~$11.81\text{ m}$) |
| **Maximum Discrepancy** | $+7.160\text{ m}$ | $-16.002\text{ m}$ | $\mathbf{17.292\text{ m}}$ (~$17.29\text{ m}$) |
| **Positive Errors** | 14 buildings ($53.8\%$) | 17 buildings ($65.4\%$) | All positive |
| **Negative Errors** | 12 buildings ($46.2\%$) | 9 buildings ($34.6\%$) | N/A |

---

## 4. Physical & Geometric Root Cause Analysis

A spatial error autopsy across the $N = 26$ individual correspondences reveals two distinct structural regimes:

### Regime A: Compact, Isolated Structures (Sub-Meter Consistency)
For isolated, rectangular buildings where tree canopy does not contaminate the roof envelope:
- `REF_TIER1_011` ($143.1\text{ m²}$): $\Delta X = +0.02\text{ m}$, $\Delta Y = +0.13\text{ m} \rightarrow \mathbf{\text{Error}_{2D} = 0.13\text{ m}}$
- `REF_TIER1_009` ($148.5\text{ m²}$): $\Delta X = -0.05\text{ m}$, $\Delta Y = -0.27\text{ m} \rightarrow \mathbf{\text{Error}_{2D} = 0.28\text{ m}}$
- `REF_TIER1_013` ($92.2\text{ m²}$): $\Delta X = -0.21\text{ m}$, $\Delta Y = +0.29\text{ m} \rightarrow \mathbf{\text{Error}_{2D} = 0.36\text{ m}}$
- `REF_TIER1_015` ($37.1\text{ m²}$): $\Delta X = +0.56\text{ m}$, $\Delta Y = +0.21\text{ m} \rightarrow \mathbf{\text{Error}_{2D} = 0.60\text{ m}}$
- `REF_TIER1_017` ($1484.5\text{ m²}$): $\Delta X = +0.12\text{ m}$, $\Delta Y = +0.71\text{ m} \rightarrow \mathbf{\text{Error}_{2D} = 0.72\text{ m}}$

On un-occluded structures, the centroid divergence remains **sub-meter ($0.13\text{--}0.72\text{ m}$)**, reflecting nominal roof eave overhangs relative to ground foundation cadastral boundaries.

### Regime B: Sprawling Campus Complexes ($> 10\text{ m}$ Centroid Shifts)
The large discrepancies are concentrated in complex multi-wing university buildings (`REF_TIER1_029`, `REF_TIER1_025`, `REF_TIER1_028`):
1. **Tree Canopy Overhang & Misclassification:** Mature trees surrounding the university faculties overhang building wings. Points on those wings were classified into Class 5 (High Vegetation) rather than Class 6 (Building).
2. **Partial Roof Tier vs. Full Cadastral Parcel:** Ground truth polygons represent the full cadastral parcel boundary at ground level. In contrast, LiDAR Class 6 captures only an elevated central roof tier, pulling the roof return centroid away from the parcel centroid by $10\text{--}17\text{ m}$.
3. **Eave & Facade Projections:** High vertical walls and multi-pitch roofs introduce geometric offsets between nadir LiDAR roof points and ground parcel outlines.

---

## 5. Engineering Conclusions & Safeguards

1. **Global Projection Consistency:** There is **no global datum translation error** (e.g. no 100–200 m offset between S-42 and WGS84). Both LiDAR and reference vectors reside natively in metric Stereo 70 (`EPSG:3844`).
2. **LiDAR Prompting Safeguard:** Because LiDAR building classification (Class 6) is incomplete over complex campus structures (omitting buildings 022, 023, 024 and occluded wings), candidate extraction must not rely exclusively on Class 6. The normalized Digital Surface Model ($\text{nDSM} \ge 2.5\text{ m}$) capturing **all non-ground elevations** must be used as the candidate discovery layer.
3. **Validation Export:** Point features with individual $\Delta X, \Delta Y, \text{Error}_{2D}$ and attributes are exported to `reports/cluj/coregistration_points.geojson` with explicit CRS **`EPSG:3844`** for visual inspection in QGIS.
