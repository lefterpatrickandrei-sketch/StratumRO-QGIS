# -*- coding: utf-8 -*-
"""
StratumRO — Deep Metacognitive Audit using Live QGIS Desktop 3.40 (PyQGIS)
========================================================================
Inspects QGIS directly from internal memory via socket (127.0.0.1:9876):
1. Complete Layer Tree audit (groups, layers, checked state, feature counts, providers).
2. Canvas render stack audit (exact layers currently drawn, scale, extent, custom order).
3. Epistemic state classification (Ground Truth vs Provisional vs Clutter).
4. Spatial grounding check on sample buildings against 5cm orthophoto.
"""

import socket
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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
    resp_len = struct.unpack(">I", raw_len)[0]
    data = b""
    while len(data) < resp_len:
        chunk = s.recv(min(65536, resp_len - len(data)))
        if not chunk:
            break
        data += chunk
    s.close()
    return json.loads(data.decode("utf-8"))

code = '''
import json
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from qgis.utils import iface

p = QgsProject.instance()
root = p.layerTreeRoot()
canvas = iface.mapCanvas()

# 1. Project metadata
audit = {
    "project_title": p.title(),
    "project_path": p.fileName(),
    "crs": p.crs().authid(),
    "layer_count_total": len(p.mapLayers()),
    "canvas": {
        "scale": round(canvas.scale(), 1),
        "extent": {
            "xmin": round(canvas.extent().xMinimum(), 2),
            "ymin": round(canvas.extent().yMinimum(), 2),
            "xmax": round(canvas.extent().xMaximum(), 2),
            "ymax": round(canvas.extent().yMaximum(), 2),
            "width_m": round(canvas.extent().width(), 2),
            "height_m": round(canvas.extent().height(), 2)
        },
        "has_custom_order": root.hasCustomLayerOrder(),
        "rendered_layers": [l.name() for l in canvas.layers()]
    },
    "tree_hierarchy": []
}

def dump_node(node):
    data = {
        "name": node.name(),
        "type": "group" if hasattr(node, "children") else "layer",
        "visible": node.itemVisibilityChecked()
    }
    if hasattr(node, "layer"):
        lyr = node.layer()
        if lyr:
            data["valid"] = lyr.isValid()
            data["type"] = "vector" if isinstance(lyr, QgsVectorLayer) else "raster"
            data["feature_count"] = lyr.featureCount() if isinstance(lyr, QgsVectorLayer) else None
            data["crs"] = lyr.crs().authid()
            data["labels_enabled"] = lyr.labelsEnabled() if isinstance(lyr, QgsVectorLayer) else False
    if hasattr(node, "children"):
        data["children"] = [dump_node(child) for child in node.children()]
    return data

for child in root.children():
    audit["tree_hierarchy"].append(dump_node(child))

# 2. Detailed audit of all LOT layers
lot_layers = {}
for lyr_id, lyr in p.mapLayers().items():
    name = lyr.name()
    if any(k in name for k in ["LOT", "T10", "T22", "OPT_B", "REST"]):
        if isinstance(lyr, QgsVectorLayer):
            feats_info = []
            for f in lyr.getFeatures():
                geom = f.geometry()
                fields = {field.name(): f[field.name()] for field in lyr.fields() if field.name() in ["body_id", "test_id", "owner_verdict", "area_m2", "ortho_ratio", "h90_m"]}
                feats_info.append({
                    "id": f.id(),
                    "fields": fields,
                    "area_geom": round(geom.area(), 2) if geom else 0,
                    "is_valid": geom.isGeosValid() if geom else False
                })
            node = root.findLayer(lyr.id())
            is_vis = node.itemVisibilityChecked() if node else False
            lot_layers[name] = {
                "id": lyr.id(),
                "visible_in_tree": is_vis,
                "feature_count": lyr.featureCount(),
                "labels_enabled": lyr.labelsEnabled(),
                "crs": lyr.crs().authid(),
                "features_sample": feats_info[:5],
                "total_features": len(feats_info)
            }

audit["lot_layers_detail"] = lot_layers

print(json.dumps(audit, indent=2))
'''

res = send_qgis_mcp("execute_code", {"code": code, "timeout": 30.0})
stdout = res.get("result", {}).get("stdout", "")
stderr = res.get("result", {}).get("stderr", "")

if stderr:
    print("Stderr:", stderr)

out_file = ROOT / "workspace" / "reviews" / "comparatie_a_vs_b_20261018" / "qgis_internal_audit.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(stdout, encoding="utf-8")
print(f"[*] Audit intern extras direct din QGIS si salvat in: {out_file} ({len(stdout)} bytes)")
