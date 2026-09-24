# -*- coding: utf-8 -*-
import base64
import json
import socket
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "workspace" / "output" / "qgis_romania_national_server_canvas.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def send_qgis_mcp(command_type, params=None):
    if params is None:
        params = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(20.0)
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

zoom_code = '''
from qgis.core import QgsProject, QgsRectangle, QgsCoordinateReferenceSystem

project = QgsProject.instance()

# Ascunde grupurile locale pentru o randare nationala clara
root = project.layerTreeRoot()
grp_local = root.findGroup("02_MODELE_ALGORITMICE_AI")
if grp_local:
    grp_local.setItemVisibilityChecked(False)

uat_lyr = None
for lyr in project.mapLayers().values():
    if "3.186 UAT" in lyr.name() or "Bazine Hidrografice" in lyr.name():
        uat_lyr = lyr
        break

if uat_lyr and hasattr(iface, "mapCanvas"):
    ext = uat_lyr.extent()
    ext.scale(1.08)
    iface.mapCanvas().setExtent(ext)
    iface.mapCanvas().refresh()
'''

if __name__ == "__main__":
    send_qgis_mcp("execute_code", {"code": zoom_code})
    send_qgis_mcp("save_project")
    
    # Capture canvas
    res = send_qgis_mcp("get_canvas_screenshot")
    if res.get("status") == "success":
        b64 = res.get("result", {}).get("base64_data")
        if b64:
            with open(OUT_PATH, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"National canvas captured to: {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
