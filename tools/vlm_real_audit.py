# -*- coding: utf-8 -*-
"""
StratumRO — P3: Real Vision-Language-Model cadastral audit.

Replaces the previous 'VLM_AUDITED_BUILDINGS' layer, which was produced by
calling VLMVerifier._heuristic_fallback(..., chip=None) directly and therefore
never sent a single pixel to any model (100% APPROVED, verdict = f(area > 45 m2)).

This script:
  1. crops a real orthophoto chip for every candidate footprint,
  2. sends the chip to a real vision model through a genuine provider chain,
  3. records the raw model reply, latency and token usage per building,
  4. runs FALSIFICATION CONTROLS (solid-colour, noise, vegetation, real) so the
     verdict distribution is falsifiable instead of self-confirming,
  5. writes GPKG layer 'VLM_REAL_AUDIT' + a full JSON transcript on disk.

Evidence classes: MEASURED (real API replies) and VALIDATED (controls must
discriminate, otherwise the audit is reported as non-discriminative).

Usage:
    venv\\Scripts\\python tools\\vlm_real_audit.py
    venv\\Scripts\\python tools\\vlm_real_audit.py --limit 20 --force
"""

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import random
import sys
import threading
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.abspath("."))

import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds

from stratum_ro.ai.providers.anthropic_provider import AnthropicProvider
from stratum_ro.ai.providers.gemini_provider import GeminiProvider
from stratum_ro.ai.providers.nvidia_nim_provider import NvidiaNIMProvider
from stratum_ro.ai.providers.ollama_provider import OllamaProvider
from stratum_ro.ai.providers.openai_provider import OpenAIProvider
from stratum_ro.ai.providers.union_alpha_provider import UnionAlphaProvider
from stratum_ro.ai.vlm_verifier import crop_building_chip, encode_chip_base64

GPKG = "workspace/output/cladiri_stereo70.gpkg"
ORTHO = "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
NDSM = "workspace/output/ndsm_stereo70.tif"
CAND_LAYER = "CLADIRI_HIBRID"
OUT_LAYER = "VLM_REAL_AUDIT"
TRANSCRIPT = "workspace/output/vlm_real_audit_transcript.json"
CSV_OUT = "workspace/output/vlm_real_audit.csv"

# Ordered fallback chain. Every entry genuinely transmits images and was probed
# live on 2026-10-08 with a synthetic chip before being trusted:
#   openrouter/google/gemini-2.5-flash        1919 ms  img_sent=1  json OK
#   openrouter/openai/gpt-4o                  2890 ms  img_sent=1  json OK
#   openrouter/qwen/qwen-2.5-vl-72b-instruct  3042 ms  img_sent=1  json OK
#   nvidia/meta/llama-3.2-11b-vision-instruct 5741 ms img_sent=1  json OK
# Direct openai + anthropic are kept last as rescuers: both returned HTTP 429
# "no credits remaining" / "credit balance too low" during the probe, so they
# currently only succeed when the account is topped up.
# (provider, model, max_tokens, chip_px)
# max_tokens is measured per route: OpenRouter returns HTTP 402 "This request
# requires more credits, or fewer max_tokens" for image payloads above ~200.
# Chip size is also measured: gemini-2.5-flash refuses >512px chips at mt=200.
# NOTE (2026-10-08): the OpenRouter balance is now NEGATIVE (-0.20 USD, the
# trial credit was consumed by probing), so OpenAI/Anthropic/OpenRouter are all
# dead. Gemini's free tier is the only route that passed the falsification
# controls, so it goes first; NVIDIA stays as the last-resort fallback even
# though llama-3.2-11b-vision scores 1/9 on discrimination.
CHAIN = [
    ("gemini", "gemini-3.1-flash-lite", 400, 512),
    ("gemini", "gemini-3.8-flash", 400, 512),
    ("union_alpha", "google/gemini-2.5-flash", 400, 512),
    ("nvidia", "meta/llama-3.2-11b-vision-instruct", 400, 512),
    ("openai", "gpt-4o", 400, 512),
    ("anthropic", "claude-3-7-sonnet-latest", 400, 512),
    ("ollama", "minicpm-v:8b", 400, 512),
]
PROVIDERS = {
    "union_alpha": UnionAlphaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "nvidia": NvidiaNIMProvider,
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
}

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, flush=True)


