# -*- coding: utf-8 -*-
import sys
import json
import socket
import struct

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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

code = '''
import json
from qgis.core import QgsProject

res = []
for lyr in QgsProject.instance().mapLayers().values():
    if "Cladiri" in lyr.name():
        fields = [f.name() for f in lyr.fields()]
        sample_feat = next(lyr.getFeatures(), None)
        attrs = sample_feat.attributes() if sample_feat else []
        res.append({
            "name": lyr.name(),
            "source": lyr.source(),
            "fields": fields,
            "sample": dict(zip(fields, [str(a) for a in attrs]))
        })
print("CLADIRI_INFO:" + json.dumps(res))
'''

if __name__ == "__main__":
    resp = send_qgis_mcp("execute_code", {"code": code})
    print(json.dumps(resp, indent=2))
