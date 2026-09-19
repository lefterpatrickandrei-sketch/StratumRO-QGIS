# Experiment Analysis — EXP_000: Frozen Baseline Reproduction

## 1. Experiment Overview
- **Experiment ID:** `EXP_000`
- **Hypothesis:** Re-executing the frozen Phase 2 pipeline reproduces identical baseline metrics (4 TP / 90 FP / 61 FN).
- **Intervention:** None (control condition).
- **Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (CUDA).

## 2. Quantitative Results
- **Candidates Detected:** 94
- **Raw Predictions:** 94
- **Reference Buildings in AOI:** 65
- **Detection Metrics:**
  - True Positives (TP): 4
  - False Positives (FP): 90
  - False Negatives (FN): 61
  - Precision: 4.26%
  - Recall: 6.15%
  - F1 Score: 5.03%
- **Segmentation Metrics:**
  - RAW Mean IoU: 69.52% (Median: 69.38%)
  - REGULARIZED Mean IoU: 70.37% (Median: 69.40%)
- **Geometry Metrics:**
  - RAW Centroid MAE 2D: 2.72 m (RMSE: 3.41 m)
  - REGULARIZED Centroid MAE 2D: 2.49 m (RMSE: 3.36 m)

## 3. Failure Mode Diagnosis
1. **Vegetation Intrusion:** High vegetation (LiDAR class 5) accounts for ~41% of points in AOI. Trees with height >= 2.5m formed 70+ of the 94 candidate blobs.
2. **Point Prompt Localization:** Centroid point prompt on multi-wing complexes prompted SAM 2 to delineate only small homogeneous roof facets rather than the entire building envelope, causing partial segmentations with IoU < 0.50.
3. **Absence of Morphological Closure:** Skylights, mechanical units, and roof pitch variations fragmented single buildings into disjoint components.

## 4. Decision Gate
- **Status:** BASELINE FROZEN (Benchmark Control).
