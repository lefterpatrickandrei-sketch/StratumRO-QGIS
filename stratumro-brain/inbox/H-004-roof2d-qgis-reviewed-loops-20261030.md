---
id: H-004
type: handoff
status: proposed
author: claude-opus-5.5
source_type: measured
sources:
  - path: workspace/reviews/final_2d_roofs_loopq4_epsg3844.gpkg
  - path: workspace/reviews/loop_2d_20261030/inspectie_loop_2d_20261030.qgs
  - path: workspace/colab_runs/loop_q/
confidence: medium
created: 2026-10-30
recheck_by: 2027-01-30
cssclasses:
  - note-handoff
supersedes: []
---
# H-004 Four QGIS-reviewed loops (follows [[H-003-roof2d-four-loops-20261030]])

H-003 loops were not all checked in QGIS. These four loops each rendered the same nine views through MCP `qgis-stratumro` (val failures, AJUSTARE targets, construction site) before deciding the next change [CALC: 2026-10-30].

- L1: merge fragments whose shared border has outline probability < 0.4. Val mean IoU 0.704 → 0.708; QGIS shows no change on the chapel OPT_B_128, whose pieces are real separate bodies.
- L2: a min-probability filter (0.75) cleaned the construction site in QGIS but cost 0.03–0.07 val IoU, because real val roofs have p 0.65–0.75. Replaced in L4 by a flag.
- L3: retrain with contact weight 10 and hue/grey augmentation (A100). Single model val IoU 0.715. QGIS shows the beige terrace OPT_B_116 is now found and the OPT_B_163 neighbours are separated. OPT_B_176 still over-extends.
- L4: final = ensemble B1+B3+L3, threshold 0.50, wall 0.4, no deletion; p < 0.75 flagged INCERT (84 of 423). Val mean IoU 0.710, 81 % detected, 87 % vertices at 45/90°, 274 pass V1..V6, 20/31 targets pass V1..V6. QGIS: construction-site false positives are all flagged INCERT, and no tree crowns in the park are drawn as roofs.

Status: pending owner review in QGIS; nothing is ADMIS.
