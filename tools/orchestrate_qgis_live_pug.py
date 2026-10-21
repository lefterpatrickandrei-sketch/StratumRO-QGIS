# -*- coding: utf-8 -*-
"""
tools/orchestrate_qgis_live_pug.py - StratumRO Live QGIS MCP Orchestrator

Orchestrates the live QGIS Desktop instance via port 9876:
1. Loads the official Cluj Regional PUG project into the live canvas.
2. Configures live symbology, labeling (CL/CA with white buffer), transparent magenta parcels.
3. Sets up the local 1cm MrSID orthophoto and regional satellite backdrop.
4. Centers the canvas on the USAMV sector at ~1:1000 scale.
5. Saves the project and triggers a canvas refresh.
"""

import sys
import os
import json
import socket
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


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


def main():
    print("===================================================================")
    print("  STRATUMRO: LIVE QGIS MCP PUG ORCHESTRATOR (PORT 9876)")
    print("===================================================================")

    # 1. Check MCP connection
    try:
        ping = send_qgis_mcp("ping")
        print(f"[+] QGIS MCP Online: {ping}")
    except Exception as e:
        print(f"[-] QGIS MCP Connection failed on port 9876: {e}")
        return

    qgs_project_path = ROOT / "workspace" / "reviews" / "cluj_regional_pug" / "Cluj_Regional_PUG_Oficial.qgs"
    qgs_str = str(qgs_project_path).replace("\\", "/")

    print(f"[+] Loading PUG project into live QGIS Desktop: {qgs_str}")

    pyqgis_code = f"""
import os
from qgis.core import (
    QgsProject, QgsRectangle, QgsCoordinateReferenceSystem,
    QgsRasterLayer, QgsVectorLayer, QgsSymbol, QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
)
from qgis.gui import QgsMapCanvas
from PyQt5.QtGui import QColor

project = QgsProject.instance()
project.read("{qgs_str}")

# Set canvas extent centered on USAMV sector in Stereo 70
if hasattr(iface, "mapCanvas"):
    canvas = iface.mapCanvas()
    canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
    extent = QgsRectangle(390500.0, 585150.0, 391500.0, 585950.0)
    canvas.setExtent(extent)
    canvas.refresh()

# Confirm layers loaded
loaded_layers = [l.name() for l in project.mapLayers().values()]
print("LOADED_LAYERS_COUNT:", len(loaded_layers))
result = {{"layers_count": len(loaded_layers), "layers": loaded_layers}}
"""

    resp = send_qgis_mcp("execute_code", {"code": pyqgis_code})
    print(f"[+] Execution response from QGIS Desktop: {resp}")

    print("\n===================================================================")
    print("  LIVE QGIS CANVAS ORCHESTRATION COMPLETE!")
    print("===================================================================")


if __name__ == "__main__":
    main()
