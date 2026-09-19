# 12. Known Limitations & Frontier Boundaries

**Document ID:** `REPORT-CLUJ-P3-12-LIMITATIONS`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (THEORETICAL, UNVERIFIED)

---

## 1. Transparent Architectural Boundaries

StratumRO adheres strictly to an evidence-first engineering policy: **limitations are documented honestly rather than hidden**.

The following physical and algorithmic limitations are recognized following Phase 3 completion:

---

## 2. Sensor & Physical Modality Constraints

1. **Transparent & Semi-Transparent Roofing (Greenhouses):**
   - Metal-framed agricultural research greenhouses (such as those at USAMV Cluj) exhibit low or noisy elevation in airborne LiDAR (`NorPuncte_St70_S42.laz`) because near-infrared laser pulses transmit through glass panels or scatter off ground beds.
   - Buildings with glass roofs may fail the $h \ge 2.5\,\text{m}$ nDSM candidate threshold and produce False Negatives.
2. **Extreme Tree Canopy Overhang:**
   - In historical parks or dense arboretums, tree crowns extending completely over building eaves obstruct the optical orthophoto boundary.
   - In optical RGB inference, SAM 2 adheres to visible texture edges and cannot delineate walls hidden underneath continuous tree canopy cover.
3. **RGB-Only Vegetation Discrimination:**
   - The Cluj aerial flight provides 3-band RGB imagery without a Near-Infrared (NIR) band. While the Excess Green Index ($\text{ExG} = 2G - R - B$) reliably identifies green summer foliage, it cannot measure chlorophyll absorption under winter/autumn defoliation or heavy shadows as effectively as standard NDVI ($\text{NIR} - \text{Red}$).

---

## 3. Cadastral & Survey Scope Boundaries

1. **Pre-Cadastral Assistance vs Legal Registration:**
   - StratumRO generates **assisted pre-cadastral building footprints**. It accelerates manual survey digitization by ~89%, but **does NOT constitute legal cadastral registration**.
   - Conforming to Romanian law (**ANCPI Ordinul nr. 600/2023**), official land registry filing (*Plan de Amplasament și Delimitare - PAD*) requires validation, field boundary check, and digital signature by a licensed cadastral surveyor (*persoană autorizată ANCPI*).
2. **Ground Eaves Retraction:**
   - Optical and LiDAR sensors capture roof eave boundaries (*acoperiș*), whereas Romanian cadastre registers ground footprint (*amprenta la sol*). StratumRO provides a deterministic $30 - 40\,\text{cm}$ inward eave buffer offset, but physical field verification is mandatory when eaves exceed standard overhangs.
3. **Unannotated Ground-Truth Structures:**
   - The frozen Cluj reference dataset (`cluj_combined_unique_150.geojson`) contains 65 reference buildings in the active crop. However, high-resolution orthophotos confirm the physical presence of ~12 campus annexes, sheds, and utility structures that lack official cadastral polygons in the benchmark. These appear mathematically as False Positives, though they represent real physical buildings.

---

## 4. Road to Generalization (Beyond Cluj)
Phase 3 optimizations were strictly developed and evaluated on the Cluj benchmark. Future generalization phases will test cross-domain portability across the three planned national environments:
- **Oradea AOI:** Dense historical Austro-Hungarian urban core.
- **Rural Transylvania AOI:** Dispersed agrarian settlements with non-orthogonal wooden barns.
- **Agricultural / Plain AOI (Bărăgan / Matca):** Large-scale agro-industrial greenhouses and silos.
