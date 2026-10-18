import socket
import json
import struct
import base64
from pathlib import Path

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
from qgis.core import QgsProject
from qgis.utils import iface

p = QgsProject.instance()
root = p.layerTreeRoot()

# Asigura-te ca ordinea customizata include noile straturi la varf
if root.hasCustomLayerOrder():
    custom_order = root.customLayerOrder()
    # Pune straturile LOT4 la inceput
    top_layers = []
    for lyr in p.mapLayers().values():
        if "Acoperis Ortho90" in lyr.name() or "Amprenta Sol ANCPI" in lyr.name() or "T22 Diagnostic" in lyr.name():
            top_layers.append(lyr)
    # Filtram cele existente si le adaugam la inceput
    remaining = [l for l in custom_order if l not in top_layers]
    root.setCustomLayerOrder(top_layers + remaining)

layers = p.mapLayersByName("LOT4 - Acoperis Ortho90 (Cyan)")
if layers:
    l = layers[0]
    for feat in l.getFeatures():
        if feat["body_id"] == "T22:C1":
            box = feat.geometry().boundingBox()
            box.grow(15.0)
            iface.mapCanvas().setExtent(box)
            iface.mapCanvas().refresh()
            print("[*] Zoom efectuat pe T22:C1:", box.toString())
            break

# Capture main window
mw = iface.mainWindow()
pix = mw.grab()
out_p = r"C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/body_recovery_20261013/qgis_t22_ortho90_live.png"
pix.save(out_p, "PNG")
print("[*] Salvat screenshot complet la:", out_p)
'''

res = send_qgis_mcp("execute_code", {"code": code})
print(res.get("result", {}).get("stdout", ""))

# Copy to brain artifact
src_p = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\workspace\reviews\body_recovery_20261013\qgis_t22_ortho90_live.png")
dst_p = Path(r"C:\Users\lefpa\.gemini\antigravity\brain\80fa85ac-8b08-481d-a858-2210a8757155\qgis_t22_ortho90_live.png")
if src_p.exists():
    dst_p.write_bytes(src_p.read_bytes())
    print("[*] Copiat in brain artifact:", dst_p)

# Also copy the multi-panel plot
chart_src = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\workspace\reviews\lot4_20261017\selected_v4_orthogonal\lot4_before_after_ortho90.png")
chart_dst = Path(r"C:\Users\lefpa\.gemini\antigravity\brain\80fa85ac-8b08-481d-a858-2210a8757155\lot4_before_after_ortho90.png")
if chart_src.exists():
    chart_dst.write_bytes(chart_src.read_bytes())
    print("[*] Copiat plansa lot 4 in brain artifact:", chart_dst)
