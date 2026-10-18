# -*- coding: utf-8 -*-
"""
StratumRO — Live QGIS Desktop Integration via QGIS MCP (127.0.0.1:9876)
======================================================================
1. Connects to running QGIS Desktop 3.40 via socket.
2. Removes any broken or duplicate nodes created by raw disk edits.
3. Injects canonical Ortho90 layers for Lot 3 and Lot 4 via official PyQGIS API:
   - ROOF_HYPOTHESES_ORTHO90 (Cyan #00e5ff)
   - FOOTPRINT_HYPOTHESES_SOL (-0.40m Green #00ff66)
   - T22_DIAGNOSTIC_LIDAR (Magenta #e91e63)
   - RAW_CANDIDATES_BEFORE (Yellow #ffeb3b, unchecked)
4. Applies professional CAD styling and body_id labels with black halo buffers.
5. Refreshes canvas, saves QGIS project, and takes a high-res screenshot.
"""
from pathlib import Path
import sys
import json
import base64
import socket
import struct

ROOT = Path(__file__).resolve().parent.parent
LOT3_GPKG = ROOT / "workspace/reviews/lot3_repairs_20261017/selected_v4_orthogonal/lot3_orthogonal.gpkg"
LOT4_GPKG = ROOT / "workspace/reviews/lot4_20261017/selected_v4_orthogonal/lot4_orthogonal.gpkg"
SCREENSHOT_PATH = ROOT / "workspace/reviews/body_recovery_20261013/live_qgis_rectified_canvas.png"


def send_qgis_mcp(command_type, params=None):
    if params is None:
        params = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(30.0)
    s.connect(("127.0.0.1", 9876))
    
    req = {"type": command_type, "params": params}
    payload = json.dumps(req).encode("utf-8")
    s.sendall(struct.pack(">I", len(payload)) + payload)
    
    raw_len = s.recv(4)
    if len(raw_len) != 4:
        s.close()
        raise RuntimeError("Failed to read header from QGIS MCP")
    
    resp_len = struct.unpack(">I", raw_len)[0]
    data = b""
    while len(data) < resp_len:
        chunk = s.recv(min(65536, resp_len - len(data)))
        if not chunk:
            break
        data += chunk
    s.close()
    return json.loads(data.decode("utf-8"))


def build_pyqgis_code():
    l3_str = str(LOT3_GPKG).replace("\\", "/")
    l4_str = str(LOT4_GPKG).replace("\\", "/")

    return f'''
import sys
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFillSymbol,
    QgsSingleSymbolRenderer, QgsPalLayerSettings,
    QgsTextFormat, QgsVectorLayerSimpleLabeling
)
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

p = QgsProject.instance()
root = p.layerTreeRoot()

print("[*] Conectat la proiectul:", p.title())

# 1. Curatare noduri vechi sau rupte
groups_to_clean = [
    "LOT3_ORTHO90_20261018_PENDING_REVIEW",
    "LOT4_ORTHO90_20261018_PENDING_REVIEW",
    "STRATUMRO_RECTIFICARI_CANONICE_ORTHO90"
]

for gname in groups_to_clean:
    grp = root.findGroup(gname)
    if grp is not None:
        for child in list(grp.findLayers()):
            p.removeMapLayer(child.layerId())
        root.removeChildNode(grp)
        print(f"[*] Sters grupul vechi: {{gname}}")

# 2. Creare grup master
master_grp = root.insertGroup(0, "STRATUMRO_RECTIFICARI_CANONICE_ORTHO90")
master_grp.setItemVisibilityChecked(True)
master_grp.setExpanded(True)

def style_vector_layer(layer, color_hex, line_width_mm, style="solid"):
    symbol = QgsFillSymbol.createSimple({{
        "color": "0,0,0,0",
        "style": "no",
        "outline_color": color_hex,
        "outline_width": str(line_width_mm),
        "outline_style": style,
        "outline_width_unit": "MM"
    }})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))

def add_layer_labels(layer, field_name="body_id"):
    pal = QgsPalLayerSettings()
    pal.fieldName = field_name
    pal.isExpression = False
    
    text = QgsTextFormat()
    text.setColor(QColor("white"))
    text.setSize(9)
    buf = text.buffer()
    buf.setEnabled(True)
    buf.setColor(QColor("black"))
    buf.setSize(0.8)
    text.setBuffer(buf)
    
    pal.setFormat(text)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)

# 3. Integrare Lot 4
grp_l4 = master_grp.addGroup("LOT4_RECTIFICAT_20261018")
grp_l4.setExpanded(True)

# L4 Roof
l4_roof = QgsVectorLayer("{l4_str}|layername=ROOF_HYPOTHESES_ORTHO90", "LOT4 - Acoperis Ortho90 (Cyan)", "ogr")
if l4_roof.isValid():
    style_vector_layer(l4_roof, "#00e5ff", 0.60, "solid")
    add_layer_labels(l4_roof, "body_id")
    p.addMapLayer(l4_roof, False)
    grp_l4.addLayer(l4_roof)
    print(f"[*] Adaugat LOT4 Acoperis Ortho90 ({{l4_roof.featureCount()}} corpuri)")

# L4 Footprint Sol (-0.40m)
l4_sol = QgsVectorLayer("{l4_str}|layername=FOOTPRINT_HYPOTHESES_SOL", "LOT4 - Amprenta Sol ANCPI -0.40m (Verde)", "ogr")
if l4_sol.isValid():
    style_vector_layer(l4_sol, "#00ff66", 0.45, "dash")
    p.addMapLayer(l4_sol, False)
    grp_l4.addLayer(l4_sol)
    print(f"[*] Adaugat LOT4 Amprenta Sol ANCPI ({{l4_sol.featureCount()}} corpuri)")

# L4 T22 Diagnostic LiDAR
l4_t22 = QgsVectorLayer("{l4_str}|layername=T22_DIAGNOSTIC_LIDAR", "LOT4 - T22 Diagnostic LiDAR nDSM (Magenta)", "ogr")
if l4_t22.isValid():
    style_vector_layer(l4_t22, "#e91e63", 0.70, "solid")
    add_layer_labels(l4_t22, "body_id")
    p.addMapLayer(l4_t22, False)
    node_t22 = grp_l4.addLayer(l4_t22)
    node_t22.setItemVisibilityChecked(True)
    print("[*] Adaugat LOT4 T22 Diagnostic LiDAR")

# L4 Raw Before (Unchecked)
l4_raw = QgsVectorLayer("{l4_str}|layername=RAW_CANDIDATES_BEFORE", "LOT4 - Masca initiala inainte de regularizare (Galben)", "ogr")
if l4_raw.isValid():
    style_vector_layer(l4_raw, "#ffeb3b", 0.40, "dot")
    p.addMapLayer(l4_raw, False)
    node_raw4 = grp_l4.addLayer(l4_raw)
    node_raw4.setItemVisibilityChecked(False)

# 4. Integrare Lot 3
grp_l3 = master_grp.addGroup("LOT3_RECTIFICAT_20261018")
grp_l3.setExpanded(True)

# L3 Roof
l3_roof = QgsVectorLayer("{l3_str}|layername=ROOF_HYPOTHESES_ORTHO90", "LOT3 - Acoperis Ortho90 (Cyan)", "ogr")
if l3_roof.isValid():
    style_vector_layer(l3_roof, "#00e5ff", 0.60, "solid")
    add_layer_labels(l3_roof, "body_id")
    p.addMapLayer(l3_roof, False)
    grp_l3.addLayer(l3_roof)
    print(f"[*] Adaugat LOT3 Acoperis Ortho90 ({{l3_roof.featureCount()}} corpuri)")

# L3 Footprint Sol (-0.40m)
l3_sol = QgsVectorLayer("{l3_str}|layername=FOOTPRINT_HYPOTHESES_SOL", "LOT3 - Amprenta Sol ANCPI -0.40m (Verde)", "ogr")
if l3_sol.isValid():
    style_vector_layer(l3_sol, "#00ff66", 0.45, "dash")
    p.addMapLayer(l3_sol, False)
    grp_l3.addLayer(l3_sol)
    print(f"[*] Adaugat LOT3 Amprenta Sol ANCPI ({{l3_sol.featureCount()}} corpuri)")

# L3 Raw Before (Unchecked)
l3_raw = QgsVectorLayer("{l3_str}|layername=RAW_CANDIDATES_BEFORE", "LOT3 - Masca initiala inainte de regularizare (Galben)", "ogr")
if l3_raw.isValid():
    style_vector_layer(l3_raw, "#ffeb3b", 0.40, "dot")
    p.addMapLayer(l3_raw, False)
    node_raw3 = grp_l3.addLayer(l3_raw)
    node_raw3.setItemVisibilityChecked(False)

# 5. Salvare proiect si refresh canvas
p.write()
iface.mapCanvas().refresh()
print("[*] Proiect QGIS salvat cu succes via PyQGIS!")
'''


