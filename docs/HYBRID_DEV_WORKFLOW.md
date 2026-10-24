# Hybrid development workflow (Antigravity + Colab CLI + Claude + Copilot)

Status: PROPOSED PROCESS, added 2026-10-24. This document is **additive**: it does not change
architecture v2 (L1-L6), the golden rules in [AGENTS.md](../AGENTS.md), or any `canon/` decision.
Companion diagram: [architecture_v2_dev_plane.md](architecture_v2_dev_plane.md).

## 1. Tools and roles

| Tool | Plan | Use it for | Do not use it for |
|---|---|---|---|
| **Antigravity IDE / 2.0 / `agy`** | Google AI Pro | Home base. Gemini Flash for routine bulk work (scaffolding, docs, test writing, long exploration). `/goal`, `/plan`, `/browser` for long, planned or research tasks. | Assuming Claude models are available inside it (listed as Ultra-tier in the docs). |
| **Colab CLI** (`google-colab-cli`, in WSL2) | Colab compute units | Heavy GPU jobs: L2a training, L2b SAM 2.1 batch refinement, L5 VLM evaluation, retraining from the feedback loop, optional bulk L1 tiling. | Anything that needs QGIS, or any decision. Colab produces proposals only. |
| **Claude (Pro)** via Claude Code or the Claude app | Claude Pro (5-hour and weekly caps, shared with claude.ai) | Architecture, hard PyQGIS / geometry / training bugs, code review, L3, L5 and MCP logic. | Bulk edits and long idle sessions (burns quota). |
| **GitHub Copilot** | Student pack (Auto model selection) | Inline completions, boilerplate, small edits, unit tests, QGIS plugin glue. | Heavy agentic work (credit allowance is limited and unpublished). |

Gemini Flash (3.8) from the AI Pro plan covers "routine parts" in any of the above.

## 2. Layer mapping

| Layer | Develop with | Runs on |
|---|---|---|
| L1 Deterministic Geo Core | Antigravity + Copilot | WS / LAPTOP (Colab only for bulk tiling if the laptop is too slow) |
| L2a Roof Segmenter | Claude (design), Gemini (scripts) | **Train: COLAB (T4/L4). Infer: LAPTOP** |
| L2b SAM 2.1 | Gemini (scripts), Claude (evaluation) | **Batch: COLAB.** Interactive: LAPTOP |
| L3 Fusion + Regularization | Claude + Copilot | WS / LAPTOP |
| L4 System 1 Triage | Gemini + Copilot | LOCAL (<35 ms) |
| L5 System 2 Verification | Claude (logic), Gemini Flash (routine) | CLOUD or WS fallback. Colab for VLM evaluation only |
| L6 Human Gate / Feedback Loop | Claude (review) | QGIS Desktop. **Retraining: COLAB** |

Local hardware measured on 2026-10-13 and 2026-10-24: RTX 4050 Laptop, 6141 MiB VRAM. The 24 GB
"Workstation" in the v2 diagram is a different machine.

## 3. Handoff protocol

1. **Start of any session (any tool):** read `AGENTS.md`, then `docs/PROJECT_STATE.md`, then
   `stratumro-brain/INDEX.md`. Run `git status -s`. Do not touch other agents' files.
2. **State lives in the repo, not in chat.** Leave a dated handoff in the task evidence folder
   (fields in [AGENT_HANDOFF.md](AGENT_HANDOFF.md)).
3. **Colab jobs** are described by a job card in `compute/colab/jobs/`. The card, the git SHA and
   `manifest.json` hashes are the only things a Colab run may depend on.
4. **Colab results come back as proposals.** Checkpoints, `metrics.json` and `run.log` are copied to
   `workspace/colab_runs/<job>/<UTC timestamp>/`. Nothing is accepted, merged into a deliverable
   or stamped `ADMIS` without the owner's explicit verdict.
5. **Memory:** agents write proposals to `stratumro-brain/inbox/` on their own branch. Never edit `canon/`.

## 4. Quota strategy

- **Claude Pro:** plan, design, review. Use `/compact` and fresh sessions. Heavy repetitive edits go to Gemini.
- **Gemini Flash (Antigravity):** default for bulk work. Quota refreshes every 5 hours with a weekly cap.
- **Copilot:** completions and small edits. Check its usage dashboard monthly.
- **Colab:** run `colab usage` before every job. Prefer T4 / L4. A100 / H100 burn units fast.
  Always `colab stop` (the wrapper does this even on failure).

## 5. Routing cheat sheet

| If the task is... | Open |
|---|---|
| "Why does this polygon / CRS / PyQGIS call misbehave?" | Claude |
| "Write tests / scaffold files / update docs for this change" | Antigravity (Gemini Flash) |
| "Finish this function / add this loop" | Copilot (inline) |
| "Train / refine / evaluate on GPU" | Colab job card |
| "Research an option, compare libraries" | Antigravity `/browser` or `/plan` |
| "Run something overnight until done" | Antigravity `/goal` |

## 6. Colab specifics

- `google-colab-cli` is **Linux / macOS only** and needs Python 3.12 or newer. On this Windows
  machine it must run inside **WSL2**. WSL was **not installed on 2026-10-24**, so install it first
  (see [compute/colab/README.md](../compute/colab/README.md)).
- Pin `google-colab-cli>=0.7.4` (0.7.3 was yanked). It is a 0.x project; expect changes.
- VMs are deleted when idle and have a maximum lifetime (about 12 hours). Jobs must checkpoint to
  Drive and be resumable.
- The official Colab VS Code extension is for notebooks only. `colab-mcp` needs a browser tab and is
  not used here.

## 7. Data policy for Colab

- Inputs are 4-channel tiles in **EPSG:3844** plus a `manifest.json` (SHA-256, CRS, resolution,
  spatial split). Never upload raw survey points, `.env` or secrets.
- Before uploading orthophoto, LiDAR or cadastral material, confirm the licence allows a private
  Google Drive / Colab VM (USAMV and ANCPI sources). When unsure, upload only cleared subsets.
- Outputs carry the git SHA that produced them and are labelled model results, not measured accuracy.

## 8. Known gaps found on 2026-10-24

- WSL2 not installed (blocks the Colab CLI on this machine).
- `segmentation_models_pytorch` is not installed in the local `venv` (needed only on Colab for L2a).
- `.agents/rules/{evidence,geometry,qgis_runtime}.md` have no YAML frontmatter. Antigravity reportedly
  discards rule files without a valid `trigger`, so those three may not be loading. Not changed here.
- `.mcp.json` and `.vscode/` are git-ignored, so those MCP mirrors are generated locally by
  `scripts/sync_mcp_mirrors.py` and are not committed.
- Installed SAM is the 2.0 checkpoint (`sam2_hiera_tiny.pt`); SAM 2.1 weights are downloaded on Colab.
- The Gemini AI Pro subscription is not necessarily Gemini **API** access for L5 runtime. Until the
  owner confirms an API key, L5 defaults to local Qwen-VL.
