import socket
import struct
import json

s = socket.socket()
s.connect(("127.0.0.1", 9876))
code = """
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
src_crs = QgsCoordinateReferenceSystem("EPSG:4326")
dst_crs = QgsCoordinateReferenceSystem("EPSG:3844")
proj = QgsProject.instance()
ops = QgsCoordinateTransform.operations(src_crs, dst_crs, proj.transformContext())
lines = [f"Ops count: {len(ops)}"]
for i, op in enumerate(ops):
    lines.append(f"[{i}] acc={op.accuracy}m avail={op.isAvailable} ballpark={op.hasBallpark} proj={op.proj}")
_result = "\\n".join(lines)
"""
req = {"type": "execute_code", "params": {"code": code}}
p = json.dumps(req).encode("utf-8")
s.sendall(struct.pack(">I", len(p)) + p)
raw = s.recv(4)
sz = struct.unpack(">I", raw)[0]
data = b""
while len(data) < sz:
    data += s.recv(min(65536, sz - len(data)))
s.close()
res = json.loads(data.decode("utf-8"))
print("Status:", res.get("status"))
if "result" in res:
    print("STDOUT:", res["result"].get("stdout"))
    print("RETURN:", res["result"].get("return_value"))
if "error" in res or "message" in res:
    print("ERROR:", res.get("error"), res.get("message"))
