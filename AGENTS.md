# AGENTS.md — StratumRO Engineering & Evidence-First Governance Guide

## 1. Project Identity & Purpose
**StratumRO** is an industrial-grade geomatics and MLOps platform developed for automated building footprint extraction, 90-degree orthogonal regularization, 3D volumetric extrusion, and planar partitioning in Romania's official projection **Stereo 70 (EPSG:3844)**, conforming to **ANCPI Ordinul nr. 600/2023**.

> **Defensible Positioning:** StratumRO is an **assisted pre-cadastral workflow** that accelerates manual digitization by ~89%. It is **NOT** a fully autonomous legal registration system. Official cadastral registration requires validation and sign-off by a licensed geodetic surveyor (*persoană autorizată ANCPI*).

---

## 2. Codebase Map & Source of Truth
* **Core Implementation:** [`stratum_ro/`](stratum_ro/)
  - `vectorizer.py`: 90° regularization, canonical 4-vertex rectangle fitting, topology cleanup, planar partition.
  - `cad_exporter.py`: TopoLT standard CAD export (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`), automated PAD coordinate table drawing, `.CP` interchange file generation.
  - `volumetric_3d.py`: True 3D LoD1 solid shell extrusion (`MultiPolygonZ` in GeoPackage), RANSAC 3D roof plane fitting, OGC CityJSON v1.1 export.
  - `onnx_engine.py`: Cross-platform ONNX Runtime inference wrapper with DirectML (DirectX 12 GPU on Windows) and multithreaded CPU fallback.
  - `processing_provider.py` & `cadastral_algorithm.py`: QGIS Processing Framework integration (`StratumROCadastralAlgorithm`).
  - `stratum_ro_dockwidget.py` & `stratum_ro.py`: PyQGIS desktop plugin GUI and dockwidget.
  - `lidar_processor.py` & `ortho_extractor.py`: Airborne LiDAR (LAS/LAZ) processing, nDSM generation, and orthophoto VRT slicing.
* **Evaluation & Audits:** [`engine/`](engine/)
  - `evaluation.py`: Rigorous geodetic evaluation metrics (IoU, Hausdorff Distance, Boundary RMSE, Centroid Shift, PASCAL/COCO matching, Wilson score confidence intervals).
  - `ablation_study.py`: Formal 5-configuration ablation study (Configs A through E).
* **Automated Test Suite:** [`stratum_ro/test/`](stratum_ro/test/)
  - 40 unit tests covering vectorization, CAD export, TopoLT layers, PAD tables, .CP export, ONNX wrappers, 3D extrusion, and QGIS Processing metadata.
* **Ground Truth & Reference Data:** [`data/ground_truth/`](data/ground_truth/)
  - Official reference datasets, including `tier1_teren.geojson` (29 real cadastral buildings in Stereo 70).
* **Official Reports:** [`reports/`](reports/) & [`docs/`](docs/)
  - Quality gate verification, audit resolutions, and architectural documentation.

---

## 3. The 8 Evidence-First Scientific Rules (MANDATORY)

For every technical claim, benchmark result, or metric, agents must classify it into exactly one of:

1. **IMPLEMENTED:** Code exists on disk and is importable.
2. **TESTED:** Automated unit or regression tests executed cleanly with reported exit code.
3. **REPRODUCED:** Independently re-executed on a clean environment, reproducing identical numbers.
4. **MEASURED:** An empirical numerical value exists from a specific script execution.
5. **VALIDATED:** Compared against an appropriate independent reference dataset.
6. **FIELD-VALIDATED:** Verified against ground-truth terrestrial survey coordinates (e.g., GNSS RTK, Total Station). *Never claim field validation without physical terrestrial survey logs!*
7. **THEORETICAL:** Expected mathematically (e.g. algebraic Procrustes residual, geometric extrusion), but not yet empirically proven in the field.
8. **UNVERIFIED:** Claim exists in text or previous audits, but cannot be reproduced from current code/data.

---

## 4. Working Conventions & Anti-Hallucination Guardrails
- **No Blind Feature Inflation:** Never add new features, frameworks, or dependencies merely because they sound impressive. Make StratumRO **more trustworthy**, not just larger.
- **Never Hide False Positives:** The 116 False Positives relative to the 29-building reference set represent adjacent unannotated structures, outbuildings, or tree canopies. Report all 3 denominators explicitly (TP, matched references, total predictions).
- **No Unsupported Accuracy Claims:** A mathematical transformation consistency (e.g. Helmert residual = 0.0000 m) is **NOT** a proof of absolute zero-centimeter cadastral accuracy on the ground.
- **Honest ONNX Status:** The ONNX engine currently provides execution provider management (DirectML/CPU) and geometric fallbacks. Real end-to-end SAM2 ONNX model weights require separate conversion and numerical validation against PyTorch before claiming full equivalence.
- **Testing Standard:** When modifying code, always execute:
  ```bash
  venv\Scripts\python -m unittest discover stratum_ro/test
  ```
  Report the exact test count (e.g., `40 passed, 8 skipped, 0 failed`). A skipped test is **NOT** a passed test.
- **Python Environment:** Always use the local virtual environment in [`venv/`](venv/).