def main():
    print("=" * 70)
    print(">>> STRATUMRO: SINCRONIZARE NATIVA LIVE IN QGIS DESKTOP (MCP) <<<")
    print("=" * 70)

    # 1. Test MCP Socket
    print("[1] Conectare la instanta vie QGIS pe 127.0.0.1:9876...")
    proj_info = send_qgis_mcp("get_project_info")
    if proj_info.get("status") != "success":
        print("[!] Eroare citire proiect:", proj_info)
        return
    p = proj_info.get("result", {})
    print(f"[*] Proiect activ: {p.get('title')} ({p.get('filename')})")
    print(f"[*] Straturi active: {p.get('layer_count')}")

    # 2. Executie PyQGIS nativ
    print("\n[2] Executie injectare straturi canonice via PyQGIS...")
    code = build_pyqgis_code()
    exec_res = send_qgis_mcp("execute_code", {"code": code, "timeout": 30.0})
    if exec_res.get("status") == "success":
        res_data = exec_res.get("result", {})
        print("--- Output QGIS Desktop ---")
        print(res_data.get("stdout", ""))
        if res_data.get("stderr"):
            print("--- Stderr QGIS Desktop ---")
            print(res_data.get("stderr"))
    else:
        print("[!] Eroare executie cod in QGIS MCP:", exec_res)
        return

    # 3. Preluare Screenshot Canvas
    print("[3] Captura ecran canvas QGIS curent...")
    shot_res = send_qgis_mcp("get_canvas_screenshot")
    if shot_res.get("status") == "success":
        b64 = shot_res.get("result", {}).get("base64_data")
        if b64:
            with open(SCREENSHOT_PATH, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"[*] Screenshot salvat la: {SCREENSHOT_PATH} ({SCREENSHOT_PATH.stat().st_size} bytes)")
            # Copy to artifact folder for user presentation
            art_shot = Path(r"C:\Users\lefpa\.gemini\antigravity\brain\80fa85ac-8b08-481d-a858-2210a8757155\live_qgis_rectified_canvas.png")
            art_shot.write_bytes(SCREENSHOT_PATH.read_bytes())
            print(f"[*] Copiat in directorul de artefacte: {art_shot}")

    print("\n" + "=" * 70)
    print(">>> SINCRONIZARE NATIVA QGIS FINALIZATA CU SUCCES! <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
