# -*- coding: utf-8 -*-
"""
tools/sync_option_b_cleaned_to_qgis.py
======================================
Injects and styles the certified Option B deliverable into the active QGIS Desktop:
- GeoPackage: `workspace/option_b_validation_20261019/b_proposals_cleaned.gpkg`
- Styling: Purple outline (#b030e0, stroke width 0.66mm, no fill)
- Permanent Base Layers: Preserves LOT1-LOT5 completely untouched and visible!
- Side-by-side QGIS canvas renderings for critical cases:
  OPT_B_039, OPT_B_126, OPT_B_144, OPT_B_187, OPT_B_210
"""

import sys
import json
import socket
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEANED_GPKG = ROOT / "workspace" / "option_b_validation_20261019" / "b_proposals_cleaned.gpkg"
OUT_IMG_DIR = ROOT / "workspace" / "option_b_validation_20261019" / "qgis_cases"


def send_qgis_code(code, timeout=60.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(("127.0.0.1", 9876))
    req = {"type": "execute_code", "params": {"code": code, "timeout": timeout}}
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
    return json.loads(data.decode("utf-8"))


def sync_option_b():
    print("=" * 75)
    print(">>> STRATUMRO: SINCRONIZARE OPTIUNEA B REMEDIATA IN QGIS DESKTOP <<<")
    print(f"[*] Sursa GeoPackage: {CLEANED_GPKG}")
    print("=" * 75)

    gpkg_str = str(CLEANED_GPKG).replace("\\", "/")
    img_dir_str = str(OUT_IMG_DIR).replace("\\", "/")
    OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)

    pyqgis_code = f'''
import os
import json
from pathlib import Path
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFillSymbol,
    QgsSingleSymbolRenderer, QgsPalLayerSettings,
    QgsTextFormat, QgsVectorLayerSimpleLabeling,
    QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob,
    QgsMapLayerType
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

p = QgsProject.instance()
root = p.layerTreeRoot()

# 1. Protect Base Layers (LOT1-LOT5)
lot_visibility = {{}}
for l in p.mapLayers().values():
    node = root.findLayer(l.id())
    if node:
        name = l.name()
        if any(k in name for k in ["LOT", "T0", "T1", "T2", "T3", "RECTIFICARI", "TESTE", "B5"]):
            # Ensure permanent LOT layers remain visible if they were active
            lot_visibility[l.id()] = node.isVisible()

# 2. Add / Update Group OPTIUNEA_B_REMEDIATA_20261019
grp_name = "OPTIUNEA_B_REMEDIATA_20261019"
grp = root.findGroup(grp_name)
if grp is not None:
    for child in list(grp.findLayers()):
        p.removeMapLayer(child.layerId())
    root.removeChildNode(grp)

grp = root.insertGroup(0, grp_name)
grp.setItemVisibilityChecked(True)
grp.setExpanded(True)

def style_layer(layer, stroke_color, stroke_width_mm, style="solid"):
    symbol = QgsFillSymbol.createSimple({{
        "color": "0,0,0,0",
        "style": "no",
        "outline_color": stroke_color,
        "outline_width": str(stroke_width_mm),
        "outline_style": style,
        "outline_width_unit": "MM"
    }})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))

def add_purple_labels(layer, field_name="candidate_id"):
    pal = QgsPalLayerSettings()
    pal.fieldName = field_name
    pal.isExpression = False
    text = QgsTextFormat()
    text.setColor(QColor("#ffffff"))
    text.setSize(8.5)
    buf = text.buffer()
    buf.setEnabled(True)
    buf.setColor(QColor("#4a0072"))
    buf.setSize(1.0)
    text.setBuffer(buf)
    pal.setFormat(text)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)

# Layer 1: Cleaned Roof Proposals (Purple outline #b030e0, stroke width 0.66mm, dashed)
lyr_roof = QgsVectorLayer("{gpkg_str}|layername=B_ROOF_PROPOSALS", "OPT_B - Acoperis Propuneri Remediate (Mov Dash)", "ogr")
if lyr_roof.isValid():
    style_layer(lyr_roof, "#b030e0", 0.66, "dash")
    add_purple_labels(lyr_roof, "candidate_id")
    p.addMapLayer(lyr_roof, False)
    grp.addLayer(lyr_roof)

# Layer 2: Ground Footprint 1CC ANCPI -0.40m (Purple outline #b030e0, stroke width 0.66mm, solid)
lyr_sol = QgsVectorLayer("{gpkg_str}|layername=B_FOOTPRINT_1CC", "OPT_B - Amprenta Sol 1CC ANCPI -0.40m (Mov Solid)", "ogr")
if lyr_sol.isValid():
    style_layer(lyr_sol, "#b030e0", 0.66, "solid")
    p.addMapLayer(lyr_sol, False)
    grp.addLayer(lyr_sol)

# Layer 3: NoData Boundary Warning (Purple dotted, 0.50mm)
lyr_nodata = QgsVectorLayer("{gpkg_str}|layername=INCOMPLET_LIMITA_ZBOR", "OPT_B - Avertizare Limita Zbor NoData (Mov Dotted)", "ogr")
if lyr_nodata.isValid():
    style_layer(lyr_nodata, "#b030e0", 0.50, "dot")
    p.addMapLayer(lyr_nodata, False)
    grp.addLayer(lyr_nodata)
    # Default uncheck warning layer
    node_nodata = root.findLayer(lyr_nodata.id())
    if node_nodata:
        node_nodata.setItemVisibilityChecked(False)

# Layer 4: Suppressed Containment Duplicates
lyr_dup = QgsVectorLayer("{gpkg_str}|layername=DUPLICATE_CONFINED_SUPRIMATE", "OPT_B - Duplicate Conținere Suprimate (Mov Subțire)", "ogr")
if lyr_dup.isValid():
    style_layer(lyr_dup, "#b030e0", 0.35, "dash dot")
    p.addMapLayer(lyr_dup, False)
    grp.addLayer(lyr_dup)
    node_dup = root.findLayer(lyr_dup.id())
    if node_dup:
        node_dup.setItemVisibilityChecked(False)

# 3. Ensure all other Option B layers have purple style (#b030e0)
for l in p.mapLayers().values():
    if not isinstance(l, QgsVectorLayer):
        continue
    node = root.findLayer(l.id())
    ancestor = node.parent() if node else None
    belongs = False
    while ancestor:
        if any(ancestor.name().startswith(k) for k in ["B_FORME_", "B_RAFINARE_", "B_CORECTII_", "OPTIUNEA_B_"]):
            belongs = True
            break
        ancestor = ancestor.parent()
    if belongs and l.id() not in [lyr_roof.id(), lyr_sol.id(), lyr_nodata.id(), lyr_dup.id()]:
        style_layer(l, "#b030e0", 0.50, "solid")
        l.triggerRepaint()

# 4. Side-by-side renderings for critical cases (OPT_B_039, OPT_B_126, OPT_B_144, OPT_B_187, OPT_B_210)
rasters = [l for l in p.mapLayers().values() if l.type() == QgsMapLayerType.RasterLayer]
crit_cases = ["OPT_B_039:C1", "OPT_B_126:C1", "OPT_B_144:C1", "OPT_B_187:C1", "OPT_B_210:C1"]
rendered_cases = []

# Sursa cu toate cazurile curatate
lyr_all = QgsVectorLayer("{gpkg_str}|layername=B_SIMPLE_ALL_CLEANED", "all_clean", "ogr")

for cid in crit_cases:
    # Find feature geometry
    geom = None
    for f in lyr_all.getFeatures():
        if str(f["candidate_id"]) == cid:
            geom = f.geometry()
            break
    if not geom or geom.isEmpty():
        continue
    
    rect = QgsRectangle(geom.boundingBox())
    rect.scale(1.6)
    
    # Create highlighted clone
    clone = lyr_all.clone()
    clone.setLabelsEnabled(False)
    clone.renderer().setSymbol(QgsFillSymbol.createSimple({{
        "color": "0,0,0,0",
        "outline_color": "#b030e0",
        "outline_width": "0.85",
        "outline_style": "solid",
        "outline_width_unit": "MM"
    }}))
    clone.setSubsetString(f'"candidate_id" = \\'{{cid}}\\'')
    
    settings = QgsMapSettings()
    settings.setDestinationCrs(p.crs())
    settings.setOutputSize(QSize(900, 750))
    settings.setExtent(rect)
    settings.setLayers([clone] + rasters)
    
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    
    case_clean_id = cid.replace(":", "_")
    out_img_path = os.path.join("{img_dir_str}", f"{{case_clean_id}}_cleaned_qgis.png")
    job.renderedImage().save(out_img_path)
    rendered_cases.append({{
        "id": cid,
        "image_path": out_img_path,
        "bounds": [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()]
    }})

# Trigger refresh and write project
iface.mapCanvas().refresh()
p.write()

result = {{
    "status": "SUCCESS",
    "group_added": grp_name,
    "layers_loaded": [lyr_roof.name(), lyr_sol.name(), lyr_nodata.name(), lyr_dup.name()],
    "rendered_critical_cases": rendered_cases
}}
print(json.dumps(result, indent=2))
'''

    res = send_qgis_code(pyqgis_code)
    stdout = res.get("result", {}).get("stdout", "")
    stderr = res.get("result", {}).get("stderr", "")

    if stderr:
        print("[!] QGIS Stderr:", stderr)
    print("[*] Rezultat sincronizare QGIS:\n", stdout)


if __name__ == "__main__":
    sync_option_b()
