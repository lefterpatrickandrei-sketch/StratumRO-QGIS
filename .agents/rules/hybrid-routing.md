---
trigger: model_decision
description: Decide when a task should become a Colab GPU job card instead of running locally, and how to hand results back.
---

# Hybrid routing rule

Applies when a task would train a model, run SAM 2.1 over many tiles, evaluate a VLM, or retrain from
the feedback loop. Background: `docs/HYBRID_DEV_WORKFLOW.md`.

1. **Local GPU is an RTX 4050 with 6 GB.** Do not start training or large batch inference on it while
   another agent uses it. Prefer a job card in `compute/colab/jobs/`.
2. **Propose, do not start.** Write or update the job card, then tell the owner. Starting a Colab job
   (it spends compute units) and uploading data need the owner's explicit go-ahead.
3. **Check before upload:** the data licence allows a private Drive / Colab VM; no secrets, no `.env`,
   no raw survey points. Inputs are EPSG:3844 tiles plus a `manifest.json` with SHA-256 hashes.
4. **Colab output is a proposal.** Copy checkpoints and `metrics.json` into
   `workspace/colab_runs/<job>/<UTC timestamp>/` with the git SHA. Never mark anything accepted or `ADMIS`.
5. **Evaluation gate (D-001):** L2a stays a recommended stage only if it beats the SAM baseline on the
   frozen, spatially separate test area. Report the comparison; do not claim gains in advance.
6. **Always stop the VM** and record `colab usage` before and after.
