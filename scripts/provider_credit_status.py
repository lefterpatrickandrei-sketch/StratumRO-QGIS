"""Probe credit/key status of every configured provider WITHOUT printing secrets.

Run: venv\\Scripts\\python.exe scripts\\provider_credit_status.py
"""
import os
import sys
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

KEYS = [
    "NVIDIA_API_KEY", "OPENROUTER_API_KEY", "UNION_ALPHA_API_KEY",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SAMBANOVA_API_KEY",
    "CEREBRAS_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
]

print("=== KEY INVENTORY (masked) ===")
for k in KEYS:
    v = os.getenv(k)
    if not v:
        print("  %-22s MISSING" % k)
    else:
        print("  %-22s len=%-4d head=%s...tail=%s" % (k, len(v), v[:3], v[-4:]))

print("\n=== OPENROUTER CREDIT BALANCE ===")
for kname in ("OPENROUTER_API_KEY", "UNION_ALPHA_API_KEY"):
    k = os.getenv(kname)
    if not k:
        continue
    try:
        r = requests.get("https://openrouter.ai/api/v1/credits",
                         headers={"Authorization": "Bearer " + k}, timeout=20)
        print("  [%s] HTTP %s" % (kname, r.status_code))
        if r.status_code == 200:
            d = r.json().get("data", {})
            print("      total_credits=%s total_usage=%s remaining=%.4f"
                  % (d.get("total_credits"), d.get("total_usage"),
                     d.get("total_credits", 0) - d.get("total_usage", 0)))
    except Exception as e:
        print("  [%s] ERROR %s" % (kname, e))

print("\n=== LIVE 1-TOKEN PROBE (does the route answer at all?) ===")
PROBES = [
    ("openrouter(OPENROUTER_API_KEY)", "https://openrouter.ai/api/v1/chat/completions",
     os.getenv("OPENROUTER_API_KEY"), "openai/gpt-4o-mini"),
    ("openrouter(UNION_ALPHA_API_KEY)", "https://openrouter.ai/api/v1/chat/completions",
     os.getenv("UNION_ALPHA_API_KEY"), "openai/gpt-4o-mini"),
    ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions",
     os.getenv("NVIDIA_API_KEY"), "meta/llama-3.2-11b-vision-instruct"),
    ("openai", "https://api.openai.com/v1/chat/completions",
     os.getenv("OPENAI_API_KEY"), "gpt-4o-mini"),
    ("anthropic", "https://api.anthropic.com/v1/messages",
     os.getenv("ANTHROPIC_API_KEY"), "claude-3-5-haiku-latest"),
]
for name, url, key, model in PROBES:
    if not key:
        print("  %-32s SKIP (no key)" % name)
        continue
    try:
        if "anthropic" in url:
            r = requests.post(url, headers={
                "x-api-key": key, "anthropic-version": "2023-06-01",
                "content-type": "application/json"},
                json={"model": model, "max_tokens": 8,
                      "messages": [{"role": "user", "content": "hi"}]}, timeout=25)
        else:
            r = requests.post(url, headers={
                "Authorization": "Bearer " + key, "content-type": "application/json"},
                json={"model": model, "max_tokens": 8,
                      "messages": [{"role": "user", "content": "hi"}]}, timeout=25)
        body = r.text[:150].replace("\n", " ")
        print("  %-32s HTTP %s  %s" % (name, r.status_code, body))
    except Exception as e:
        print("  %-32s ERROR %s" % (name, e))