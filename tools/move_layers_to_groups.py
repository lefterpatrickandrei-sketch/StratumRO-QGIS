# -*- coding: utf-8 -*-
"""
Properly move the remaining 21 layers into their designated 4 groups in the QGIS Layer Tree.
"""
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

move_code = '''
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer

project = QgsProject.instance()
root = project.layerTreeRoot()

def get_or_create_group(name):
    g = root.findGroup(name)
    if not g:
        g = root.addGroup(name)
    return g

grp_oficial = get_or_create_group("01_DATE_OFICIALE_STAT")
grp_ai      = get_or_create_group("02_MODELE_ALGORITMICE_AI")
grp_osm     = get_or_create_group("03_REFERINTA_BRUTA_OSM")
grp_carto   = get_or_create_group("04_FOND_CARTOGRAFIC")

# Collect all layer tree nodes
nodes_to_move = []
for child in list(root.children()):
    if isinstance(child, QgsLayerTreeLayer):
        nodes_to_move.append(child)
    elif isinstance(child, QgsLayerTreeGroup):
        # check child layers inside other groups
        if child not in [grp_oficial, grp_ai, grp_osm, grp_carto]:
            for gc in list(child.children()):
                if isinstance(gc, QgsLayerTreeLayer):
                    nodes_to_move.append(gc)

for node in nodes_to_move:
    lyr = node.layer()
    if not lyr:
        continue
    name = lyr.name()
    target_grp = None
    
    if "(oficial" in name:
        if "Esri" in name:
            target_grp = grp_carto
        else:
            target_grp = grp_oficial
    elif "(osm+AI" in name:
        target_grp = grp_ai
    elif "(osm)" in name:
        if "OpenStreetMap" in name:
            target_grp = grp_carto
        else:
            target_grp = grp_osm
    else:
        target_grp = grp_ai
        
    parent = node.parent()
    clone = node.clone()
    target_grp.addChildNode(clone)
    if parent:
        parent.removeChildNode(node)

# Clean up empty non-standard groups
for child in list(root.children()):
    if isinstance(child, QgsLayerTreeGroup) and child not in [grp_oficial, grp_ai, grp_osm, grp_carto]:
        root.removeChildNode(child)

print("Layer tree reorganized successfully!")
'''

if __name__ == "__main__":
    res = send_qgis_mcp("execute_code", {"code": move_code})
    print("Result:", res.get("status"))
    print(res.get("result", {}).get("stdout", ""))
    
    # Save project
    send_qgis_mcp("save_project")
