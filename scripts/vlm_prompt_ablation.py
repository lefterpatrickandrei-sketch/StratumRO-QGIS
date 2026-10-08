"""Prompt-ablation test: does the audit PROMPT cause the false approvals?

Measured tension on 2026-10-08:
  * probe_remaining_routes.py, NEUTRAL prompt ("Describe this chip."),
    gemini-3.1-flash-lite  -> rejected noise, solid_red, solid_white,
    described the real chip correctly                        => 4/4 correct
  * tools/vlm_real_audit.py, build_cadastral_prompt() asks
    "is this a real building?" and gemini-3.1-flash-lite    -> approved noise,
    solid_white, solid_blue, solid_green                     => 1/4 correct

Hypothesis: a leading yes/no question invites acquiescence, so the model must be
asked to DESCRIBE the image first and only then classify it.

This script measures discrimination for several prompt templates over the same
17 falsification controls, so the choice is evidence-based.

Usage:
  venv\\Scripts\\python.exe scripts\\vlm_prompt_ablation.py
"""
import json
import os
import sys
import threading
import time

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

from stratum_ro.ai.providers.gemini_provider import GeminiProvider  # noqa: E402
from stratum_ro.ai.vlm_verifier import (  # noqa: E402
    build_cadastral_prompt, crop_building_chip, encode_chip_base64,
)

GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
ORTHO = os.path.join(ROOT, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
MODEL = "gemini-3.1-flash-lite"

_lock = threading.Lock()
_last = [0.0]


def gated_call(prov, chip, system_p, user_p, max_tokens, gate=4.5):
    """One Gemini call with a global 4.5s spacing (free-tier 15 RPM)."""
    with _lock:
        now = time.time()
        if now < _last[0]:
            time.sleep(_last[0] - now)
        _last[0] = time.time() + gate
    b64 = encode_chip_base64(chip, "JPEG", 85)
    return prov.generate(prompt=user_p, system_prompt=system_p, images=[b64],
                         model=MODEL, timeout=90.0, max_tokens=max_tokens,
                         temperature=0.0)


# --------------------------------------------------------------------------
# prompt templates
# --------------------------------------------------------------------------
SYS_AUDIT = None  # uses build_cadastral_prompt's own system prompt


def tpl_audit(bid, area, perim, h):
    sys_p, usr_p = build_cadastral_prompt(
        building_id=bid, area_m2=area, perimeter_m=perim, ndsm_height_m=h)
    return sys_p, usr_p, 700


NEUTRAL_SYS = (
    "You are a photogrammetry technician auditing orthophoto chips for a "
    "Romanian pre-cadastral project. Answer only from what is visible in the "
    "image. Never assume a building is present."
)

DESCRIBE_FIRST = (
    "Describe this orthophoto chip in one short paragraph: what the dominant "
    "surface texture is, whether straight edges, a roof ridge, shadow or "
    "ground/vegetation are visible, and whether any structure is present at "
    "all. Then on a new line output exactly:\n"
    "IMAGE_IS_BUILDING: yes|no\n"
    "If no building is visible, say why in one sentence."
)

CLS_FIRST = (
    "Look at this orthophoto chip. Output exactly these lines:\n"
    "IMAGE_IS_BUILDING: yes|no\n"
    "EVIDENCE: one sentence naming the visible pixel evidence\n"
    "Answer 'no' for noise, blank colour, blurred or vegetation-only chips."
)


def tpl_neutral(bid, area, perim, h):
    return NEUTRAL_SYS, DESCRIBE_FIRST, 200


def tpl_strict(bid, area, perim, h):
    return NEUTRAL_SYS, CLS_FIRST, 120


def tpl_neutral_json(bid, area, perim, h):
    return NEUTRAL_SYS, (
        DESCRIBE_FIRST
        + "\nThen output JSON: {\"is_real_building\": bool, "
          "\"confidence\": 0.0-1.0, \"reasoning\": \"...\"}"), 400


TEMPLATES = [
    ("audit_current", tpl_audit),
    ("neutral_describe_first", tpl_neutral),
    ("strict_classify_first", tpl_strict),
    ("neutral_describe_then_json", tpl_neutral_json),
]


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------
def build_controls(real_chip):
    ctrls = []
    rng = np.random.default_rng(7)
    ctrls.append(("noise", Image.fromarray(
        rng.integers(0, 255, (512, 512, 3), dtype=np.uint8)), False))
    for nm, rgb in (("solid_red", (220, 30, 30)), ("solid_white", (250, 250, 248)),
                    ("solid_blue", (30, 60, 220)), ("solid_green", (30, 200, 60)),
                    ("solid_black", (8, 8, 8))):
        ctrls.append((nm, Image.new("RGB", (512, 512), rgb), False))
    ctrls.append(("blur_far", real_chip.filter(ImageFilter.GaussianBlur(9)), False))
    inv = real_chip.transpose(Image.FLIP_LEFT_RIGHT)
    ctrls.append(("inverted", Image.eval(real_chip, lambda v: 255 - v), False))
    ctrls.append(("real_positive", real_chip, True))
    return ctrls


def verdict_of(text):
    """Parse IMAGE_IS_BUILDING / is_real_building out of a free-text reply."""
    t = (text or "").lower()
    if "image_is_building: yes" in t or '"is_real_building": true' in t:
        return True
    if "image_is_building: no" in t or '"is_real_building": false' in t:
        return False
    # fall back: look for an explicit no/negative mention near the top
    if t.startswith("no") or " does not contain" in t or "no visual information" in t:
        return False
    return None


def main():
    import geopandas as gpd

    gdf = gpd.read_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN")
    row = gdf.iloc[0]
    chip = crop_building_chip(ortho_path=ORTHO, polygon=row.geometry,
                              padding_m=6.0, target_size=(512, 512))
    if chip is None:
        print("[!] chip crop failed")
        return
    ctrls = build_controls(chip)
    area = float(row["area_m2"]); perim = float(row["perimeter_m"])
    h = float(row["inaltime_med_m"]) if "inaltime_med_m" in gdf.columns else None

    prov = GeminiProvider()
    if not prov.is_available():
        print("[!] GEMINI_API_KEY missing")
        return

    table = {}
    for tname, tfn in TEMPLATES:
        sys_p, usr_p, mt = tfn("probe", area, perim, h)
        correct = 0
        detail = []
        for cname, img, expect_yes in ctrls:
            r = gated_call(prov, img, sys_p, usr_p, mt)
            if not r.is_ok():
                detail.append("%s=ERR(%s)" % (cname, (r.error or "")[:40]))
                continue
            got = verdict_of(r.content)
            ok = (got is not None and got == expect_yes)
            correct += 1 if ok else 0
            detail.append("%s=%s%s" % (cname, "YES" if got else ("NO" if got is False else "?"),
                                       "" if ok else "!"))
            print("  %-26s %-14s expect=%-3s got=%-4s %s (%.1fs)"
                  % (tname, cname, expect_yes, got, "OK" if ok else "WRONG",
                     r.duration_sec))
        table[tname] = (correct, len(ctrls), detail)

    print("\n=== DISCRIMINATION BY PROMPT TEMPLATE ===")
    for tname, (c, n, _) in sorted(table.items(), key=lambda x: -x[1][0]):
        print("  %-30s %d/%d = %.0f%%" % (tname, c, n, 100.0 * c / n))

    out = os.path.join(ROOT, "workspace", "output", "vlm_prompt_ablation.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({k: {"correct": v[0], "n": v[1], "detail": v[2]}
                   for k, v in table.items()}, fh, indent=1)
    print("\n[*] written %s" % out)


if __name__ == "__main__":
    main()