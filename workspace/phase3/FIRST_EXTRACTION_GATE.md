# STRATUMRO — FIRST EXTRACTION GATE (SUBSYSTEM 1: GEOMETRY)

**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Phase:** Phase 3 — First Subsystem Extraction Authorization  
**Target Component:** Computational Geometry & Regularization  
**Audit Standard:** 8 Evidence-First Scientific Rules (AGENTS.md §3)  
**Date:** 2026-09-20  

---

## 1. SPECIFICAȚIA PORȚII DE PRIMĂ EXTRAGERE

- **Modul Sursă:** `stratum_ro/vectorizer.py` & `engine/evaluation.py`
- **Simboluri de Extras:**
  1. `_extract_largest_polygon(geom)`
  2. `remove_acute_spikes(poly, min_angle_deg)`
  3. `count_macro_reflex_corners(poly, min_edge_len, tol_deg)`
  4. `compute_orthogonality_ratio(poly, min_edge_len, tol_deg)`
  5. `orthogonalize_cad(poly, tolerance)`
  6. `calculate_iou(poly1, poly2)`
  7. `calculate_hausdorff_distance(geom1, geom2)`
  8. `calculate_boundary_rmse(cand, ref, step)`
  9. `calculate_centroid_shift(poly1, poly2)`
- **Contract Asociat:** `IGeometryEngine` (`stratum_ro/contracts/geometry.py`)
- **Dependențe Directe:** `shapely`, `numpy`, `scipy`, `math`. (Zero QGIS, Zero UI, Zero LLM).
- **Locație Țintă Core:** `stratum_ro/core/geometry/`
  - `stratum_ro/core/geometry/regularizer.py`
  - `stratum_ro/core/geometry/metrics.py`
- **Strategie Retrocompatibilitate (Compatibility Wrapper):**
  - În `stratum_ro/vectorizer.py`, simbolurile mutate vor fi importate și re-exportate direct din `stratum_ro.core.geometry.regularizer`:
    ```python
    from stratum_ro.core.geometry.regularizer import (
        _extract_largest_polygon,
        remove_acute_spikes,
        count_macro_reflex_corners,
        compute_orthogonality_ratio,
        orthogonalize_cad
    )
    ```
  - Astfel, orice cod client vechi (`from stratum_ro.vectorizer import orthogonalize_cad`) va funcționa 100% neschimbat.
- **Riscuri Științifice:**
  - Modificarea coordonatelor la regularizare sau alterarea suprafețelor calculate.
  - *Atenuare:* Testarea strictă pe cazurile de aur din `golden_geometry_baseline.json` cu toleranță de $0.000\text{ mm}$.
- **Teste de Verificare a Porții:**
  1. `test_geometry_golden.py` (Cele 12 tipologii geometrice de aur existente).
  2. `test_vectorizer.py` (Testele unitare existente ale vectorizatorului).
  3. `test_contracts.py` (Verificarea contractelor).
  4. `test_phase1_golden_freeze.py` (Verificarea imuabilității datelor Ground Truth și a determinismului).
- **Plan de Rollback:**
  - Dacă apar regresii în teste, restaurarea `stratum_ro/vectorizer.py` din backup-ul git (`git checkout -- stratum_ro/vectorizer.py`) și ștergerea `stratum_ro/core/geometry/`.

---

**POARTĂ APROBATĂ PENTRU EXTRAGEREA SUBSISTEMULUI 1 (GEOMETRY).**
