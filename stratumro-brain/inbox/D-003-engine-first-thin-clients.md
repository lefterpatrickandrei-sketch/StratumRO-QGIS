---
id: D-003
type: decision
status: proposed
author: perplexity-computer
source_type: agent-inference
sources:
  - path: docs/STRATUMRO_PRODUCT_IDENTITY_AND_DESKTOP_DIRECTION_2026-10-17.md (in the code repository)
confidence: medium
created: 2026-10-21
recheck_by: 2026-12-21
cssclasses:
  - note-decision
supersedes: []
---
# D-003 Engine first, apps as thin clients (PROPOSED, not yet approved)

Proposal: keep StratumRO as a headless engine with one setup file per run, and treat the QGIS plugin, a command-line entry point and a small MCP tool set as clients. Defer the desktop app until the QGIS-phase exit checks pass. No Rust rewrite without a measured bottleneck.

Basis: the owner's own product-identity document says the core stays separate from the interface and that a Rust component needs a measured bottleneck [REPO]. Details are in the Rebuild Blueprint.

Needs: owner approval. Until then, treat as a recommendation.
