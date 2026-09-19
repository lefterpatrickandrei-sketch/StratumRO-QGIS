# Experiment Analysis — EXP_004: Multi-Point Interior Prompting

## 1. Hypothesis
Anchoring both the bounding box envelope and 5 distributed interior points guides SAM 2 to encompass multi-pitched, complex roofs simultaneously.

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
  - Mean IoU: 68.02%
