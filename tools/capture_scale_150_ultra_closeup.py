# -*- coding: utf-8 -*-
"""
Capture Ultra Close-Up Cadastral Frames at Strict 1:150 Scale (Window 44m x 25m)
Directly from live QGIS map canvas.
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
        "filename": "scara150_01_B046_decros_L_taiat.png",
        "title": "B046 — Scara 1:150 (Fereastra 44m x 25m): Decrosul in L taiat drept prin curte"
    },
    {
        "id": "OPT_B_144",
        "scale": 150.0,
        "filename": "scara150_02_B144_rotatie_gresita_coama.png",
        "title": "B144 — Scara 1:150: Rotatie deviată cu 12 grade fata de frontul strazii"
    },
    {
        "id": "OPT_B_126",
        "scale": 180.0,
        "filename": "scara150_03_B126_biserica_absida_amputata.png",
        "title": "B126 — Scara 1:180: Absida estica si nartexul vestic retezate din biserica"
    },
    {
        "id": "W004_003",
        "scale": 200.0,
        "filename": "scara150_04_W004_003_hala_ciopartita_trepte.png",
        "title": "W004_003 — Scara 1:200: Hala mare industriala taiata drept, calcand peste T17:C1"
    },
    {
        "id": "W001_005_M0066",
        "scale": 150.0,
        "filename": "scara150_05_Calea_Manastur_copac_pe_iarba.png",
        "title": "Calea Manastur — Scara 1:150: Cutie pe coroana copacului si iarba goala"
    },
    {
        "id": "OPT_B_065",
        "scale": 150.0,
        "filename": "scara150_06_Cimitir_cavou_pe_morminte.png",
        "title": "Cimitirul Manastur — Scara 1:150: Cripta funerara / cavou desenat ca si cladire"
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

canvas = iface.mapCanvas()
found = False
for lyr in QgsProject.instance().mapLayers().values():
    if lyr.type() == 0:
        for f in lyr.getFeatures():
            val = ""
            for fld in ["candidate_id", "id"]:
                if fld in f.fields().names():
                    val = str(f.attribute(fld))
                    break
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

print("[+] All scale 1:150 ultra-closeups captured successfully!")
