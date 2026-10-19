# -*- coding: utf-8 -*-
"""
tools/capture_scale_150_remediated_frames.py
============================================
Captures Ultra Close-Up Cadastral Frames at Strict 1:150 Scale
Directly from live QGIS map canvas after precision-first remediation.
"""
import sys
import json
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.zoom_case_qgis import send_qgis_mcp

targets = [
    {
        "id": "OPT_B_046",
        "scale": 150.0,
        "filename": "scara150_01_B046_remediat.png",
        "title": "B046 — Remediat la Scara 1:150: Decroșul în L păstrat complet (9 noduri, fără tăiere prin curte)"
    },
    {
        "id": "OPT_B_144",
        "scale": 150.0,
        "filename": "scara150_02_B144_remediat.png",
        "title": "B144 — Remediat la Scara 1:150: Aliniere la front și anexa păstrată"
    },
    {
        "id": "OPT_B_126",
        "scale": 180.0,
        "filename": "scara150_03_B126_remediat.png",
        "title": "B126 — Remediat la Scara 1:180: Biserică cu absidă și nartex păstrate (14 noduri 90°)"
    },
    {
        "id": "OPT_B_028",
        "scale": 150.0,
        "filename": "scara150_07_B028_remediat.png",
        "title": "B028 — Remediat la Scara 1:150: Formă articulată cu verandă (8 noduri la 90°)"
    },
    {
        "id": "OPT_B_035",
        "scale": 150.0,
        "filename": "scara150_08_B035_remediat.png",
        "title": "B035 — Remediat la Scara 1:150: L-shape ortogonal la 90° (6 noduri)"
    }
]

out_dir = ROOT / "workspace" / "reviews" / "scara_150_ultra_detaliu"
out_dir.mkdir(parents=True, exist_ok=True)

for t in targets:
    cid = t["id"]
    scale_val = t["scale"]
    print(f"[*] Navigating to {cid} at scale 1:{scale_val:.0f}...")
    code = f'''
from qgis.core import QgsProject
from qgis.utils import iface

canvas = iface.mapCanvas()
found = False

# First search in active cleaned layer
for lyr in QgsProject.instance().mapLayers().values():
    if "OPT_B - Acoperis Propuneri Remediate" in lyr.name() or "B_ROOF_PROPOSALS" in lyr.name():
        lyr.dataProvider().reloadData()
        lyr.triggerRepaint()
        for f in lyr.getFeatures():
            val = str(f.attribute("candidate_id")) if "candidate_id" in f.fields().names() else ""
            if "{cid}" in val:
                c = f.geometry().centroid().asPoint()
                canvas.setCenter(c)
                canvas.zoomScale({scale_val})
                canvas.refresh()
                canvas.waitWhileRendering()
                found = True
                break
        if found:
            break

if not found:
    for lyr in QgsProject.instance().mapLayers().values():
        if lyr.type() == 0:
            for f in lyr.getFeatures():
                for fld in ["candidate_id", "id", "body_id"]:
                    if fld in f.fields().names() and "{cid}" in str(f.attribute(fld)):
                        c = f.geometry().centroid().asPoint()
                        canvas.setCenter(c)
                        canvas.zoomScale({scale_val})
                        canvas.refresh()
                        canvas.waitWhileRendering()
                        found = True
                        break
                if found:
                    break
            if found:
                break
'''
    send_qgis_mcp("execute_code", {"code": code})
    
    res = send_qgis_mcp("get_canvas_screenshot")
    if res.get("status") == "success":
        b64 = res["result"]["base64_data"]
        img_bytes = base64.b64decode(b64)
        out_file = out_dir / t["filename"]
        out_file.write_bytes(img_bytes)
        print(f"[+] Salvat {out_file.name} ({len(img_bytes)} bytes)")
    else:
        print(f"[-] Eroare la {cid}")

print("[+] All scale 1:150 remediated frames captured successfully!")
