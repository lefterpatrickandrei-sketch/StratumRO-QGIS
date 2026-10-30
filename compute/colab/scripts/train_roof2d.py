"""Phase 1 multi-task 2D roof segmenter (RGB only): roof mask + outline + corner heads.

UNet with a torchvision ImageNet encoder (ResNet-34 or ConvNeXt-Tiny/Small; no extra pip packages on Colab). Losses ignore 255:
    L = 1.0 * (0.5 BCE + 0.5 Dice)_roof + 0.5 * BCE_edge(pos_weight 4) + 0.5 * focal_corner
Augmentation: rot90/flip, GSD 0.10..0.25 m (scale 0.67..1.67 of the 0.15 m grid), seasonal colour,
hard shadows, blur, noise (roof2d_data.augment_photometric). bfloat16 autocast on CUDA.

Output is a PROPOSAL checkpoint + metrics, never an owner verdict.

    python compute/colab/scripts/train_roof2d.py --data workspace/colab_2d_roof_dataset_v3 --out <run dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof2d_data import IGNORE, SPLIT_TRAIN, SPLIT_VAL, augment_photometric, normalize_rgb, sample_crop  # noqa: E402

CROP = 512


ARCHS = ("resnet34", "convnext_tiny", "convnext_small")


def build_model(pretrained: bool = True, arch: str = "resnet34"):
    """UNet with a torchvision ImageNet encoder; logits (N, 3, H, W): channel 0 roof, 1 edge, 2 corner."""
    import torch
    import torch.nn as nn
    import torchvision

    class Up(nn.Module):
        def __init__(self, cin, cskip, cout):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv2d(cin + cskip, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
                nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
            )

        def forward(self, x, skip=None):
            x = nn.functional.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
            return self.conv(torch.cat([x, skip], 1) if skip is not None else x)

    class RoofUNet(nn.Module):
        def __init__(self):
            super().__init__()
            weights = torchvision.models.ResNet34_Weights.IMAGENET1K_V1 if pretrained else None
            r = torchvision.models.resnet34(weights=weights)
            self.stem = nn.Sequential(r.conv1, r.bn1, r.relu)  # /2, 64
            self.pool, self.l1, self.l2, self.l3, self.l4 = r.maxpool, r.layer1, r.layer2, r.layer3, r.layer4
            self.u4, self.u3 = Up(512, 256, 256), Up(256, 128, 128)
            self.u2, self.u1, self.u0 = Up(128, 64, 64), Up(64, 64, 64), Up(64, 0, 32)
            self.head = nn.Conv2d(32, 3, 1)

        def forward(self, x):
            s0 = self.stem(x)
            s1 = self.l1(self.pool(s0))
            s2 = self.l2(s1)
            s3 = self.l3(s2)
            s4 = self.l4(s3)
            return self.head(self.u0(self.u1(self.u2(self.u3(self.u4(s4, s3), s2), s1), s0)))

    class ConvNeXtUNet(nn.Module):
        """ConvNeXt stages give /4../32 skips; a small conv stem supplies the /2 skip for sharp outlines."""

        def __init__(self, name):
            super().__init__()
            wcls = {"convnext_tiny": torchvision.models.ConvNeXt_Tiny_Weights,
                    "convnext_small": torchvision.models.ConvNeXt_Small_Weights}[name]
            f = getattr(torchvision.models, name)(weights=wcls.IMAGENET1K_V1 if pretrained else None).features
            self.s4, self.s8 = nn.Sequential(f[0], f[1]), nn.Sequential(f[2], f[3])
            self.s16, self.s32 = nn.Sequential(f[4], f[5]), nn.Sequential(f[6], f[7])
            self.stem2 = nn.Sequential(nn.Conv2d(3, 32, 3, stride=2, padding=1, bias=False), nn.BatchNorm2d(32),
                                      nn.ReLU(inplace=True))
            self.u4, self.u3 = Up(768, 384, 256), Up(256, 192, 128)
            self.u2, self.u1, self.u0 = Up(128, 96, 64), Up(64, 32, 32), Up(32, 0, 32)
            self.head = nn.Conv2d(32, 3, 1)

        def forward(self, x):
            h = self.stem2(x)
            a = self.s4(x)
            b = self.s8(a)
            c = self.s16(b)
            d = self.s32(c)
            return self.head(self.u0(self.u1(self.u2(self.u3(self.u4(d, c), b), a), h)))

    if arch == "resnet34":
        return RoofUNet()
    if arch in ("convnext_tiny", "convnext_small"):
        return ConvNeXtUNet(arch)
    raise ValueError(f"unknown arch {arch!r}, expected one of {ARCHS}")


def multitask_loss(logits, target):
    """logits (N,3,H,W) float; target (N,3|4,H,W) uint8: roof {0,1,255}, edge/corner {0,1}, optional contact {0,1}.

    Contact pixels (shared walls between two owner roofs) weigh 5x in the outline loss.
    """
    import torch
    import torch.nn.functional as F

    roof_t = target[:, 0]
    valid = (roof_t != IGNORE).float()
    n_valid = valid.sum().clamp(min=1.0)
    t_roof = (roof_t == 1).float()
    zero = logits.sum() * 0.0
    if valid.sum() < 1:
        return zero, {"roof": 0.0, "edge": 0.0, "corner": 0.0}

    bce = (F.binary_cross_entropy_with_logits(logits[:, 0], t_roof, reduction="none") * valid).sum() / n_valid
    p = torch.sigmoid(logits[:, 0]) * valid
    dice = 1.0 - (2.0 * (p * t_roof).sum() + 1.0) / (p.sum() + (t_roof * valid).sum() + 1.0)
    roof_loss = 0.5 * bce + 0.5 * dice

    t_edge = target[:, 1].float()
    pw = torch.tensor(4.0, device=logits.device)
    w_edge = valid * (1.0 + 4.0 * target[:, 3].float()) if target.shape[1] > 3 else valid
    edge_loss = (F.binary_cross_entropy_with_logits(logits[:, 1], t_edge, pos_weight=pw, reduction="none") * w_edge).sum() / n_valid

    t_c = target[:, 2].float()
    pc = torch.sigmoid(logits[:, 2])
    ce = F.binary_cross_entropy_with_logits(logits[:, 2], t_c, reduction="none")
    pt = pc * t_c + (1 - pc) * (1 - t_c)
    alpha = 0.75 * t_c + 0.25 * (1 - t_c)
    corner_loss = (alpha * (1 - pt) ** 2 * ce * valid).sum() / n_valid * 10.0

    total = 1.0 * roof_loss + 0.5 * edge_loss + 0.5 * corner_loss
    return total, {"roof": float(roof_loss.detach()), "edge": float(edge_loss.detach()), "corner": float(corner_loss.detach())}


def load_rasters(data_dir: Path):
    """Return rgb (H,W,3), owner labels (C,H,W) [roof, edge, corner(, contact)], split (H,W), transform."""
    import rasterio

    with rasterio.open(data_dir / "aoi_rgb.tif") as src:
        rgb = np.moveaxis(src.read(), 0, -1)
        transform = src.transform
    names = [k for k in ("roof", "edge", "corner", "contact") if (data_dir / f"label_{k}.tif").is_file()]
    labels = np.stack([rasterio.open(data_dir / f"label_{k}.tif").read(1) for k in names])
    split = rasterio.open(data_dir / "split.tif").read(1)
    return rgb, labels, split, transform


def with_pseudo(labels: np.ndarray, pseudo: np.ndarray) -> np.ndarray:
    """Copy of labels where pseudo roofs (uint8 1 = V1..V6-gated loop output) fill pixels still 255.

    Owner positives and negatives are never overridden. Pseudo outlines get an edge target.
    """
    import cv2

    out = labels.copy()
    fill = (out[0] == IGNORE) & (pseudo == 1)
    out[0][fill] = 1
    grad = cv2.morphologyEx(fill.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(bool)
    out[1][grad & (out[0] != IGNORE)] = 1
    return out


def centers_of(labels_roof: np.ndarray, split: np.ndarray, which: int, step: int = 64) -> np.ndarray:
    """Grid-sampled (row, col) points that are known roof pixels in a split (crop anchors)."""
    sub = (labels_roof[::step, ::step] == 1) & (split[::step, ::step] == which)
    return np.argwhere(sub) * step


class CropDataset:
    def __init__(self, rgb, labels, split, n: int, seed: int):
        self.rgb, self.split = rgb, split
        self.labels = labels.copy()
        self.labels[0][split != SPLIT_TRAIN] = IGNORE  # training never sees val/buffer labels
        self.labels[1:, split != SPLIT_TRAIN] = 0
        self.pos = centers_of(self.labels[0], split, SPLIT_TRAIN)
        self.known = np.argwhere(self.labels[0][::32, ::32] != IGNORE) * 32
        self.n, self.seed = n, seed

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        rng = np.random.default_rng((self.seed, i, time.time_ns() % 1_000_003))
        pool = self.pos if (rng.random() < 0.6 and len(self.pos)) else self.known
        r, c = pool[int(rng.integers(len(pool)))] + rng.integers(-160, 161, size=2)
        scale = float(np.exp(rng.uniform(np.log(0.67), np.log(1.67))))
        img, lab = sample_crop(self.rgb, self.labels, (r, c), CROP, scale, rng)
        img = augment_photometric(img, rng)
        return normalize_rgb(img), lab


def val_crops(rgb, labels, split):
    """Fixed, non-augmented 512 crops: up to 40 anchored on val roofs and up to 40 on val known background.

    The background half makes the pixel IoU drop when the model paints roofs over trees or fields, which
    roof-anchored crops alone cannot see.
    """
    roof_pts = centers_of(labels[0], split, SPLIT_VAL, step=192)[:40]
    sub = (labels[0][::256, ::256] == 0) & (split[::256, ::256] == SPLIT_VAL)
    bg_pts = (np.argwhere(sub) * 256)[:40]
    out = []
    for r, c in list(roof_pts) + list(bg_pts):
        img, lab = sample_crop(rgb, labels, (r, c), CROP, 1.0, None)
        out.append((normalize_rgb(img), lab))
    return out


def evaluate(model, crops, device, dtype):
    import torch

    inter = union = tp = fn = 0
    model.eval()
    with torch.no_grad(), torch.autocast(device, dtype=dtype, enabled=device == "cuda"):
        for i in range(0, len(crops), 8):
            x = torch.from_numpy(np.stack([c[0] for c in crops[i : i + 8]])).to(device)
            y = np.stack([c[1][0] for c in crops[i : i + 8]])
            pred = (torch.sigmoid(model(x)[:, 0].float()) > 0.5).cpu().numpy()
            valid = y != IGNORE
            t = y == 1
            inter += int((pred & t & valid).sum())
            union += int(((pred | t) & valid).sum())
            tp += int((pred & t).sum())
            fn += int((~pred & t).sum())
    model.train()
    return {"val_pixel_iou": inter / max(union, 1), "val_roof_recall": tp / max(tp + fn, 1)}


def train(data_dir: Path, out: Path, epochs: int, samples_per_epoch: int, batch_size: int, lr: float,
          init: Path | None = None, pseudo: Path | None = None, workers: int = 2, seed: int = 0,
          arch: str = "resnet34") -> dict:
    import torch
    from torch.utils.data import DataLoader

    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float16
    gpu = torch.cuda.get_device_name(0) if device == "cuda" else "cpu"
    torch.manual_seed(seed)

    import rasterio

    rgb, labels, split, _ = load_rasters(data_dir)
    train_labels = with_pseudo(labels, rasterio.open(pseudo).read(1)) if pseudo else labels
    ds = CropDataset(rgb, train_labels, split, samples_per_epoch, seed)
    dl = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=workers, drop_last=True,
                    persistent_workers=workers > 0)
    vcrops = val_crops(rgb, labels, split)

    model = build_model(pretrained=init is None, arch=arch).to(device)
    if init is not None:
        model.load_state_dict(torch.load(init, map_location=device)["model"])
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * len(dl), pct_start=0.1)

    history, best = [], -1.0
    for epoch in range(epochs):
        t0, parts = time.time(), []
        for x, y in dl:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device, dtype=dtype, enabled=device == "cuda"):
                logits = model(x)
            loss, comp = multitask_loss(logits.float(), y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            parts.append([float(loss)] + list(comp.values()))
        m = evaluate(model, vcrops, device, dtype)
        rec = {"epoch": epoch, "loss": round(float(np.mean([p[0] for p in parts])), 4),
               **{k: round(float(np.mean([p[i + 1] for p in parts])), 4) for i, k in enumerate(("roof", "edge", "corner"))},
               **{k: round(v, 4) for k, v in m.items()}, "seconds": round(time.time() - t0, 1)}
        history.append(rec)
        print(json.dumps(rec), flush=True)
        state = {"model": model.state_dict(), "epoch": epoch, "history": history, "arch": arch}
        torch.save(state, out / "latest.pt")
        if m["val_pixel_iou"] > best:
            best = m["val_pixel_iou"]
            torch.save(state, out / "best.pt")

    metrics = {
        "status": "PROPOSAL_NOT_ACCEPTED",
        "device": gpu,
        "autocast_dtype": str(dtype).replace("torch.", ""),
        "epochs": epochs,
        "samples_per_epoch": samples_per_epoch,
        "batch_size": batch_size,
        "best_val_pixel_iou": round(best, 4),
        "val_crops": len(vcrops),
        "pseudo_labels": str(pseudo) if pseudo else None,
        "init": str(init) if init else "imagenet",
        "arch": arch,
        "peak_vram_mib": round(torch.cuda.max_memory_allocated() / 2**20, 1) if device == "cuda" else None,
        "history": history,
    }
    (out / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--samples-per-epoch", type=int, default=480)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--init", type=Path)
    ap.add_argument("--pseudo", type=Path)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--arch", choices=ARCHS, default="resnet34")
    args = ap.parse_args(argv)
    m = train(args.data, args.out, args.epochs, args.samples_per_epoch, args.batch_size, args.lr,
              args.init, args.pseudo, args.workers, arch=args.arch)
    print("best_val_pixel_iou", m["best_val_pixel_iou"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
