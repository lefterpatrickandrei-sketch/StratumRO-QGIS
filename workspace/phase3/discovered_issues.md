# Discovered Issues During Phase 3 Core Extraction

This document records architectural, code quality, or minor numerical curiosities discovered during forensic analysis and extraction in Phase 3. In accordance with §54 and §55 ("DO NOT CHANGE SCIENTIFIC BEHAVIOR DURING MIGRATION"), zero production code was altered to fix these items; they are cataloged here for subsequent evaluation in Phase 4 (Domain Packs) or future optimization cycles.

---

## 1. Acute Spike Removal Redundancy
- **Location:** `stratum_ro/vectorizer.py` lines 42-64 (`remove_acute_spikes`)
- **Observed Behavior:** The function handles Polygon exterior rings and strips acute spikes using interior angle thresholds (< 35°), but does not explicitly iterate over interior holes.
- **Evidence:** Extracted identically to `stratum_ro.core.geometry.regularizer.remove_acute_spikes`.
- **Impact:** Low; cadastral building boundaries in Cluj-Napoca dataset (`tier1_teren.geojson`) are primarily simple single-polygon envelopes without interior courtyards.
- **Baseline Status:** Golden baseline matches this exact behavior.
- **Recommended Future Phase:** Phase 4 / Cadastre Domain Pack enhancement.

---

## 2. TopoLT Layer String Constants Embedded in Algorithmic Code
- **Location:** `stratum_ro/cad_exporter.py`
- **Observed Behavior:** Cadastral DXF export logic is tightly coupled with hardcoded Romanian TopoLT layer names (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`).
- **Evidence:** Kept outside `stratum_ro/core/` in domain/top-level as required by §18 ("CADASTRAL LOGIC").
- **Impact:** None on Core isolation; confirms proper boundary placement for Phase 4.
- **Baseline Status:** Frozen in Phase 1 baseline.
- **Recommended Future Phase:** Phase 4 (Cadastre RO Domain Pack).

---

## 3. Coordinate Axis Order in Legacy GeoJSON Exporters
- **Location:** `engine/evaluation.py` & `stratum_ro/volumetric_3d.py`
- **Observed Behavior:** GeoJSON exports assume `[X, Y]` = `[East, North]` for EPSG:3844 (Stereo 70), adhering to OGC GeoJSON RFC 7946 specifications (`always_xy=True`).
- **Evidence:** Formally preserved in `stratum_ro.core.geodesy.transformer.CoreTransformer(always_xy=True)`.
- **Impact:** Zero drift.
- **Baseline Status:** Compliant with Stereo 70 geodetic conventions.
- **Recommended Future Phase:** Phase 4.
