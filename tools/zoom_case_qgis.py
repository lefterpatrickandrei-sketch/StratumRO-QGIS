# -*- coding: utf-8 -*-
"""
Zoom QGIS canvas to a specific candidate ID and capture a high-resolution screenshot.
"""
import base64
import json
import socket
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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

def zoom_to_candidate(candidate_id, out_png, scale_margin=2.2):
    code = f'''
from qgis.core import QgsProject, QgsRectangle

project = QgsProject.instance()
found = False
for lyr in project.mapLayers().values():
    if lyr.type() == 0:  # Vector layer
        for f in lyr.getFeatures():
            cid = ""
            for field in ["candidate_id", "id", "c_id"]:
                if field in f.fields().names():
                    cid = str(f.attribute(field))
                    break
            if not cid:
                cid = str(f.id())
            if "{candidate_id}" in cid:
                bb = f.geometry().boundingBox()
                bb.scale({scale_margin})
                if hasattr(iface, "mapCanvas"):
                    iface.mapCanvas().setExtent(bb)
                    iface.mapCanvas().refresh()
                    iface.mapCanvas().waitWhileRendering()
                found = True
                break
        if found:
            break
'''
    res = send_qgis_mcp("execute_code", {"code": code})
    print(f"Zoom execute result: {res.get('status')}")
    
    # Capture canvas screenshot
    res_snap = send_qgis_mcp("get_canvas_screenshot")
    if res_snap.get("status") == "success":
        result = res_snap.get("result", {})
        b64_data = result.get("base64_data") or result.get("data", "")
        img_bytes = base64.b64decode(b64_data)
        out_file = Path(out_png)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(img_bytes)
        print(f"[+] Saved screenshot to: {out_file} ({len(img_bytes)} bytes, {result.get('width')}x{result.get('height')})")
        return str(out_file)
    else:
        print(f"[-] Screenshot failed: {res_snap}")
        return None

if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "OPT_B_046"
    out = sys.argv[2] if len(sys.argv) > 2 else f"workspace/reviews/zoom_{cid}.png"
    zoom_to_candidate(cid, out)
