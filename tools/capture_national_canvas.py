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

render_code = '''
from qgis.core import QgsProject, QgsMapSettings, QgsMapRendererParallelJob
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtCore import QSize
import os

project = QgsProject.instance()
settings = QgsMapSettings()

# Active layers for national overview
layers = [lyr for lyr in project.mapLayers().values() if lyr.name().startswith(('ANAR', 'ANCPI', 'cIMeC'))]
settings.setLayers(layers)
settings.setDestinationCrs(project.crs())

uat_lyrs = project.mapLayersByName('ANCPI - Toate cele 3.186 UAT-uri din Romania (National)')
if uat_lyrs:
    ext = uat_lyrs[0].extent()
    ext.scale(1.05)
    settings.setExtent(ext)

settings.setOutputSize(QSize(1920, 1080))
settings.setBackgroundColor(QColor(255, 255, 255))

job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()
img = job.renderedImage()
out_file = r'C:/Users/lefpa/Downloads/QGIS-AI/workspace/output/qgis_romania_national_server_canvas.png'
img.save(out_file, 'PNG')
print(f'Rendered directly to {out_file}, size: {os.path.getsize(out_file)}')
'''

if __name__ == "__main__":
    send_qgis_mcp("save_project")
    resp = send_qgis_mcp("execute_code", {"code": render_code})
    print(resp.get("result", {}).get("stdout", ""))
