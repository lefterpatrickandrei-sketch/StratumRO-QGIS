# Experiment Analysis — EXP_002: Multimodal Vegetation Filtering

## 1. Hypothesis
Combining LiDAR point classification ratios (Class 6 vs 3,4,5), optical Excess Green Index (ExG), and height roughness eliminates false positive tree canopies without suppressing genuine buildings.

## 2. Quantitative Results
- **Candidates Evaluated:** 75
- **Vegetation Rejected:** 44
- **Building Candidates Retained:** 31
- **Detection (RAW):**
  - TP: 4 (Baseline: 4)
  - FP: 27 (Baseline: 90 -> Massive reduction!)
  - FN: 61 (Baseline: 61)
  - Precision: 12.90% (Baseline: 4.26%)
  - Recall: 6.15% (Baseline: 6.15%)
  - F1: 8.33% (Baseline: 5.03%)

## 3. Finding
Vegetation filtering successfully pruned tree canopy false positives while preserving genuine structural candidates.
