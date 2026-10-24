---
id: D-005
type: decision
status: proposed
author: claude-sonnet
source_type: agent-inference
sources:
  - path: docs/HYBRID_DEV_WORKFLOW.md (in the code repository)
  - path: docs/architecture_v2_dev_plane.md (in the code repository)
  - url: https://github.com/googlecolab/google-colab-cli
    retrieved: 2026-10-24
confidence: medium
created: 2026-10-24
recheck_by: 2026-12-24
cssclasses:
  - note-decision
supersedes: []
---
# D-005 Hybrid development and Colab compute plane (PROPOSED, not yet approved)

Proposal: develop with Antigravity (Gemini Flash), Claude Pro and Copilot Student in the same repository, and run heavy GPU work (L2a training, L2b SAM 2.1 batch, VLM evaluation, retraining) as Colab jobs driven by the Colab CLI inside WSL2. Architecture v2 L1-L6 is unchanged. Colab output is a proposal only; the human gate (L6) stays the sole approval.

Why: the local GPU is an RTX 4050 with 6 GB [REPO: nvidia-smi, 2026-10-24]. The Colab CLI runs only on Linux/macOS and needs Python 3.12+ [PUB: PyPI, retrieved 2026-10-24]. VM lifetime is limited, so jobs must checkpoint [PUB: Colab FAQ].

Conflict to resolve: AGENTS.md rule 6 says no new cloud services without an approved requirement. This note is that requirement request.

Open: WSL2 not installed [REPO: `wsl --status`, 2026-10-24]; data licence for Drive/Colab upload unconfirmed; Gemini API key for L5 unconfirmed.

Needs: owner approval.
