# StratumRO Hermes provider/model live probe (read-only, no secrets in output)
# Reads API keys from the Hermes .env; prints only catalogs, latencies, correctness.
import json
import os
import time
import urllib.request
import urllib.error

ENV_PATH = r"C:\Users\lefpa\AppData\Local\hermes\.env"
OUT_PATH = r"C:\Users\lefpa\Downloads\QGIS-AI\workspace\hermes\probe_results.json"

# --- load Hermes .env keys (never printed) ---
keys = {}
with open(ENV_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip().strip('"').strip("'")

def http(method, url, headers=None, body=None, timeout=45):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for h, v in (headers or {}).items():
        req.add_header(h, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
            return {"ok": True, "status": resp.status, "latency_s": round(time.time() - t0, 3), "data": payload}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "latency_s": round(time.time() - t0, 3), "error": e.read().decode()[:300]}
    except Exception as e:
        return {"ok": False, "status": None, "latency_s": round(time.time() - t0, 3), "error": f"{type(e).__name__}: {e}"}

results = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "catalogs": {}, "probes": {}}

# --- 1. CATALOG DISCOVERY (live) ---
# OpenRouter catalog (public endpoint)
orr = http("GET", "https://openrouter.ai/api/v1/models")
if orr["ok"]:
    ids = sorted(m["id"] for m in orr["data"]["data"])
    results["catalogs"]["openrouter"] = {
        "status": orr["status"], "model_count": len(ids),
        "key_configured": bool(keys.get("OPENROUTER_API_KEY")),
        "candidate_samples": [i for i in ids if any(s in i for s in (
            "llama-3.3-70b", "deepseek/deepseek-chat", "glm", "qwen3", "claude", "gpt-5"))][:12],
    }
else:
    results["catalogs"]["openrouter"] = {"status": orr.get("status"), "error": orr.get("error")}

# NVIDIA NIM catalog (auth)
nvk = keys.get("NVIDIA_API_KEY")
nv = http("GET", "https://integrate.api.nvidia.com/v1/models", {"Authorization": f"Bearer {nvk}"} if nvk else {})
if nv["ok"]:
    ids = sorted(m["id"] for m in nv["data"]["data"])
    results["catalogs"]["nvidia_nim"] = {
        "status": nv["status"], "model_count": len(ids), "key_configured": bool(nvk),
        "candidate_samples": [i for i in ids if any(s in i for s in ("glm", "llama-3.3", "llama-3.1-8b", "nemotron", "qwen"))][:12],
    }
else:
    results["catalogs"]["nvidia_nim"] = {"status": nv.get("status"), "error": nv.get("error")}

# Anthropic catalog (auth)
ank = keys.get("ANTHROPIC_API_KEY")
an = http("GET", "https://api.anthropic.com/v1/models?limit=50", {"x-api-key": ank, "anthropic-version": "2023-06-01"} if ank else {})
if an["ok"]:
    ids = sorted(m["id"] for m in an["data"]["data"])
    results["catalogs"]["anthropic"] = {
        "status": an["status"], "model_count": len(ids), "key_configured": bool(ank),
        "candidate_samples": ids[:15],
    }
else:
    results["catalogs"]["anthropic"] = {"status": an.get("status"), "error": an.get("error")}

# --- 2. LIVE MINIMAL INFERENCE PROBES ---
MARKER = "STRATUMRO_MODEL_TEST_OK"

def probe_openrouter(model):
    return http("POST", "https://openrouter.ai/api/v1/chat/completions",
                {"Authorization": f"Bearer {keys.get('OPENROUTER_API_KEY','')}", "Content-Type": "application/json"},
                {"model": model, "messages": [{"role": "user", "content": f"Return exactly:\n\n{MARKER}"}], "max_tokens": 2000})

def probe_nvidia(model):
    return http("POST", "https://integrate.api.nvidia.com/v1/chat/completions",
                {"Authorization": f"Bearer {nvk}", "Content-Type": "application/json"},
                {"model": model, "messages": [{"role": "user", "content": f"Return exactly:\n\n{MARKER}"}], "max_tokens": 200})

def probe_anthropic(model):
    return http("POST", "https://api.anthropic.com/v1/messages",
                {"x-api-key": ank, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                {"model": model, "max_tokens": 200, "messages": [{"role": "user", "content": f"Return exactly:\n\n{MARKER}"}]})

def extract_text(resp, provider):
    try:
        if provider == "anthropic":
            return "".join(b.get("text", "") for b in resp["data"]["content"])
        return resp["data"]["choices"][0]["message"]["content"] or ""
    except Exception:
        return ""

probes = [
    ("openrouter", "meta-llama/llama-3.3-70b-instruct", probe_openrouter),
    ("nvidia_nim", "z-ai/glm-5.3", probe_nvidia),
    ("anthropic", "claude-sonnet-5", probe_anthropic),
]

for provider, model, fn in probes:
    r = fn(model)
    entry = {"provider": provider, "model": model, "ok": r["ok"], "http_status": r.get("status"), "latency_s": r["latency_s"]}
    if r["ok"]:
        text = extract_text(r, provider)
        entry["correct_marker"] = MARKER in text
        entry["response_excerpt"] = text.strip()[:120]
    else:
        entry["error"] = r.get("error", "")[:200]
    results["probes"][f"{provider}:{model}"] = entry

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# --- clean summary (no secrets) ---
print(json.dumps(results, indent=2, ensure_ascii=False))
