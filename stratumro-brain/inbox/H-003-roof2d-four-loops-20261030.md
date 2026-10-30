---
id: H-003
type: handoff
status: proposed
author: claude-opus-5.5
source_type: measured
sources:
  - path: workspace/colab_runs/loop_b1..loop_b4 (scan_metrics.json per run)
  - path: workspace/reviews/final_2d_roofs_loop4_ensemble_epsg3844.gpkg
  - path: workspace/reviews/loop_2d_20261030/inspectie_loop_2d_20261030.qgs
confidence: medium
created: 2026-10-30
recheck_by: 2027-01-30
cssclasses:
  - note-handoff
supersedes: []
---
# H-003 Four improvement loops on the 2D roof pipeline (follows [[H-002-roof2d-a100-loop-run-20261030]])

All metrics below are on 31 owner ADMIS roofs in the val strip (Y > 585730) [CALC: `scan_metrics.json`, 2026-10-30].

- Loop 1. The QGIS project holds one ACCEPTED_BY_OWNER polygon (T10), so no extra owner labels exist. Most failures were merged neighbours. Changes: contact channel, edge threshold 0.25, overlap resolver, rectilinear snapping. Result: mean IoU 0.66 → 0.73, V6 overlaps 227 → 11–14. SAM 2.1 Large added only +0.008.
- Loop 2. ConvNeXt-Small without enough negatives painted roofs over parks and the cemetery (20.9 % of the AOI), and mean IoU fell to 0.22. Roof-anchored val crops hid this [CALC].
- Loop 3. Added 37,510 m² of tree negatives (nDSM ≥ 2.5 m plus foliage) and background-anchored val crops. ConvNeXt reached 0.42 and ResNet-34 0.67. ResNet is kept. Single runs vary between 0.58 and 0.73.
- Loop 4. The 2-model ResNet ensemble (loops 1 + 3) at threshold 0.50 gives mean IoU 0.70, 29 % at IoU ≥ 0.90, 82 % of vertices at 45/90°, 3.5 % of roof pixels on known background and 7 overlaps. 17/31 AJUSTARE targets pass V1..V6. A 3-model ensemble was not better.

Seen in QGIS: tombs are rejected, and OPT_B_144 now has its full corner. Some false positives on the north construction site pass V1..V6. The large complexes and the chapel (OPT_B_128) are still split into pieces.

Status: pending owner review; nothing is ADMIS.
