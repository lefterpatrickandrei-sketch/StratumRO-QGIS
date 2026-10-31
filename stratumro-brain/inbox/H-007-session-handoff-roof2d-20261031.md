---
id: H-007
type: handoff
status: proposed
author: claude-opus-5.5
source_type: repo
sources:
  - path: docs/SESSION_HANDOFF_ROOF2D_20261031.md
  - path: workspace/reviews/cladiri_2d_final_r3_epsg3844.gpkg
  - path: workspace/reviews/verdicte_proprietar/verdicte_20261031.json
confidence: high
created: 2026-10-31
recheck_by: 2027-01-31
cssclasses:
  - note-handoff
supersedes: []
---
# H-007 Entry point for the 2D roof work (follows [[H-006-final-2d-map-r1-r3-20261031]])

The full handoff for any agent or session continuing the work is `docs/SESSION_HANDOFF_ROOF2D_20261031.md` [REPO, commit 6074d96 + handoff commit]. It covers state, workflow scripts, models, measured results, owner rules, technical traps, next steps and the commit list.

Facts [REPO, 2026-10-31]:
- The deliverable is `cladiri_2d_final_r3_epsg3844.gpkg`: 328 buildings, 137 owner ADMIS.
- The owner deleted 29 INCERT buildings in QGIS. They are saved as ELIMINAT in `verdicte_20261031.gpkg`. A re-run of `finalize_roof2d_map.py` must add those ids to `elimina`.
- The production segmenter is a 3× ResNet-34 ensemble (val IoU 0.71). Rejected after measurement: ConvNeXt (0.42), Meta satellite ViT-H (0.525), SAM 2.1 refinement (+0.008). Meta canopy height from RGB: precision 0.72–0.79, recall ~0.33.
- The model weights exist only on the local disk, without backup. There are 31 commits not pushed.

Status: pending owner decisions (retrain with owner negatives, model backup, push, Hugging Face access).