class RateGate:
    """Serialises calls to a provider and enforces a minimum interval.

    Necessary because the Gemini free tier enforces ~15 requests/minute and
    answers 429 to bursts. Without this gate, 4 parallel workers exhausted the
    quota on the 17 falsification controls and every real candidate then fell
    through to the non-discriminative NVIDIA fallback.
    """

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self):
        with self._lock:
            now = time.time()
            if now < self._next_at:
                time.sleep(self._next_at - now)
                now = time.time()
            self._next_at = now + self.min_interval


# measured quota: free tier burst limit is 15 RPM
RATE_GATES = {
    "gemini": RateGate(4.5),
    "union_alpha": RateGate(1.2),
    "openai": RateGate(0.5),
    "anthropic": RateGate(0.5),
    "nvidia": RateGate(0.0),
    "ollama": RateGate(0.0),
}


# --------------------------------------------------------------------------
# Control-chip synthesis
# --------------------------------------------------------------------------
def control_chips(real_chip, rng):
    """
    Build falsification controls from a real chip.

    The controls reuse the geometry metadata of a genuine building but replace
    the imagery, so the ONLY thing that can change the verdict is the picture.
    """
    if real_chip is None:
        return []
    w, h = real_chip.size
    arr = np.asarray(real_chip.convert("RGB"))
    out = []

    # 1. solid colours: a building cannot look like a flat colour field
    for name, rgb in [("red", (220, 20, 20)), ("green", (20, 200, 60)),
                      ("blue", (25, 40, 220)), ("white", (250, 250, 250)),
                      ("black", (6, 6, 6))]:
        c = Image.new("RGB", (w, h), rgb)
        out.append(("solid_%s" % name, c))

    # 2. uniform Gaussian noise: no structure, no roof, no shadow
    noise = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    out.append(("noise", Image.fromarray(noise)))

    # 3. blurred-to-nothing: image content destroyed, geometry intact
    out.append(("blur_far", real_chip.convert("RGB").filter(
        ImageFilter.GaussianBlur(radius=max(w, h) / 2.0))))

    # 4. inverted photo: still structured, but semantically destroyed
    out.append(("inverted", Image.fromarray(255 - arr)))

    return out


def vegetation_controls(unc_gdf, n=8, seed=7):
    """Chips centred on UNCLASSIFIED (non-building) polygons."""
    if unc_gdf is None or len(unc_gdf) == 0:
        return []
    rng = random.Random(seed)
    picks = rng.sample(list(unc_gdf.index), min(n, len(unc_gdf)))
    out = []
    for i in picks:
        geom = unc_gdf.loc[i].geometry
        if geom is None or geom.is_empty:
            continue
        chip = crop_building_chip(ortho_path=ORTHO, polygon=geom, padding_m=6.0,
                                  target_size=(512, 512), draw_contour=True)
        if chip is not None:
            out.append(("vegetation_%d" % i, chip))
    return out


# --------------------------------------------------------------------------
# Audit prompt -- MEASURED, do not "simplify" this back to a yes/no question.
#
# scripts/vlm_prompt_ablation.py ran the same 9 falsification controls against
# gemini-3.1-flash-lite with 4 prompt templates (2026-10-08):
#     audit_current  (asks "is this a real building?")   -> 2/9  = 22%
#     neutral_describe_first                              -> 7/9  = 78%
#     strict_classify_first                               -> 7/9  = 78%
#     neutral_describe_then_json (this one)               -> 8/9  = 89%
# A leading yes/no question invites acquiescence: the leading question was
# what made the previous VLM layer approve pure noise. Describe-first forces
# the model to commit to visible evidence before it is allowed to classify.
# --------------------------------------------------------------------------
AUDIT_SYSTEM_PROMPT = (
    "You are a photogrammetry technician auditing orthophoto chips for a "
    "Romanian pre-cadastral project. Answer only from what is visible in the "
    "image. Never assume a building is present."
)

AUDIT_TASK_PROMPT = (
    "Describe this orthophoto chip in one short paragraph: what the dominant "
    "surface texture is, whether straight edges, a roof ridge, shadow or "
    "ground/vegetation are visible, and whether any structure is present at "
    "all. Then on a new line output exactly:\n"
    "IMAGE_IS_BUILDING: yes|no\n"
    "Then output JSON with these keys: is_real_building (boolean), "
    "ancpi_code (1CC, 1CC-ANEXA, 2CC, 2CC-ANEXA, 3CC, 4CC or FALSE_POSITIVE), "
    "roof_type, confidence (0.0-1.0), reasoning (one sentence of pixel "
    "evidence). Use FALSE_POSITIVE for noise, blank colour, blurred or "
    "vegetation-only chips."
)


