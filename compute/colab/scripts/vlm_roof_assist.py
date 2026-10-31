"""VLM assistant for the 2D roof loop (Colab A100): Qwen3-VL-8B judges each outline and names the roof type.

Reuses the approach of the unmerged B1 job (branch feat/hybrid-dev-workflow, 5ce4746, vlm_eval_b1.py): same
model, label likelihood instead of free text. Here the label probability is read from the first-token logits
after a prefilled answer prefix (labels have distinct first tokens), so each question costs one forward pass.

Questions per chip (only pixels reach the VM, never coordinates):
  verdict    ADMIS | AJUSTARE | ELIMINAT          (owner's canonical meaning, see VERDICT_PROMPT)
  roof_type  FLAT | SHED | GABLE | HIP | MANSARD | COMPLEX | OTHER

Modes:
  classify   all chips of chips_manifest.json -> vlm_predictions.json (+ calibration on the owner set)
  lora       LoRA SFT of the verdict on owner chips of the train split, pick the epoch on owner val, then classify

The VLM output is advice for the owner. It never sets ADMIS; the local merge maps it to ADMIS_PROPUS / INCERT.

    python vlm_roof_assist.py --chips <dir with chips/ and chips_manifest.json> --out <dir> [--mode lora]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

MODEL = "Qwen/Qwen3-VL-8B-Instruct"
VERDICTS = ["ADMIS", "AJUSTARE", "ELIMINAT"]
ROOFS = ["FLAT", "SHED", "GABLE", "HIP", "MANSARD", "COMPLEX", "OTHER"]
VERDICT_PROMPT = (
    "Aerial orthophoto chip of Cluj-Napoca, Romania, about 7.5 cm per pixel. A proposed roof outline is drawn in "
    "magenta; the colour itself carries no meaning.\n"
    "Answer with exactly one label:\n"
    "ADMIS - the magenta outline encloses one real building roof and follows its eaves well (small offsets are fine).\n"
    "AJUSTARE - it is a real building roof, but the outline needs correction: it misses part of the roof, cuts a "
    "corner, covers a neighbouring building too, or spills onto the ground.\n"
    "ELIMINAT - not a building roof: trees, bushes, ground, road, parked cars, tombs, construction pit, shadow, "
    "or a black no-data area."
)
ROOF_PROMPT = (
    "Aerial orthophoto chip, about 7.5 cm per pixel. Look at the building roof inside the magenta outline and "
    "classify its shape with exactly one label:\n"
    "FLAT - flat roof or terrace. SHED - one single slope. GABLE - two slopes meeting at one ridge. "
    "HIP - four slopes (or a pyramid). MANSARD - two slopes per side with a break. "
    "COMPLEX - several ridges or wings (L, T, U shaped roof). OTHER - dome, glass, or not a roof."
)


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


class VLM:
    def __init__(self, torch, max_pixels: int = 640 * 640):
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(MODEL)
        self.processor.image_processor.max_pixels = max_pixels
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL, torch_dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa").eval()
        tok = self.processor.tokenizer
        self.first_ids = {}
        for group in (VERDICTS, ROOFS):
            ids = [tok.encode(" " + lab, add_special_tokens=False)[0] for lab in group]
            if len(set(ids)) != len(ids):
                raise RuntimeError(f"labels share a first token: {group}")
            self.first_ids[tuple(group)] = ids

    def inputs(self, image, prompt: str, answer_prefix: str, answer: str = ""):
        msgs = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
        text = self.processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        return self.processor(text=[text + answer_prefix + answer], images=[image], return_tensors="pt").to(self.model.device)

    def probs(self, image, prompt: str, answer_prefix: str, labels: list[str]) -> dict:
        x = self.inputs(image, prompt, answer_prefix)
        with self.torch.no_grad():
            logits = self.model(**x).logits[0, -1].float()
        sel = logits[self.first_ids[tuple(labels)]]
        p = self.torch.softmax(sel, -1).tolist()
        return {lab: round(v, 4) for lab, v in zip(labels, p)}


def load(chips: Path):
    from PIL import Image

    manifest = json.loads((chips / "chips_manifest.json").read_text(encoding="utf-8"))
    def img(cid):
        p = chips / "chips" / f"{cid}.jpg"
        return Image.open(p if p.is_file() else chips / "chips" / f"{cid}.png").convert("RGB")

    return manifest, img


def owner_split(manifest: list[dict], seed: int = 0) -> dict:
    """Stratified 60/40 split of the owner chips (train for LoRA, val for epoch choice and calibration)."""
    rng = random.Random(seed)
    split = {}
    for lab in VERDICTS:
        ids = sorted(m["id"] for m in manifest if m["set"] == "owner" and m["owner_verdict"] == lab)
        rng.shuffle(ids)
        k = int(round(0.6 * len(ids)))
        split.update({i: "train" for i in ids[:k]})
        split.update({i: "val" for i in ids[k:]})
    return split


def calibration(preds: dict, manifest: list[dict], ids: set | None = None) -> dict:
    rows = [m for m in manifest if m["set"] == "owner" and (ids is None or m["id"] in ids)]
    conf = {t: {p: 0 for p in VERDICTS} for t in VERDICTS}
    for m in rows:
        p = preds[m["id"]]["verdict"]
        conf[m["owner_verdict"]][max(p, key=p.get)] += 1
    n = len(rows)
    acc = sum(conf[t][t] for t in VERDICTS) / max(n, 1)
    recall = {t: round(conf[t][t] / max(sum(conf[t].values()), 1), 3) for t in VERDICTS}
    admis_pred = sum(conf[t]["ADMIS"] for t in VERDICTS)
    return {"n": n, "accuracy": round(acc, 3), "macro_recall": round(sum(recall.values()) / 3, 3), "recall": recall,
            "admis_precision": round(conf["ADMIS"]["ADMIS"] / max(admis_pred, 1), 3),
            "always_admis_accuracy": round(sum(1 for m in rows if m["owner_verdict"] == "ADMIS") / max(n, 1), 3),
            "confusion_true_rows": conf}


def classify(vlm: VLM, manifest, img, roof_too: bool = True) -> dict:
    preds = {}
    for i, m in enumerate(manifest, 1):
        try:
            im = img(m["id"])
            rec = {"verdict": vlm.probs(im, VERDICT_PROMPT, "Label:", VERDICTS)}
            if roof_too:
                rec["roof_type"] = vlm.probs(im, ROOF_PROMPT, "Roof:", ROOFS)
        except Exception as exc:  # noqa: BLE001 - fail closed per chip
            rec = {"verdict": {"ADMIS": 0.0, "AJUSTARE": 1.0, "ELIMINAT": 0.0}, "error": repr(exc)}
        preds[m["id"]] = rec
        if i % 100 == 0:
            log(f"classified {i}/{len(manifest)}")
    return preds


def train_lora(vlm: VLM, manifest, img, split: dict, epochs: int, lr: float) -> dict:
    torch = vlm.torch
    from peft import LoraConfig, get_peft_model

    model = get_peft_model(vlm.model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                                 target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    vlm.model = model
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    owner = {m["id"]: m for m in manifest if m["set"] == "owner"}
    train = [i for i, s in split.items() if s == "train"]
    val = {i for i, s in split.items() if s == "val"}
    freq = {lab: sum(1 for i in train if owner[i]["owner_verdict"] == lab) for lab in VERDICTS}
    weights = [1 / math.sqrt(freq[owner[i]["owner_verdict"]]) for i in train]
    rng = random.Random(0)
    history, best = [], (-1.0, None, 0)
    for epoch in range(1, epochs + 1):
        model.train()
        total = 0.0
        for k, cid in enumerate(rng.choices(train, weights=weights, k=len(train)), 1):
            im = img(cid)
            n_prefix = vlm.inputs(im, VERDICT_PROMPT, "Label:")["input_ids"].shape[1]
            x = vlm.inputs(im, VERDICT_PROMPT, "Label:", " " + owner[cid]["owner_verdict"])
            labels = x["input_ids"].clone()
            labels[:, :n_prefix] = -100
            loss = model(**x, labels=labels).loss / 4
            loss.backward()
            total += float(loss) * 4
            if k % 4 == 0:
                opt.step()
                opt.zero_grad()
        opt.step()
        opt.zero_grad()
        model.eval()
        vp = classify(vlm, [owner[i] for i in val], img, roof_too=False)
        cal = calibration(vp, manifest, val)
        history.append({"epoch": epoch, "train_loss": round(total / len(train), 4), "val": cal})
        log(f"lora epoch {epoch}: loss {history[-1]['train_loss']} val macro {cal['macro_recall']} acc {cal['accuracy']}")
        if cal["macro_recall"] > best[0]:
            best = (cal["macro_recall"], {k: v.detach().clone() for k, v in model.state_dict().items() if "lora_" in k}, epoch)
    model.load_state_dict(best[1], strict=False)
    model.eval()
    return {"history": history, "best_epoch": best[2], "train_counts": freq, "lr": lr, "r": 16}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chips", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=("classify", "lora"), default="classify")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    args = ap.parse_args(argv)
    import torch

    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    manifest, img = load(args.chips)
    vlm = VLM(torch)
    log(f"loaded {MODEL} on {torch.cuda.get_device_name(0)}")
    split = owner_split(manifest)
    report = {"model": MODEL, "mode": args.mode, "gpu": torch.cuda.get_device_name(0), "status": "ADVICE_NOT_VERDICT"}
    if args.mode == "lora":
        report["lora"] = train_lora(vlm, manifest, img, split, args.epochs, args.lr)
    preds = classify(vlm, manifest, img)
    report["calibration_owner_all"] = calibration(preds, manifest)
    report["calibration_owner_val"] = calibration(preds, manifest, {i for i, s in split.items() if s == "val"})
    report["owner_split"] = split
    report["minutes"] = round((time.time() - t0) / 60, 1)
    report["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 1)
    (args.out / "vlm_predictions.json").write_text(json.dumps(preds), encoding="utf-8")
    (args.out / "vlm_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(json.dumps({k: report[k] for k in ("calibration_owner_all", "calibration_owner_val", "minutes")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
