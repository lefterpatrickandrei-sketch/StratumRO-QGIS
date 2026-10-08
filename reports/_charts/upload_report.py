#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Upload the StratumRO report to file.io so it is readable on the phone
after the laptop is closed. Temporary host - file self-destructs.

Run: venv\\Scripts\\python reports\\_charts\\upload_report.py
"""
import os
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

SRC = r"C:\Users\lefpa\Downloads\QGIS-AI\reports\STRATUMRO_RAPORT_2026-10-08.html"
SIZE_MB = os.path.getsize(SRC) / 1024.0 / 1024.0

import requests  # noqa: E402

print("Sursa   :", SRC)
print("Marime  : %.2f MB" % SIZE_MB)

with open(SRC, "rb") as fh:
    resp = requests.post(
        "https://file.io",
        files={"file": (os.path.basename(SRC), fh, "text/html")},
        timeout=300,
    )

print("HTTP    :", resp.status_code)

if resp.status_code != 200:
    print("RESPUNS :", resp.text[:500])
    sys.exit(1)

payload = resp.json()
if payload.get("status") != "success":
    print("ESUITE  :", json.dumps(payload)[:500])
    sys.exit(1)

data = payload["data"]
url = data["url"]
if not url.endswith("/"):
    url = url + "/"

print()
print("=" * 66)
print("  URL DE CITIRE :", url)
print("  ID            :", data.get("id"))
print("  Expira in     :", data.get("expiry", "necunoscut"))
print("  Expira la     :", data.get("expiryTimestamp", "necunoscut"))
print("=" * 66)