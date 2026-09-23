# -*- coding: utf-8 -*-
import sys
import json
import socket
import struct

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

dump_code = '''
from qgis.core import QgsProject
root = QgsProject.instance().layerTreeRoot()
print("TREE_DUMP:\\n" + root.dump())
'''

if __name__ == "__main__":
    resp = send_qgis_mcp("execute_code", {"code": dump_code})
    print(resp.get("result", {}).get("stdout", ""))
