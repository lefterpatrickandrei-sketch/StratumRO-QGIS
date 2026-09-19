# 01. Baseline Reproduction & Benchmark Control (E0)

**Document ID:** `REPORT-CLUJ-P3-01-BASELINE-REPRO`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (REPRODUCED, MEASURED)

---

## 1. Purpose of the Frozen Baseline

Before testing any algorithmic modifications in Phase 3, the exact Phase 2 pipeline was executed and preserved as a control condition (`E0`).

The baseline artifacts are permanently isolated in:
```text
reports/cluj/phase3/baseline/
├── baseline_config.json
├── baseline_metrics.json
├── baseline_run.log
└── baseline_manifest.json
```

---

## 2. Quantitative Baseline Verification

Re-executing `tools/run_authentic_sam2_cluj_pipeline.py` from commit `4c1497a` produced identical values:

| Parameter / Metric | Measured Baseline Value | Verification Source |
|:---|:---|:---|
| **Candidates Generated** | 94 | `reports/cluj/phase3/baseline/baseline_metrics.json` |
| **Raw AI Predictions** | 94 | `workspace/phase3/predictions/EXP_000_baseline_raw.geojson` |
| **Regularized Predictions** | 94 | `workspace/phase3/predictions/EXP_000_baseline_reg.geojson` |
| **Reference Buildings in AOI** | 65 | `data/derived_reference/cluj_combined_unique_150.geojson` |
| **True Positives (TP)** | 4 | `_evaluate_against_reference` (IoU >= 0.50) |
| **False Positives (FP)** | 90 | Unmatched candidate blobs |
| **False Negatives (FN)** | 61 | Unmatched reference buildings |
| **Precision** | 4.26% | $4 / (4 + 90)$ |
| **Recall** | 6.15% | $4 / (4 + 61)$ |
| **F1 Score** | 5.03% | Harmonic mean of P and R |
| **RAW Mean IoU** | 69.52% | Evaluated across 4 matched TPs |
| **REGULARIZED Mean IoU** | 70.37% | Post 90° regularization |
| **RAW Centroid MAE 2D** | 2.72 m | Metric offset in Stereo 70 |
| **REGULARIZED Centroid MAE 2D** | 2.49 m | Metric offset in Stereo 70 |
| **Total Pipeline Runtime** | 13.15 s | CUDA execution on RTX 4050 |

---

## 3. Input Data Checksum Manifest

All source and derived rasters were hashed using SHA-256 to guarantee zero silent modification:

- `active_ortho_crop.tif`: `6ff38a8e3bf27c62b53f6630f7b99335f6087d0c345b53d45c81f335b2e3bc0a`
- `cluj_ndsm_1m.tif`: `f9c15ff93bf73cb1d43997f7fa20ce5b0e513511ebfa374092b775438865518b`
- `sam2_hiera_tiny.pt`: `2fe4017646548f074d262d294697fc5d00344d5cf30cb1056efec88ea6fae726`
- `cluj_combined_unique_150.geojson`: `47b2c0eeb04470bc506b3a24694fbfa27725832a82da6423450e1efb54a2a4ee`

---

## 4. Conclusion
The Phase 2 baseline is **100% reproduced** and provides an indisputable benchmark control for evaluating Phase 3 interventions.
