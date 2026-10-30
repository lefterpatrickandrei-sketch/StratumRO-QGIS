# -*- coding: utf-8 -*-
"""
StratumRO - Phase 1 continuous 2D roof loop (RGB only, EPSG:3844), local RTX 4050 or Colab A100.

Each iteration k:
  1. Train the multi-task roof / outline / corner UNet (train_roof2d.py) on owner labels plus the
     pseudo roofs of iteration k-1 (they only fill pixels that are still ignore_index=255).
  2. Scan the whole AOI (scan_roof2d_aoi.py): sliding-window inference, instance split on the outline
     head, regularization, and the simultaneous V1..V6 gates (stratum_ro.core.qa_qc) on every polygon.
  3. Proposals that pass all six gates with mean roof probability >= 0.75 become the pseudo roofs of
     iteration k+1 (PSEUDO_GOLD_2D, status PENDING_OWNER_REVIEW - never ADMIS).
  4. Stop on the convergence targets (val ADMIS mean IoU >= 0.90, >= 98 % 45/90 deg vertices, no NoData
     contact, no overlaps), on a plateau (val IoU gain < 0.01 and pseudo set change < 5 %), or at
     ``--max-iterations``.

Writes <out>/loop_convergence_report.json and one folder per iteration (checkpoints, GeoPackage,
before/after sheet for the AJUSTARE targets). Everything is a proposal for owner review.

Earlier versions evaluated V3/V4 on the building bbox instead of the polygon and did no training;
that heuristic loop was removed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[3]


def compute_multitask_2d_loss_numpy(
    pred_roof: np.ndarray,
    pred_edge: np.ndarray,
    pred_corner: np.ndarray,
    target_roof: np.ndarray,
    target_edge: np.ndarray,
    target_corner: np.ndarray,
    ignore_index: int = 255,
) -> Dict[str, float]:
    """
    Reference deterministic implementation of the Multi-Task 2D Roof Loss:
      L_total = 1.0 * L_roof_dice_bce (ignoring 255)
              + 0.5 * L_edge_bce
              + 0.5 * L_corner_focal
    """
    valid = target_roof != ignore_index
    if not np.any(valid):
        return {"total_loss": 0.0, "roof_loss": 0.0, "edge_loss": 0.0, "corner_loss": 0.0}

    p_r = np.clip(pred_roof[valid].astype(np.float64), 1e-6, 1.0 - 1e-6)
    t_r = (target_roof[valid] == 1).astype(np.float64)
    bce_r = -np.mean(t_r * np.log(p_r) + (1.0 - t_r) * np.log(1.0 - p_r))
    inter = np.sum(p_r * t_r)
    dice_r = 1.0 - (2.0 * inter + 1.0) / (np.sum(p_r) + np.sum(t_r) + 1.0)
    roof_loss = 0.5 * bce_r + 0.5 * dice_r

    p_e = np.clip(pred_edge[valid].astype(np.float64), 1e-6, 1.0 - 1e-6)
    t_e = (target_edge[valid] > 0).astype(np.float64)
    edge_loss = float(-np.mean(t_e * np.log(p_e) + (1.0 - t_e) * np.log(1.0 - p_e)))

    p_c = np.clip(pred_corner[valid].astype(np.float64), 1e-6, 1.0 - 1e-6)
    t_c = (target_corner[valid] > 0).astype(np.float64)
    corner_loss = float(-np.mean(t_c * np.log(p_c) + (1.0 - t_c) * np.log(1.0 - p_c)))

    total = float(1.0 * roof_loss + 0.5 * edge_loss + 0.5 * corner_loss)
    return {
        "total_loss": round(total, 5),
        "roof_loss": round(float(roof_loss), 5),
        "edge_loss": round(edge_loss, 5),
        "corner_loss": round(corner_loss, 5),
    }


def converged(m: Dict[str, Any]) -> bool:
    val = m["admis_iou_val"]["mean_iou"] or 0.0
    return (
        val >= 0.90
        and m["angles"]["ortho_45_90_share"] >= 0.98
        and m["v5_nodata_touching_proposals"] == 0
        and m["v6_overlapping_proposals"] == 0
    )


def git_sha() -> str:
    for p in (Path("/content/GIT_SHA"), REPO_ROOT / "GIT_SHA"):
        if p.is_file():
            return p.read_text().strip()
    try:
        return subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def run_loop(data: Path, out: Path, max_iterations: int, epochs_first: int, epochs_next: int,
             samples_per_epoch: int, batch_size: int, workers: int, lr: float) -> Dict[str, Any]:
    from scan_roof2d_aoi import scan
    from train_roof2d import train

    out.mkdir(parents=True, exist_ok=True)
    history: List[Dict[str, Any]] = []
    init: Optional[Path] = None
    pseudo: Optional[Path] = None
    stop_reason = "max_iterations"
    for it in range(1, max_iterations + 1):
        t0 = time.time()
        it_dir = out / f"iter_{it:02d}"
        done_train, done_scan = it_dir / "train_metrics.json", it_dir / "scan" / "scan_metrics.json"
        if done_train.is_file():  # resume after a crash or a recycled VM
            tm = json.loads(done_train.read_text(encoding="utf-8"))
        else:
            tm = train(data, it_dir, epochs_first if it == 1 else epochs_next, samples_per_epoch, batch_size,
                       lr if it == 1 else lr * 0.5, init, pseudo, workers)
        if done_scan.is_file():
            sm = json.loads(done_scan.read_text(encoding="utf-8"))
        else:
            sm = scan(data, it_dir / "best.pt", it_dir / "scan")
        rec = {
            "iteration": it,
            "device": tm["device"],
            "best_val_pixel_iou": tm["best_val_pixel_iou"],
            "pseudo_labels_in": str(pseudo) if pseudo else None,
            **{k: sm[k] for k in ("proposals", "all_six_passed", "gate_pass_rates", "angles", "admis_iou_val",
                                  "admis_iou_train_seen", "targets_detected", "targets_all_six",
                                  "hard_negatives_hit", "v5_nodata_touching_proposals",
                                  "v6_overlapping_proposals", "new_proposals_not_in_review",
                                  "new_proposals_all_six", "pseudo_roofs")},
            "minutes": round((time.time() - t0) / 60, 1),
        }
        history.append(rec)
        print(json.dumps(rec), flush=True)
        init, pseudo = it_dir / "best.pt", it_dir / "scan" / "pseudo_roofs.tif"
        if converged(sm):
            stop_reason = "converged_all_targets"
            break
        if len(history) >= 2:
            a, b = history[-2], history[-1]
            gain = (b["admis_iou_val"]["mean_iou"] or 0) - (a["admis_iou_val"]["mean_iou"] or 0)
            change = abs(b["pseudo_roofs"] - a["pseudo_roofs"]) / max(a["pseudo_roofs"], 1)
            if gain < 0.01 and change < 0.05:
                stop_reason = "plateau"
                break

    best = max(history, key=lambda h: h["admis_iou_val"]["mean_iou"] or 0)
    report = {
        "crs": "EPSG:3844",
        "phase": "Phase 1 - 2D roof outlines from RGB orthophoto (no LiDAR input)",
        "status": "PROPOSAL_PENDING_OWNER_REVIEW",
        "git_sha": git_sha(),
        "data_manifest": str(data / "manifest.json"),
        "targets": {"admis_val_mean_iou": 0.90, "ortho_45_90_share": 0.98, "nodata_contact": 0, "overlaps": 0},
        "stop_reason": stop_reason,
        "iterations_run": len(history),
        "best_iteration": best["iteration"],
        "history": history,
    }
    (out / "loop_convergence_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=REPO_ROOT / "workspace" / "colab_2d_roof_dataset_v3")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "workspace" / "colab_runs" / "continuous_2d")
    parser.add_argument("--max-iterations", type=int, default=4)
    parser.add_argument("--epochs-first", type=int, default=40)
    parser.add_argument("--epochs-next", type=int, default=15)
    parser.add_argument("--samples-per-epoch", type=int, default=640)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=5e-4)
    args = parser.parse_args(argv)
    report = run_loop(args.data, args.out, args.max_iterations, args.epochs_first, args.epochs_next,
                      args.samples_per_epoch, args.batch_size, args.workers, args.lr)
    print(json.dumps({k: report[k] for k in ("stop_reason", "iterations_run", "best_iteration")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
