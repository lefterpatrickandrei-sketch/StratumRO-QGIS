---
id: D-001
type: decision
status: approved
author: owner
source_type: owner
sources:
  - path: StratumRO Multimodal Architecture Report (Appendix A and section 7)
confidence: high
created: 2026-10-21
recheck_by: 2027-01-21
cssclasses:
  - note-decision
supersedes: []
---
# D-001 Trained roof segmenter is a recommended stage (L2a)

Decision: the architecture shows a trained roof segmenter (4-channel RGB plus nDSM U-Net++ or DeepLabV3+) as a recommended stage, with SAM as boundary refiner and label drafter (L2b).

Why: Cluj recall is 6.15% (4 of 65 references) while matched masks reach 69.5% IoU, so the limit is which objects are proposed [REPO].

Condition: the stage stays only if it beats the SAM baseline on a frozen, spatially separate test area. No expected gain for Romanian imagery is claimed.

Approved by owner on 2026-10-21 (answer: "Recommended stage").
