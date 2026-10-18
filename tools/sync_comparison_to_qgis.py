import socket
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "workspace" / "reviews" / "comparatie_a_vs_b_20261018"
OUT_GPKG = OUT_DIR / "comparatie_a_vs_b.gpkg"
gpkg_str = str(OUT_GPKG.resolve()).replace("\\", "/")
shot_path = str((OUT_DIR / "qgis_comparatie_a_vs_b.png").resolve()).replace("\\", "/")

code = f"""
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFillSymbol,
    QgsSingleSymbolRenderer, QgsPalLayerSettings,
    QgsTextFormat, QgsVectorLayerSimpleLabeling
)
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

p = QgsProject.instance()
root = p.layerTreeRoot()

grp_name = "STRATUMRO_COMPARATIE_A_VS_B"
old_grp = root.findGroup(grp_name)
if old_grp is not None:
    for child in list(old_grp.findLayers()):
        p.removeMapLayer(child.layerId())
    root.removeChildNode(old_grp)

master = root.insertGroup(0, grp_name)
master.setItemVisibilityChecked(True)
master.setExpanded(True)

def style_vector(layer, color_hex, line_width_mm, style="solid"):
    symbol = QgsFillSymbol.createSimple({{
        "color": "0,0,0,0",
        "style": "no",
        "outline_color": color_hex,
        "outline_width": str(line_width_mm),
        "outline_style": style,
        "outline_width_unit": "MM"
    }})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))

def add_labels(layer, field_name="body_id", text_color="white", buf_color="black"):
    pal = QgsPalLayerSettings()
    pal.fieldName = field_name
    pal.isExpression = False
    text = QgsTextFormat()
    text.setColor(QColor(text_color))
    text.setSize(8.5)
    buf = text.buffer()
    buf.setEnabled(True)
    buf.setColor(QColor(buf_color))
    buf.setSize(0.8)
    text.setBuffer(buf)
    pal.setFormat(text)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)

# 1. OPTIUNEA A: LOT 5 (Cyan #00e5ff solid / Verde lime #00ff66 dash)
grp_a = master.addGroup("OPTIUNEA_A_LOT5_TINTIT (1/4 Zona)")
grp_a.setExpanded(True)

l_l5_roof = QgsVectorLayer("{gpkg_str}|layername=LOT5_OPTIUNEA_A_ROOF", "LOT5 - Acoperis Ortho90 (Cyan)", "ogr")
if l_l5_roof.isValid():
    style_vector(l_l5_roof, "#00e5ff", 0.90, "solid")
    add_labels(l_l5_roof, "body_id", "white", "#002b36")
    p.addMapLayer(l_l5_roof, False)
    grp_a.addLayer(l_l5_roof)
    print("Adaugat LOT5 Roof:", l_l5_roof.featureCount())

l_l5_sol = QgsVectorLayer("{gpkg_str}|layername=LOT5_OPTIUNEA_A_SOL", "LOT5 - Amprenta Sol ANCPI -0.40m (Verde)", "ogr")
if l_l5_sol.isValid():
    style_vector(l_l5_sol, "#00ff66", 0.65, "dash")
    p.addMapLayer(l_l5_sol, False)
    grp_a.addLayer(l_l5_sol)
    print("Adaugat LOT5 Sol:", l_l5_sol.featureCount())

# 2. OPTIUNEA B: REGIONAL FILTRAT (Orange #ff9800 solid / Verde deschis #76ff03 dash)
grp_b = master.addGroup("OPTIUNEA_B_REGIONAL_FILTRAT (2/4 Zona)")
grp_b.setExpanded(True)

l_b_roof = QgsVectorLayer("{gpkg_str}|layername=OPTIUNEA_B_ROOF_VALIDAT", "OPT_B - Cladiri Validate nDSM (Portocaliu)", "ogr")
if l_b_roof.isValid():
    style_vector(l_b_roof, "#ff9800", 0.85, "solid")
    add_labels(l_b_roof, "body_id", "#ffcc80", "black")
    p.addMapLayer(l_b_roof, False)
    grp_b.addLayer(l_b_roof)
    print("Adaugat OPT_B Roof:", l_b_roof.featureCount())

l_b_sol = QgsVectorLayer("{gpkg_str}|layername=OPTIUNEA_B_SOL_VALIDAT", "OPT_B - Amprenta Sol -0.40m (Verde)", "ogr")
if l_b_sol.isValid():
    style_vector(l_b_sol, "#76ff03", 0.60, "dash")
    p.addMapLayer(l_b_sol, False)
    grp_b.addLayer(l_b_sol)
    print("Adaugat OPT_B Sol:", l_b_sol.featureCount())

# 3. OPTIUNEA B: FALSURI POZITIVE ELIMINATE (Gri #9e9e9e, debifat implicit)
l_b_rej = QgsVectorLayer("{gpkg_str}|layername=OPTIUNEA_B_FALS_POZITIV_ELIMINAT", "OPT_B - Falsuri Pozitive Eliminate (Gri)", "ogr")
if l_b_rej.isValid():
    style_vector(l_b_rej, "#9e9e9e", 0.40, "dot")
    p.addMapLayer(l_b_rej, False)
    node_rej = master.addLayer(l_b_rej)
    node_rej.setItemVisibilityChecked(False)
    print("Adaugat OPT_B Falsuri Eliminate:", l_b_rej.featureCount())

# Update custom layer order so new layers draw on top of rasters
if root.hasCustomLayerOrder():
    order = root.customLayerOrder()
    new_top = [l_l5_roof, l_l5_sol, l_b_roof, l_b_sol, l_b_rej]
    rem = [l for l in order if l not in new_top]
    root.setCustomLayerOrder(new_top + rem)

p.write()
iface.mapCanvas().refresh()
print("[*] Sincronizare reusita: Grupul STRATUMRO_COMPARATIE_A_VS_B este activ in QGIS!")

mw = iface.mainWindow()
pix = mw.grab()
pix.save("{shot_path}", "PNG")
print("[*] Screenshot salvat la: {shot_path}")
"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(30.0)
s.connect(("127.0.0.1", 9876))
req = {"type": "execute_code", "params": {"code": code, "timeout": 30.0}}
payload = json.dumps(req).encode("utf-8")
s.sendall(struct.pack(">I", len(payload)) + payload)

raw_len = s.recv(4)
resp_len = struct.unpack(">I", raw_len)[0]
data = b""
while len(data) < resp_len:
    chunk = s.recv(min(65536, resp_len - len(data)))
    if not chunk:
        break
    data += chunk
s.close()
res = json.loads(data.decode("utf-8"))
print("Stdout:", res.get("result", {}).get("stdout", ""))
if res.get("result", {}).get("stderr"):
    print("Stderr:", res.get("result", {}).get("stderr"))
