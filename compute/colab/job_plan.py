"""Load, validate and print the plan for a Colab job card (no network, no GPU, no side effects).

    python compute/colab/job_plan.py train_l2a            # validate + print the plan
    python compute/colab/job_plan.py train_l2a --json     # machine-readable

Exit code 0 = card valid, 1 = invalid. Used by ``colab_job.ps1`` before anything is started.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
JOBS_DIR = HERE / "jobs"

VALID_GPUS = {"T4", "L4", "G4", "A100", "H100"}
MAX_MINUTES = 720  # Colab VMs have a maximum lifetime of about 12 hours
REQUIRED_KEYS = (
    "name", "description", "gpu", "time_limit_minutes", "script",
    "inputs", "outputs", "checkpoint", "requires_owner_approval", "status",
)
VALID_STATUS = {"scaffolded", "card-only"}


def load_card(name: str, jobs_dir: Path = JOBS_DIR) -> dict:
    path = jobs_dir / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"job card not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(card: dict, repo: Path = REPO) -> list[str]:
    """Return a list of problems (empty list = valid)."""
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in card:
            errors.append(f"missing key: {key}")
    if errors:
        return errors
    if card["gpu"] not in VALID_GPUS:
        errors.append(f"gpu must be one of {sorted(VALID_GPUS)}, got {card['gpu']!r}")
    minutes = card["time_limit_minutes"]
    if not isinstance(minutes, int) or isinstance(minutes, bool) or not 0 < minutes <= MAX_MINUTES:
        errors.append(f"time_limit_minutes must be an int in 1..{MAX_MINUTES}")
    if card["requires_owner_approval"] is not True:
        errors.append("requires_owner_approval must be true (Colab spends compute units)")
    if card["status"] not in VALID_STATUS:
        errors.append(f"status must be one of {sorted(VALID_STATUS)}")
    elif card["status"] == "scaffolded":
        script = card["script"]
        if not script or not (repo / script).is_file():
            errors.append(f"script not found for a scaffolded card: {script!r}")
    for key in ("inputs", "outputs"):
        if not isinstance(card[key], dict) or not card[key]:
            errors.append(f"{key} must be a non-empty mapping")
    if "EPSG:3844" not in str(card.get("crs", "EPSG:3844")):
        errors.append("crs, when given, must be EPSG:3844")
    return errors


def describe(card: dict) -> list[str]:
    lines = [
        f"job:         {card['name']}  [{card['status']}]",
        f"gpu:         {card['gpu']}",
        f"time limit:  {card['time_limit_minutes']} min",
        f"script:      {card['script']}",
        f"checkpoint:  {card['checkpoint']}",
        "inputs:",
    ]
    lines += [f"  - {k}: {v}" for k, v in card["inputs"].items()]
    lines.append("outputs:")
    lines += [f"  - {k}: {v}" for k, v in card["outputs"].items()]
    lines.append("approval:    owner must approve before this job is started")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("job")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        card = load_card(args.job)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(card)
    if errors:
        for e in errors:
            print(f"INVALID: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(card, indent=2, ensure_ascii=False))
    else:
        print("\n".join(describe(card)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
