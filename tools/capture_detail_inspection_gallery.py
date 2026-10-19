# -*- coding: utf-8 -*-
"""
Capture High-Resolution Ultra-Closeup (1:150 - 1:250) Inspection Cases
Across the entire orthophoto from live QGIS Desktop canvas.
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
        "id": "OPT_B_065",
        "name": "01_cimitir_cavou_funerar",
        "desc": "Cimitirul Manastur: cavou / mormant de 15 mp clasificat drept 'cladire'",
        "scale_margin": 2.5
    },
    {
        "id": "W003_005_M0062",
        "name": "02_parc_umbra_arbori",
        "desc": "Parcul USAMV: poligon pe peluza verde, trasat pe umbra unui copac batran",
        "scale_margin": 2.2
    },
    {
        "id": "W001_005_M0066",
        "name": "03_calea_manastur_strada_trecere",
        "desc": "Calea Manastur: poligon pe carosabil / trecere de pietoni si trotuar",
        "scale_margin": 2.5
    },
    {
        "id": "W006_004_M0009",
        "name": "04_bazine_tehnice_decantoare",
        "desc": "Zona tehnica sud-est: bazine de apa si decantoare decupate ca 'cladiri'",
        "scale_margin": 2.0
    },
    {
        "id": "OPT_B_187",
        "name": "05_nodata_limita_zbor",
        "desc": "Marginea de zbor: cladire taiata la jumatate de chenarul alb NoData",
        "scale_margin": 2.2
    },
    {
        "id": "OPT_B_144",
        "name": "06_rotatie_deviata_coama",
        "desc": "Aliniere gresita: cutie rotita cu 15 grade fata de coama reala a acoperisului",
        "scale_margin": 2.2
    },
    {
        "id": "OPT_B_046",
        "name": "07_curte_inghitita_L_shape",
        "desc": "Mutilare decros: dreptunghi forțat care baga 15 mp de iarba in casa",
        "scale_margin": 2.2
    },
    {
        "id": "OPT_B_126",
        "name": "08_biserica_absida_amputata",
        "desc": "Biserica / capela: absida de est si turnul de vest retezate complet",
        "scale_margin": 2.0
    }
]

out_dir = ROOT / "workspace" / "reviews" / "detail_inspection_cases"
out_dir.mkdir(parents=True, exist_ok=True)

for t in targets:
    cid = t["id"]
    margin = t["scale_margin"]
    print(f"[*] Zooming to {cid} ({t['name']})...")
    code = f'''
from qgis.core import QgsProject, QgsRectangle

project = QgsProject.instance()
found = False
for lyr in project.mapLayers().values():
    if lyr.type() == 0:
        for f in lyr.getFeatures():
            for fld in ["candidate_id", "id"]:
                if fld in f.fields().names() and "{cid}" in str(f.attribute(fld)):
                    bb = f.geometry().boundingBox()
                    bb.scale({margin})
                    if hasattr(iface, "mapCanvas"):
                        iface.mapCanvas().setExtent(bb)
                        iface.mapCanvas().refresh()
                        iface.mapCanvas().waitWhileRendering()
                    found = True
                    break
            if found:
                break
    if found:
        break
'''
    send_qgis_mcp("execute_code", {"code": code})
    
    # Capture canvas screenshot
    res = send_qgis_mcp("get_canvas_screenshot")
    if res.get("status") == "success":
        b64 = res["result"]["base64_data"]
        img_bytes = base64.b64decode(b64)
        out_path = out_dir / f"{t['name']}.png"
        out_path.write_bytes(img_bytes)
        print(f"[+] Saved {out_path.name} ({len(img_bytes)} bytes)")
    else:
        print(f"[-] Failed to capture {cid}")

print("[+] All detail inspection cases captured successfully!")
