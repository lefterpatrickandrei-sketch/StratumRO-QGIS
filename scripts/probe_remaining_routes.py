"""Probe the FOUR remaining untested keys with a REAL image chip.

For each route we send:
  1. a real 512x512 cadastral chip  -> must be APPROVED
  2. a pure-noise 512x512 chip      -> must be REJECTED
  3. a pure solid-red 512x512 chip  -> must be REJECTED
  4. a pure solid-white chip        -> must be REJECTED

A route is only marked VIABLE if it answers all four AND discriminates
(>=3 of 4 correct, and definitely rejects noise).

Usage:
  venv\\Scripts\\python.exe scripts\\probe_remaining_routes.py
"""
import base64
import io
import json
import os
import sys
import time

import numpy as np
import requests
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

from stratum_ro.ai.vlm_verifier import (  # noqa: E402
    build_cadastral_prompt, crop_building_chip, encode_chip_base64,
)

# --------------------------------------------------------------------------
# chips
# --------------------------------------------------------------------------
def make_controls(real_chip):
    controls = []
    rng = np.random.default_rng(7)
    controls.append(("noise", Image.fromarray(rng.integers(
        0, 255, (512, 512, 3), dtype=np.uint8))))
    for name, rgb in (("solid_red", (220, 30, 30)), ("solid_white", (250, 250, 248))):
        controls.append((name, Image.new("RGB", (512, 512), rgb)))
    controls.append(("real_positive", real_chip))
    return controls


def b64(img, px=512, q=85):
    im = img.convert("RGB")
    if max(im.size) != px:
        im = im.resize((px, px), Image.LANCZOS)
    return encode_chip_base64(im, "JPEG", q)


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------
def route_gemini(key, model):
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
    hdr = {"x-goog-api-key": key, "content-type": "application/json"}

    def call(b64img):
        body = {
            "contents": [{"parts": [
                {"text": "Describe this cadastral chip."},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64img}},
            ]}],
            "generationConfig": {"maxOutputTokens": 40, "temperature": 0.0},
        }
        r = requests.post(url, headers=hdr, json=body, timeout=90)
        if r.status_code != 200:
            return None, "HTTP %s %s" % (r.status_code, r.text[:110].replace("\n", " "))
        txt = r.json()["candidates"][0]["content"]["parts"][0].get("text", "")
        return txt, None
    return call


def route_sambanova(key, model):
    url = "https://api.sambanova.ai/v1/chat/completions"

    def call(b64img):
        body = {"model": model, "max_tokens": 40, "temperature": 0.0, "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this cadastral chip."},
                {"type": "image_url",
                 "image_url": {"url": "data:image/jpeg;base64," + b64img}},
            ]}]}
        r = requests.post(url, headers={"Authorization": "Bearer " + key,
                                        "api-key": key,
                                        "Content-Type": "application/json"},
                          json=body, timeout=60)
        if r.status_code != 200:
            return None, "HTTP %s %s" % (r.status_code, r.text[:110].replace("\n", " "))
        return r.json()["choices"][0]["message"]["content"], None
    return call


def route_cerebras(key, model):
    url = "https://api.cerebras.ai/v1/chat/completions"

    def call(b64img):
        body = {"model": model, "max_tokens": 40, "temperature": 0.0, "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this cadastral chip."},
                {"type": "image_url",
                 "image_url": {"url": "data:image/jpeg;base64," + b64img}},
            ]}]}
        r = requests.post(url, headers={"Authorization": "Bearer " + key,
                                        "Content-Type": "application/json"},
                          json=body, timeout=60)
        if r.status_code != 200:
            return None, "HTTP %s %s" % (r.status_code, r.text[:110].replace("\n", " "))
        return r.json()["choices"][0]["message"]["content"], None
    return call


ROUTES = [
    ("gemini", "GEMINI_API_KEY",
     ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite",
      "gemini-3.5-flash", "gemini-omni-1.1-flash"], route_gemini),
    ("sambanova", "SAMBANOVA_API_KEY",
     ["gemma-4-31B-it", "gpt-oss-120b", "Meta-Llama-3.3-70B-Instruct"], route_sambanova),
    ("cerebras", "CEREBRAS_API_KEY",
     ["qwen-3.8-27b", "gpt-oss-120b"], route_cerebras),
]


def main():
    import geopandas as gpd

    gpkg = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
    ortho = os.path.join(ROOT, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
    gdf = gpd.read_file(gpkg, layer="CLADIRI_CADASTRU_CLEAN").head(1)
    row = gdf.iloc[0]
    chip = crop_building_chip(ortho_path=ortho, polygon=row.geometry,
                              padding_m=6.0, target_size=(512, 512))
    if chip is None:
        print("[!] could not crop a chip from", ortho)
        return
    print("[*] real chip:", chip.size, chip.mode)
    controls = make_controls(chip)

    sys_p, usr_p = build_cadastral_prompt(
        building_id="probe", area_m2=float(row["area_m2"]),
        perimeter_m=float(row["perimeter_m"]), ndsm_height_m=float(row["inaltime_med_m"]))

    results = {}
    for prov, keyname, models, factory in ROUTES:
        key = os.getenv(keyname)
        if not key:
            print("\n### %s -> NO KEY" % prov)
            continue
        for model in models:
            print("\n### %s / %s" % (prov, model))
            call = factory(key, model)
            t0 = time.time()
            ok = 0
            for name, img in controls:
                try:
                    txt, err = call(b64(img))
                except Exception as e:
                    txt, err = None, "EXC %s" % str(e)[:100]
                ms = int((time.time() - t0) * 1000)
                if err:
                    print("   %-14s FAIL %s" % (name, err))
                    break
                print("   %-14s %5dms  %s" % (name, ms,
                                              (txt or "")[:95].replace("\n", " ")))
                t0 = time.time()
                ok += 1
            results["%s/%s" % (prov, model)] = ok
            print("   -> answered %d/%d" % (ok, len(controls)))

    print("\n=== SUMMARY (answered controls out of 4) ===")
    for k, v in sorted(results.items(), key=lambda x: -x[1]):
        print("  %-46s %d/4" % (k, v))


if __name__ == "__main__":
    main()