# --------------------------------------------------------------------------
# Single VLM call with fallback chain
# --------------------------------------------------------------------------
_B64_CACHE = {}


def chip_b64(chip, px, quality=88):
    """Encode a chip (PIL Image) at a specific pixel size.

    The cache key MUST include a content digest. Keying on (size, px, quality)
    alone is wrong: every chip here is 512x512, so all buildings and all
    falsification controls silently shared the first image's bytes, which made
    the audit report the same reasoning for solid_red, solid_green and the real
    building. That bug was measured on 2026-10-08 (16/17 "discrimination" was
    really one image judged 17 times).
    """
    img = chip.convert("RGB")
    if max(img.size) != px:
        img = img.resize((px, px), Image.LANCZOS)
    digest = hashlib.sha256(img.tobytes()).hexdigest()[:20]
    key = (digest, px, quality)
    if key not in _B64_CACHE:
        _B64_CACHE[key] = encode_chip_base64(img, "JPEG", quality)
    return _B64_CACHE[key]


def call_vlm(chip, area_m2, perim_m, ndsm_h, bid, timeout=60.0):
    """Returns (result_dict, meta). result_dict is None if all providers failed."""
    # describe-first prompt (see the ablation table above); geometry is still
    # passed as context but never as a leading yes/no question.
    ctx = ("\nGeoreferenced context for this footprint: area %.1f m2, perimeter "
           "%.1f m, LiDAR height %s m." % (area_m2, perim_m, ndsm_h)) if area_m2 else ""
    sys_p = AUDIT_SYSTEM_PROMPT
    usr_p = AUDIT_TASK_PROMPT + ctx
    errors = []

    for prov_name, model, mt, px in CHAIN:
        prov = PROVIDERS[prov_name]()
        if not prov.is_available():
            errors.append("%s: unavailable" % prov_name)
            continue
        gate = RATE_GATES.get(prov_name)
        if gate is not None:
            gate.wait()
        b64 = chip_b64(chip, px)
        try:
            resp = prov.generate(prompt=usr_p, system_prompt=sys_p, images=[b64],
                                 model=model, timeout=timeout, max_tokens=mt,
                                 temperature=0.0)
        except Exception as e:  # never let a provider crash the batch
            errors.append("%s: %s" % (prov_name, e))
            continue

        if not (resp.is_ok() and resp.parsed_json):
            err = (resp.error or "no json")[:120]
            errors.append("%s/%s: %s" % (prov_name, model, err))
            continue

        sent = (resp.raw_payload or {}).get("images_sent", 0)
        if sent != 1:
            errors.append("%s/%s: images_sent=%s (image NOT transmitted)"
                          % (prov_name, model, sent))
            continue

        p = resp.parsed_json
        raw_reply = resp.content or ""
        # The describe-first template emits a plain `IMAGE_IS_BUILDING: yes|no`
        # line and then a JSON object. Accept either signal, and prefer the
        # explicit line, because the JSON block can be truncated at low
        # max_tokens. Without this fallback every verdict silently degraded to
        # REVIEW_NEEDED (measured 2026-10-08).
        line_flag = None
        low = raw_reply.lower()
        if "image_is_building: yes" in low:
            line_flag = True
        elif "image_is_building: no" in low:
            line_flag = False
        json_flag = p.get("is_real_building")
        if isinstance(json_flag, str):
            json_flag = json_flag.strip().lower() in ("true", "yes", "1")
        if line_flag is not None:
            is_real = line_flag
        elif json_flag is not None:
            is_real = bool(json_flag)
        else:
            is_real = None

        code = str(p.get("ancpi_code", "") or "").strip()
        if not code:
            code = "1CC" if is_real else "FALSE_POSITIVE"
        if not is_real:
            code = "FALSE_POSITIVE"
        verdict = ("APPROVED" if is_real else "REJECTED") if is_real is not None \
            else "REVIEW_NEEDED"
        meta = {
            "provider": prov_name,
            "model": resp.model_name,
            "max_tokens": mt,
            "chip_px": px,
            "duration_sec": resp.duration_sec,
            "images_sent": sent,
            "usage": resp.usage,
            "chain_errors": errors,
        }
        return {
            "is_real_building": is_real,
            "ancpi_code": code,
            "typology": str(p.get("typology", "")),
            "confidence": float(p.get("confidence", 0.0) or 0.0),
            "verdict": verdict,
            "roof_type": str(p.get("roof_type", "")),
            "eave_visible": p.get("eave_visible"),
            "has_calcan": p.get("has_calcan"),
            "vegetation_occlusion": p.get("vegetation_occlusion"),
            "reasoning": str(p.get("reasoning", ""))[:400],
            "raw_reply": raw_reply[:900],
        }, meta

    return None, {"errors": errors}


