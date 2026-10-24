# Colab compute scaffold (heavy GPU jobs)

Purpose: run heavy StratumRO jobs on Google Colab with the official `google-colab-cli`, while the
laptop (RTX 4050, 6 GB) keeps QGIS, L1, L3, L4 and inference. Process and rules:
[docs/HYBRID_DEV_WORKFLOW.md](../../docs/HYBRID_DEV_WORKFLOW.md) and
[.agents/rules/hybrid-routing.md](../../.agents/rules/hybrid-routing.md).

> Nothing here starts a job or uploads data by itself. The wrapper refuses to run without `-Confirm`.

## One-time setup (Windows -> WSL2)

`google-colab-cli` is **Linux/macOS only** and needs **Python >= 3.12**. WSL2 was **not installed**
on this machine on 2026-10-24.

```powershell
wsl.exe --install -d Ubuntu          # needs an administrator shell and a reboot
```

Then, inside Ubuntu:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install "google-colab-cli>=0.7.4"      # 0.7.3 was yanked
colab usage                                     # shows your compute-unit balance
```

Auth defaults to `--auth adc`. See the CLI README for `--auth oauth2`.

## Job cards

`jobs/*.yaml` declare GPU, inputs, outputs, checkpoint path and time limit. The wrapper reads a card
and runs: `colab new` -> upload -> `colab exec` -> download -> `colab stop` (always, even on failure).

| Card | Script | Status |
|---|---|---|
| `train_l2a.yaml` | `scripts/train_l2a.py` | scaffolded, not run |
| `refine_sam21.yaml` | `scripts/refine_sam21.py` | scaffolded, not run |
| `retrain_from_feedback.yaml` | `scripts/train_l2a.py` (new split manifest) | card only |
| `vlm_eval.yaml` | not written yet | card only |

## Running (after the owner approves a job)

```powershell
./compute/colab/colab_job.ps1 -Job train_l2a -DryRun        # prints the plan, runs nothing
./compute/colab/colab_job.ps1 -Job train_l2a -Confirm       # real run, spends compute units
```

Results land in `workspace/colab_runs/<job>/<UTC timestamp>/` as **proposals**: checkpoint,
`metrics.json`, `run.log`, git SHA. Nothing is accepted without the owner.

## Data contract

- Inputs: 4-channel tiles (R, G, B, nDSM) in EPSG:3844 and a `manifest.json` with SHA-256, CRS,
  resolution and the spatial split (Train 126 / Val 22 / Test 31, 30 m buffer, per the v2 diagram).
- Never upload raw survey points, `.env`, or data whose licence forbids a private Drive / Colab VM.
- Checkpoint to Drive every N epochs. VMs are deleted when idle and have a maximum lifetime.

## Tests

```powershell
python -m unittest discover compute/colab/tests
```
