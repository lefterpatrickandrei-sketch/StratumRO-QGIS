---
id: F-003
type: fact
status: proposed
author: perplexity-computer
source_type: repo
sources:
  - path: reports/cluj/ and docs/PROJECT_STATE.md in the code repository (HEAD 64a5cec, 2026-10-20)
confidence: medium
created: 2026-10-21
recheck_by: 2026-12-21
cssclasses:
  - note-fact
supersedes: []
---
# F-003 Cluj measured baseline (before any model change)

Numbers [REPO], from the repository reports, not re-run by me:
- Phase 2: 94 candidates, 65 references, TP 4, FP 90, FN 61; precision 4.26%, recall 6.15%; matched mean IoU 69.5%; RMSE 3.41 m.
- Phase 3 integrated: FP 22; precision 15.38%; recall 6.15%.
- References are legal parcels, not roof outlines, so recall against them understates roof extraction quality.
- Source orthophoto step 1.1651 cm; the pipeline has been working on a 15 cm cache.

Not verified: current test-suite status (not run); roof-level references do not exist yet.

Use: this is the baseline that any new model (SAM 2.1, 4-channel segmenter) must beat on a frozen, separate test area.