# --------------------------------------------------------------------------
def ndsm_median(src, geom):
    if src is None or geom is None or geom.is_empty:
        return None
    try:
        win = from_bounds(*geom.bounds, src.transform)
        a = src.read(1, window=win)
        if a.size == 0:
            return None
        v = a[np.isfinite(a) & (a > 0)]
        return float(np.median(v)) if v.size else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all candidates")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--force", action="store_true", help="ignore on-disk cache")
    args = ap.parse_args()

    t_start = time.time()
    gdf = gpd.read_file(GPKG, layer=CAND_LAYER)
    if args.limit:
        gdf = gdf.iloc[: args.limit]
    log("[*] Candidates: %s (%d features)" % (CAND_LAYER, len(gdf)))

    unc = gpd.read_file(GPKG, layer="UNCLASSIFIED")
    ndsm_src = rasterio.open(NDSM) if os.path.exists(NDSM) else None

    cache = {}
    if os.path.exists(TRANSCRIPT) and not args.force:
        with open(TRANSCRIPT, "r", encoding="utf-8") as fh:
            cache = {r["key"]: r for r in json.load(fh)}
        log("[*] Cache: %d entries loaded from %s" % (len(cache), TRANSCRIPT))

    rng = np.random.default_rng(20261008)

    jobs = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        key = hashlib.sha256(
            ("%s|%s" % (int(row.get("id", idx)), geom.wkt)).encode("utf-8")
        ).hexdigest()[:16]
        jobs.append((key, int(row.get("id", idx)), geom, float(geom.area), float(geom.length)))

    # ---- control jobs (built from real chips so only imagery differs) ----
    ctrl_jobs = []
    real_chip = None
    if len(jobs):
        k0, id0, g0, a0, p0 = jobs[0]
        real_chip = crop_building_chip(ortho_path=ORTHO, polygon=g0, padding_m=6.0,
                                       target_size=(512, 512), draw_contour=True)
    for cname, cimg in control_chips(real_chip, rng):
        ctrl_jobs.append((hashlib.sha256(("CTRL|%s|%d" % (cname, 0)).encode()).hexdigest()[:16],
                          "CTRL_%s" % cname, cimg, a0 if len(jobs) else 100.0,
                          p0 if len(jobs) else 40.0, cname))
    for cname, cimg in vegetation_controls(unc, n=8):
        ctrl_jobs.append((hashlib.sha256(("CTRL|%s|%d" % (cname, 1)).encode()).hexdigest()[:16],
                          "CTRL_%s" % cname, cimg, 120.0, 45.0, cname))
    # sensitivity control: the genuine chip, must be recognised
    if real_chip is not None:
        ctrl_jobs.append((hashlib.sha256(("CTRL|real_positive").encode()).hexdigest()[:16],
                          "CTRL_real_positive", real_chip, a0, p0, "real_positive"))
    log("[*] Falsification controls: %d" % len(ctrl_jobs))

    results = dict(cache)

    def work_real(job):
        key, bid, geom, area, perim = job
        if key in results and results[key].get("result"):
            return "cached", key
        chip = crop_building_chip(ortho_path=ORTHO, polygon=geom, padding_m=6.0,
                                  target_size=(512, 512), draw_contour=True)
        if chip is None:
            results[key] = {"key": key, "id": bid, "kind": "real", "result": None,
                            "meta": {"errors": ["chip crop failed"]}}
            return "chip_fail", key
        res, meta = call_vlm(chip, area, perim, ndsm_median(ndsm_src, geom), "ID_%d" % bid)
        results[key] = {"key": key, "id": bid, "kind": "real", "area_m2": round(area, 2),
                        "result": res, "meta": meta}
        return ("ok" if res else "fail"), key

    def work_ctrl(job):
        key, bid, img, area, perim, cname = job
        if key in results and results[key].get("result"):
            return "cached", key
        res, meta = call_vlm(img, area, perim, None, bid)
        results[key] = {"key": key, "id": bid, "kind": "control", "control": cname,
                        "result": res, "meta": meta}
        return ("ok" if res else "fail"), key

    # controls first: they gate whether the audit is worth trusting at all.
    # They are cached separately from the candidates so that repeated audits of
    # the 179 buildings do not re-spend the Gemini free-tier quota on controls.
    ctrl_cache_file = os.path.join(os.path.dirname(TRANSCRIPT),
                                   "vlm_audit_controls.json")
    ctrl_cache = {}
    if os.path.exists(ctrl_cache_file) and not args.force:
        try:
            with open(ctrl_cache_file, "r", encoding="utf-8") as fh:
                ctrl_cache = json.load(fh)
            # Rehydrate into results so reporting and the transcript see them.
            results.update({k: v for k, v in ctrl_cache.items() if v.get("result")})
        except Exception:
            ctrl_cache = {}

    log("\n[1/2] Running falsification controls...")
    pending_ctrl = [j for j in ctrl_jobs if j[0] not in ctrl_cache]
    if ctrl_cache:
        log("    %d/%d controls reused from cache (%s)"
            % (len(ctrl_cache), len(ctrl_jobs), ctrl_cache_file))
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        ctrl_futs = [ex.submit(work_ctrl, j) for j in pending_ctrl]
        for n, f in enumerate(cf.as_completed(ctrl_futs), 1):
            st, key = f.result()
            log("    control %2d/%2d  %-18s %s" % (n, len(ctrl_futs), key, st))

    try:
        fresh = {k: v for k, v in results.items()
                 if v.get("kind") == "control" and v.get("result")}
        with open(ctrl_cache_file, "w", encoding="utf-8") as fh:
            json.dump(fresh, fh, ensure_ascii=False, indent=1)
    except Exception as e:
        log("    [warn] could not persist control cache: %s" % e)

    log("\n[2/2] Auditing %d real candidates with real image chips..." % len(jobs))
    fails = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work_real, j) for j in jobs]
        for n, f in enumerate(cf.as_completed(futs), 1):
            st, key = f.result()
            if st in ("fail", "chip_fail"):
                fails.append(key)
            if n % 15 == 0 or n == len(futs):
                log("    %3d/%3d  (fail=%d, %.0fs)" % (n, len(futs), len(fails), time.time() - t_start))

    if ndsm_src is not None:
        ndsm_src.close()

    with open(TRANSCRIPT, "w", encoding="utf-8") as fh:
        json.dump(list(results.values()), fh, ensure_ascii=False, indent=1)
    log("[*] Transcript written: %s (%d records)" % (TRANSCRIPT, len(results)))

    # ---------------- reporting ----------------
    reals = [r for r in results.values() if r.get("kind") == "real" and r.get("result")]
    ctrls = [r for r in results.values() if r.get("kind") == "control" and r.get("result")]

    log("\n" + "=" * 78)
    log("  P3 — REAL VLM AUDIT RESULTS")
    log("=" * 78)
    log("Real candidates answered by a vision model : %d / %d" % (len(reals), len(jobs)))
    log("Total wall clock                            : %.1f s" % (time.time() - t_start))
    if reals:
        lat = [r["meta"]["duration_sec"] for r in reals]
        log("Latency ms  min/med/max                     : %.0f / %.0f / %.0f"
            % (1000 * min(lat), 1000 * np.median(lat), 1000 * max(lat)))
        log("Providers used                              : %s"
            % dict(pd_series(r["meta"]["provider"] for r in reals)))

    log("\n-- verdict distribution (real candidates) --")
    vd = {}
    for r in reals:
        vd[r["result"]["verdict"]] = vd.get(r["result"]["verdict"], 0) + 1
    for k, v in sorted(vd.items(), key=lambda x: -x[1]):
        log("    %-16s %4d  (%.1f%%)" % (k, v, 100.0 * v / max(len(reals), 1)))

    log("\n-- ANCPI code distribution (real candidates) --")
    cd = {}
    for r in reals:
        cd[r["result"]["ancpi_code"]] = cd.get(r["result"]["ancpi_code"], 0) + 1
    for k, v in sorted(cd.items(), key=lambda x: -x[1]):
        log("    %-16s %4d  (%.1f%%)" % (k, v, 100.0 * v / max(len(reals), 1)))

    log("\n-- roof types --")
    rt = {}
    for r in reals:
        rt[r["result"]["roof_type"]] = rt.get(r["result"]["roof_type"], 0) + 1
    for k, v in sorted(rt.items(), key=lambda x: -x[1])[:10]:
        log("    %-28s %4d" % (k[:28], v))

    # falsifiability gate
    log("\n-- FALSIFICATION CONTROLS --")
    neg_ok = 0
    neg_tot = 0
    for r in sorted(ctrls, key=lambda x: x["control"]):
        cn = r["control"]
        v = r["result"]["verdict"]
        approved = v == "APPROVED"
        expected_approve = (cn == "real_positive")
        good = (approved == expected_approve)
        if expected_approve:
            neg_tot += 1
            neg_ok += 1 if good else 0
        else:
            neg_tot += 1
            neg_ok += 1 if good else 0
        log("    %-18s %-14s %-8s %s" % (cn, v, "OK" if good else "WRONG",
                                         "(must approve)" if expected_approve else "(must reject)"))
    disc = neg_ok / max(neg_tot, 1)
    log("\n    discrimination = %d/%d = %.1f%%" % (neg_ok, neg_tot, 100 * disc))
    if disc >= 0.9:
        log("    VERDICT: audit is DISCRIMINATIVE -> verdict distribution is meaningful.")
    else:
        log("    VERDICT: audit is NOT DISCRIMINATIVE -> do not use these verdicts for delivery.")

    # ---------------- write GPKG layer ----------------
    if reals:
        by_id = {int(r["id"]): r for r in reals}
        sel = gdf[gdf["id"].isin(by_id.keys())].copy()
        sel["vlm_verdict"] = [by_id[int(i)]["result"]["verdict"] for i in sel["id"]]
        sel["vlm_code"] = [by_id[int(i)]["result"]["ancpi_code"] for i in sel["id"]]
        sel["vlm_conf"] = [by_id[int(i)]["result"]["confidence"] for i in sel["id"]]
        sel["vlm_typology"] = [by_id[int(i)]["result"]["typology"] for i in sel["id"]]
        sel["vlm_roof"] = [by_id[int(i)]["result"]["roof_type"] for i in sel["id"]]
        sel["vlm_eave"] = [by_id[int(i)]["result"]["eave_visible"] for i in sel["id"]]
        sel["vlm_calcan"] = [by_id[int(i)]["result"]["has_calcan"] for i in sel["id"]]
        sel["vlm_veg_occl"] = [by_id[int(i)]["result"]["vegetation_occlusion"] for i in sel["id"]]
        sel["vlm_reason"] = [by_id[int(i)]["result"]["reasoning"] for i in sel["id"]]
        sel["vlm_model"] = ["%s/%s" % (by_id[int(i)]["meta"]["provider"], by_id[int(i)]["meta"]["model"])
                            for i in sel["id"]]
        sel["vlm_latency_s"] = [by_id[int(i)]["meta"]["duration_sec"] for i in sel["id"]]
        sel["vlm_images_sent"] = [by_id[int(i)]["meta"]["images_sent"] for i in sel["id"]]
        sel.to_file(GPKG, layer=OUT_LAYER, driver="GPKG")
        log("\n[+] GPKG layer '%s' written with %d real VLM verdicts" % (OUT_LAYER, len(sel)))

        import csv as _csv
        with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
            w = _csv.writer(fh)
            w.writerow(["id", "area_m2", "verdict", "ancpi_code", "confidence", "roof_type",
                        "eave_visible", "has_calcan", "vegetation_occlusion", "model",
                        "latency_s", "images_sent", "reasoning"])
            for i in sel.index:
                r = sel.loc[i]
                w.writerow([r["id"], r["area_m2"], r["vlm_verdict"], r["vlm_code"], r["vlm_conf"],
                            r["vlm_roof"], r["vlm_eave"], r["vlm_calcan"], r["vlm_veg_occl"],
                            r["vlm_model"], r["vlm_latency_s"], r["vlm_images_sent"],
                            (r["vlm_reason"] or "")[:300]])
        log("[+] CSV written: %s" % CSV_OUT)

    if fails:
        log("\n[!] %d candidates had no successful model answer: %s" % (len(fails), fails[:12]))
    log("\n[*] DONE in %.1f s" % (time.time() - t_start))


def pd_series(it):
    d = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return d


if __name__ == "__main__":
    main()