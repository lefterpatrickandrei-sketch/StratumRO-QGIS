---
id: D-002
type: decision
status: approved
author: owner
source_type: owner
sources:
  - path: owner message, 2026-10-21
confidence: high
created: 2026-10-21
recheck_by: 2027-01-21
cssclasses:
  - note-decision
supersedes: []
---
# D-002 ESA SNAP comes after the cadastre and PUG work in QGIS

Decision: ESA SNAP (Sentinel NDVI and related products) is a later phase that starts after the cadastre and PUG phase in QGIS is finished and its exit checks pass. CAD and point-cloud software (AutoCAD, Civil 3D, CloudCompare) are also later.

Why: stated by the owner; also the repo's own toolchain inventory reserves SNAP for a later satellite phase [REPO]. Sentinel-2 bands used for NDVI are 10 m, so they give context, not building outlines [PUB: Copernicus documentation].

Exit checks: see the Execution Plan Report, Gate A.
