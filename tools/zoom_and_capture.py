# -*- coding: utf-8 -*-
"""
Zoom canvas to UAT Iepuresti extent with 5% margin and capture a crisp screenshot.
"""
import base64
import json
import socket
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "workspace" / "output" / "qgis_iepuresti_official_with_providers.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def send_qgis_mcp(command_type, params=None):
    if params is None:
        params = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15.0)
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
from qgis.core import QgsProject, QgsRectangle

project = QgsProject.instance()
uat_lyr = None
for lyr in project.mapLayers().values():
    if "Limita UAT Oficiala" in lyr.name() or "IEP_00_limita_UAT_ANCPI_oficial" in lyr.name():
        uat_lyr = lyr
        break

if uat_lyr:
    ext = uat_lyr.extent()
    ext.scale(1.08)
    if hasattr(iface, "mapCanvas"):
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
            print(f"Canvas captured to: {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
