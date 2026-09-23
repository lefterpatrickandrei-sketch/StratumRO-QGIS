# -*- coding: utf-8 -*-
"""
Helper script to query QGIS Desktop via QGIS MCP socket on 127.0.0.1:9876.
"""
import sys
import json
import socket
import struct
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def send_qgis_mcp(command_type, params=None):
    if params is None:
        params = {}
    host = "127.0.0.1"
    port = 9876
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15.0)
    s.connect((host, port))
    
    req = {
        "type": command_type,
        "params": params
    }
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

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "info"
    if action == "info":
        res = send_qgis_mcp("get_project_info")
        p = res.get("result", {})
        print("="*60)
        print("QGIS MCP PROJECT INFORMATION")
        print("="*60)
        print(f"Project File : {p.get('filename')}")
        print(f"Project Title: {p.get('title')}")
        print(f"Project CRS  : {p.get('crs')}")
        print(f"Total Layers : {p.get('layer_count')}")
        print("-" * 60)
        for idx, lyr in enumerate(p.get("layers", []), 1):
            name = lyr.get("name", "Unknown")
            lid = lyr.get("id", "")
            vis = lyr.get("visible", False)
            ltype = lyr.get("type", "")
            print(f"[{idx:02d}] {'[X]' if vis else '[ ]'} {name} (type={ltype})")
    elif action == "extent":
        res = send_qgis_mcp("get_canvas_extent")
        print(json.dumps(res, indent=2))
    elif action == "layers":
        res = send_qgis_mcp("get_layers", {"limit": 100})
        layers = res.get("result", {}).get("layers", [])
        print(f"Total retrieved: {len(layers)}")
        for l in layers:
            print(f" - {l.get('name')}: features={l.get('feature_count')}, visible={l.get('visible')}, geom={l.get('geometry_type')}")
    elif action == "cmd":
        cmd_type = sys.argv[2]
        cmd_params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        res = send_qgis_mcp(cmd_type, cmd_params)
        print(json.dumps(res, indent=2, ensure_ascii=False))
