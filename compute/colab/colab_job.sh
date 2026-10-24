#!/usr/bin/env bash
# Run one StratumRO Colab job inside WSL2 / Linux with google-colab-cli.
#
# Usage: colab_job.sh JOB GPU SCRIPT TIME_LIMIT_MIN OUT_DIR GIT_SHA
#
# Always stops the VM on exit (success, failure or Ctrl-C) so compute units are not burned.
#
# NOTE: `colab new`, `colab exec -f`, `colab upload`, `colab download`, `colab usage` come from the
# google-colab-cli README (v0.7.x). The exact argument order of upload/download was NOT verified on
# this machine (WSL2 missing). Check `colab upload --help` and `colab download --help` before the
# first real run and adjust the two marked lines.
set -euo pipefail

JOB="$1"; GPU="$2"; SCRIPT="$3"; LIMIT_MIN="$4"; OUT_DIR="$5"; GIT_SHA="$6"
SESSION="sr-$(echo "$JOB" | tr -c 'a-zA-Z0-9' '-' | cut -c1-7)"   # short alias
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

command -v colab >/dev/null 2>&1 || { echo "colab CLI not found. See compute/colab/README.md" >&2; exit 4; }

stop_vm() {
  echo "[colab_job] stopping session $SESSION"
  colab stop -s "$SESSION" >/dev/null 2>&1 || true
  echo "[colab_job] usage after:" | tee -a "$OUT_DIR/run.log"
  colab usage 2>&1 | tee -a "$OUT_DIR/run.log" || true
}
trap stop_vm EXIT

mkdir -p "$OUT_DIR"
echo "[colab_job] job=$JOB gpu=$GPU script=$SCRIPT sha=$GIT_SHA" | tee "$OUT_DIR/run.log"
echo "[colab_job] usage before:" | tee -a "$OUT_DIR/run.log"
colab usage 2>&1 | tee -a "$OUT_DIR/run.log"

colab new -s "$SESSION" --gpu "$GPU" 2>&1 | tee -a "$OUT_DIR/run.log"

# VERIFY ARG ORDER: `colab exec -f` sends ONE file to the kernel, so support modules (for example
# l2a_data.py, imported by train_l2a.py) must be uploaded to /content first. UNCOMMENT after checking
# `colab upload --help`; a real train_l2a run fails with ImportError until this is enabled.
# for f in "$REPO_DIR"/compute/colab/scripts/*.py; do
#   colab upload -s "$SESSION" "$f" "/content/$(basename "$f")"
# done
# echo "$GIT_SHA" > /tmp/GIT_SHA && colab upload -s "$SESSION" /tmp/GIT_SHA /content/GIT_SHA

# Run with a hard time limit so a hung job cannot burn units.
GIT_SHA="$GIT_SHA" timeout "${LIMIT_MIN}m" \
  colab exec -s "$SESSION" -f "$REPO_DIR/$SCRIPT" 2>&1 | tee -a "$OUT_DIR/run.log"

# VERIFY ARG ORDER: bring back small outputs (metrics.json). Checkpoints stay on Drive.
# colab download -s "$SESSION" "/content/metrics.json" "$OUT_DIR/metrics.json"

echo "$GIT_SHA" > "$OUT_DIR/GIT_SHA"
echo "[colab_job] done. Output is a PROPOSAL, not an approval: $OUT_DIR" | tee -a "$OUT_DIR/run.log"
