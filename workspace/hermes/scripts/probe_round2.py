# StratumRO round-2 probes: NVIDIA NIM fast models + OpenAI Codex Responses + retry glm
import json, time, urllib.request, urllib.error

ENV_PATH = r"C:\Users\lefpa\AppData\Local\hermes\.env"
keys = {}
with open(ENV_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip().strip('"').strip("'")

MARKER = "STRATUMRO_MODEL_TEST_OK"

def http(method, url, headers=None, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for h, v in (headers or {}).items():
        req.add_header(h, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status, "latency_s": round(time.time() - t0, 3),
                    "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "latency_s": round(time.time() - t0, 3),
                "error": e.read().decode()[:250]}
    except Exception as e:
        return {"ok": False, "status": None, "latency_s": round(time.time() - t0, 3),
                "error": f"{type(e).__name__}: {e}"}

nvk = keys.get("NVIDIA_API_KEY", "")
out = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "probes": {}}

def probe_nvidia(model, timeout=90):
    return http("POST", "https://integrate.api.nvidia.com/v1/chat/completions",
                {"Authorization": f"Bearer {nvk}", "Content-Type": "application/json"},
                {"model": model, "messages": [{"role": "user", "content": f"Return exactly:\n\n{MARKER}"}],
                 "max_tokens": 50}, timeout=timeout)

# NVIDIA candidates from live catalog: glm-5.3 (retry longer), nemotron-3.5-lightning (fast), llama-3.3-70b (EOL?)
for model, to in [
    ("z-ai/glm-5.3", 120),
    ("nvidia/nemotron-3.5-lightning-30b-a3b", 60),
    ("meta/llama-3.3-70b-instruct", 60),
]:
    r = probe_nvidia(model, to)
    e = {"ok": r["ok"], "http_status": r.get("status"), "latency_s": r["latency_s"]}
    if r["ok"]:
        try:
            text = r["data"]["choices"][0]["message"]["content"] or ""
            e["correct_marker"] = MARKER in text
            e["response_excerpt"] = text.strip()[:100]
        except Exception as ex:
            e["parse_error"] = str(ex)
    else:
        e["error"] = r.get("error", "")[:200]
    out["probes"][f"nvidia_nim:{model}"] = e

# OpenAI Codex OAuth - check auth.json token validity via ChatGPT backend (Responses API)
auth_path = r"C:\Users\lefpa\AppData\Local\hermes\auth.json"
codex = {"checked": False}
try:
    with open(auth_path, encoding="utf-8") as f:
        auth = json.load(f)
    entry = auth.get("openai-codex", auth.get("openai_codex", {}))
    codex["auth_entry_exists"] = bool(entry)
    codex["providers_in_auth"] = list(auth.keys())[:10]
except Exception as ex:
    codex["error"] = str(ex)
out["codex_auth"] = codex

with open(r"C:\Users\lefpa\Downloads\QGIS-AI\workspace\hermes\probe_results_round2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
