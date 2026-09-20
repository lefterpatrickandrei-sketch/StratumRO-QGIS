# -*- coding: utf-8 -*-
"""
Capture Live QGIS Canvas Screenshot via QGIS MCP socket.
Saves rendered visual evidence directly to workspace/output/qgis_phase4_live_canvas.png.
"""

import base64
import json
import socket
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "workspace" / "output" / "qgis_phase4_live_canvas.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def capture_qgis_canvas():
    host = "127.0.0.1"
    port = 9876
    print(f"Connecting to QGIS MCP on {host}:{port}...")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10.0)
    s.connect((host, port))

    req = {
        "type": "get_canvas_screenshot",
        "params": {}
    }
    payload = json.dumps(req).encode("utf-8")
    s.sendall(struct.pack(">I", len(payload)) + payload)

    raw_len = s.recv(4)
    if len(raw_len) != 4:
        print("Failed to read header from QGIS MCP.")
        s.close()
        return False

    resp_len = struct.unpack(">I", raw_len)[0]
    data = b""
    while len(data) < resp_len:
        chunk = s.recv(min(65536, resp_len - len(data)))
        if not chunk:
            break
        data += chunk
    s.close()

    resp = json.loads(data.decode("utf-8"))
    if resp.get("status") == "success":
        # Check if saved to disk or decode base64
        if not OUT_PATH.exists() or OUT_PATH.stat().st_size == 0:
            b64 = resp.get("result", {}).get("base64_data")
            if b64:
                with open(OUT_PATH, "wb") as f:
                    f.write(base64.b64decode(b64))
        print(f"Successfully captured live QGIS canvas to: {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
        return True
    else:
        print(f"Error from QGIS MCP: {resp.get('message')}")
        return False


if __name__ == "__main__":
    capture_qgis_canvas()
