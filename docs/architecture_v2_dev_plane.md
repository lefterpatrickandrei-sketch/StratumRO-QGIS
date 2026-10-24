# Architecture v2 + development and compute plane (additive)

This page **adds** a dev/compute plane next to `perplexity AI/png/fig1_architecture_v2_hybrid.png`.
The original diagram and its layers L1-L6 are unchanged; the IDs below are the same ones.
Process details: [HYBRID_DEV_WORKFLOW.md](HYBRID_DEV_WORKFLOW.md).

New deployment tag: **`COLAB`** (next to the existing `WS`, `LAPTOP`, `CLOUD`, `LOCAL`).

```mermaid
flowchart LR
  subgraph DEV["Dev plane (new)"]
    AG["Antigravity IDE / agy<br/>Gemini Flash + /goal /plan /browser"]
    CL["Claude Pro<br/>design, hard bugs, review"]
    CP["Copilot Student<br/>completions, tests"]
  end
  subgraph V2["Architecture v2 (unchanged)"]
    L1["L1 Geo Core"] --> L3["L3 Fusion + Regularization"]
    L2a["L2a Roof Segmenter"] --> L3
    L2b["L2b SAM 2.1 Refinement"] --> L4["L4 System 1 Triage"]
    L3 --> L5["L5 System 2 Verification"]
    L4 --> L5
    L5 --> L6["L6 Human Gate (QGIS)"]
    L5 --> FB["Feedback Loop / Retraining Store"]
  end
  subgraph COMP["Compute plane (new)"]
    LAP["LAPTOP RTX 4050 6GB<br/>QGIS, L1, L3, L4, inference"]
    COL["COLAB via colab CLI in WSL2<br/>train L2a, SAM 2.1 batch, VLM eval, retrain"]
    DRV["Drive<br/>tiles, checkpoints, metrics"]
  end
  AG --> V2
  CL --> V2
  CP --> V2
  L1 -. runs on .-> LAP
  L3 -. runs on .-> LAP
  L4 -. runs on .-> LAP
  L2a -. train .-> COL
  L2b -. batch .-> COL
  FB -. retrain .-> COL
  COL <--> DRV
  DRV -->|"proposals only"| LAP
```

## Layer to compute mapping

| Layer | Compute tag | Heavy job card |
|---|---|---|
| L1 | WS + LAPTOP | optional bulk tiling (not scaffolded yet) |
| L2a | **COLAB** (train) / LAPTOP (infer) | `compute/colab/jobs/train_l2a.yaml` |
| L2b | **COLAB** (batch) / LAPTOP (interactive) | `compute/colab/jobs/refine_sam21.yaml` |
| L5 | CLOUD + WS fallback | `compute/colab/jobs/vlm_eval.yaml` (evaluation only) |
| Feedback Loop | **COLAB** (retrain) | `compute/colab/jobs/retrain_from_feedback.yaml` |

Guarantees kept from v2: L3 geometry stays deterministic and local; L5 stays fail-closed; the
human gate (L6) is the only approval. Colab output never auto-approves anything.
