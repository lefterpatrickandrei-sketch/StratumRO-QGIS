"""L2a roof segmenter training (UNet++, 4 input channels RGB + nDSM) for a Colab GPU VM.

STATUS: scaffolded, NOT run. Output is a PROPOSAL (checkpoint + metrics.json), never an approval.

Run on the VM (support module l2a_data.py must be next to this file or in /content):
    python train_l2a.py --manifest /content/drive/MyDrive/StratumRO/l2a/manifest.json \
        --root /content/drive/MyDrive/StratumRO/l2a --out /content/drive/MyDrive/StratumRO/runs/train_l2a/<ts>

Needs on the VM: pip install segmentation-models-pytorch==0.5.0 rasterio
Design notes (from the 2026-10-24 research, see docs/HYBRID_DEV_WORKFLOW.md):
  * smp patches the first conv for in_channels=4; the nDSM filter is zero-initialised here so training
    starts from RGB behaviour (only when the encoder exposes ``conv1``).
  * Geometric augmentation on all 4 channels; photometric on RGB only; nDSM heights are never jittered.
  * Spatial split with a buffer (no random tiles). Resumes from <out>/checkpoints/latest.pt.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/content")

import numpy as np

from l2a_data import augment, load_manifest, prepare_input, validate_manifest


def dice_bce_loss(logits, target, eps: float = 1.0):
    """Dice + BCE on logits (N,1,H,W) vs target (N,1,H,W) float in {0,1}. Torch is imported lazily."""
    import torch
    import torch.nn.functional as F

    bce = F.binary_cross_entropy_with_logits(logits, target)
    prob = torch.sigmoid(logits)
    inter = (prob * target).sum(dim=(1, 2, 3))
    denom = prob.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3))
    dice = 1.0 - (2.0 * inter + eps) / (denom + eps)
    return bce + dice.mean()


def iou_score(logits, target, threshold: float = 0.5) -> float:
    import torch

    pred = (torch.sigmoid(logits) > threshold).float()
    inter = (pred * target).sum().item()
    union = (pred + target).clamp(max=1.0).sum().item()
    return 1.0 if union == 0 else inter / union


def build_model(encoder: str = "resnet34", pretrained: bool = True):
    import segmentation_models_pytorch as smp
    import torch

    model = smp.UnetPlusPlus(
        encoder_name=encoder,
        encoder_weights="imagenet" if pretrained else None,
        in_channels=4,
        classes=1,
    )
    conv1 = getattr(model.encoder, "conv1", None)
    if conv1 is not None and conv1.weight.shape[1] == 4:
        with torch.no_grad():
            conv1.weight[:, 3].zero_()  # nDSM channel starts neutral
    return model


class TileDataset:
    def __init__(self, tiles: list[dict], root: Path, train: bool, seed: int = 0):
        self.tiles, self.root, self.train = tiles, root, train
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return len(self.tiles)

    def __getitem__(self, i: int):
        import rasterio

        t = self.tiles[i]
        with rasterio.open(self.root / t["image"]) as src:
            arr = src.read()  # (4,H,W): R,G,B uint8 + nDSM metres
        with rasterio.open(self.root / t["mask"]) as src:
            mask = (src.read(1) > 0).astype(np.float32)
        rgb = np.moveaxis(arr[:3], 0, -1).astype(np.uint8)
        x = prepare_input(rgb, arr[3].astype(np.float32))
        if self.train:
            x, mask = augment(x, mask, self.rng)
        return x.astype(np.float32), mask[None].astype(np.float32)


def git_sha() -> str:
    env = Path("/content/GIT_SHA")
    if env.is_file():
        return env.read_text().strip()
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--encoder", default="resnet34")
    ap.add_argument("--verify-hashes", action="store_true")
    args = ap.parse_args(argv)

    root, out = Path(args.root), Path(args.out)
    manifest = load_manifest(Path(args.manifest))
    problems = validate_manifest(manifest, root, verify_hashes=args.verify_hashes)
    if problems:
        print("MANIFEST INVALID:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1

    import torch
    from torch.utils.data import DataLoader

    ckpt_dir = out / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    tiles = {s: [t for t in manifest["tiles"] if t["split"] == s] for s in ("train", "val", "test")}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(args.encoder).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    scaler = torch.amp.GradScaler(device, enabled=device == "cuda")
    train_dl = DataLoader(TileDataset(tiles["train"], root, True), batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_dl = DataLoader(TileDataset(tiles["val"], root, False), batch_size=args.batch_size, num_workers=2)

    start_epoch, history = 0, []
    latest = ckpt_dir / "latest.pt"
    if latest.is_file():  # resume after a VM was recycled
        state = torch.load(latest, map_location=device)
        model.load_state_dict(state["model"])
        opt.load_state_dict(state["opt"])
        start_epoch, history = state["epoch"] + 1, state["history"]
        print(f"resumed from epoch {start_epoch}")

    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()
        model.train()
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device, dtype=torch.float16, enabled=device == "cuda"):
                loss = dice_bce_loss(model(x).float(), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        model.eval()
        ious = []
        with torch.no_grad():
            for x, y in val_dl:
                ious.append(iou_score(model(x.to(device)).float(), y.to(device)))
        val_iou = float(np.mean(ious)) if ious else float("nan")
        history.append({"epoch": epoch, "val_iou": val_iou, "seconds": round(time.time() - t0, 1)})
        print(history[-1], flush=True)
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "epoch": epoch, "history": history}, latest)

    metrics = {
        "job": "train_l2a",
        "status": "PROPOSAL_NOT_ACCEPTED",
        "git_sha": git_sha(),
        "crs": manifest["crs"],
        "split_counts": {k: len(v) for k, v in tiles.items()},
        "buffer_m": manifest.get("buffer_m", 30.0),
        "history": history,
        "peak_vram_mib": round(torch.cuda.max_memory_allocated() / 2**20, 1) if device == "cuda" else None,
        "note": "Validation IoU only. The frozen test split is evaluated separately against the SAM baseline (D-001).",
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("wrote", out / "metrics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
