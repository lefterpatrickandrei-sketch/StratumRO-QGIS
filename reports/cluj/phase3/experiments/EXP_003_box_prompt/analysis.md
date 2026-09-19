# Experiment Analysis — EXP_003: Bounding Box Prompting Alone

## 1. Hypothesis
Prompting SAM 2 with the bounding box alone prevents the model from collapsing onto a single homogeneous roof facet around a center point, improving recall on sprawling buildings.

## 2. Quantitative Results
- **Predictions Segmented:** 31
- **Detection (RAW):**
  - TP: 4 (Baseline: 4)
  - FP: 27 (Baseline: 90)
  - FN: 61 (Baseline: 61)
  - Precision: 12.90%
  - Recall: 6.15%
  - F1: 8.33%
- **Segmentation (RAW):**
  - Mean IoU: 65.02%
