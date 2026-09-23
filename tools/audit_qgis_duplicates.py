# -*- coding: utf-8 -*-
"""
Auditing script: Inspects all layers in the QGIS project via MCP socket,
analyzing duplicates, source URIs, attribute schemas, and current naming.
"""
import sys
import json
import socket
import struct
from collections import defaultdict

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

audit_code = '''
import json
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer

project = QgsProject.instance()
root = project.layerTreeRoot()

def get_layer_group(node, current_path=""):
    result = {}
    for child in node.children():
        if hasattr(child, "name") and hasattr(child, "children"): # Group
            sub_path = f"{current_path}/{child.name()}" if current_path else child.name()
            result.update(get_layer_group(child, sub_path))
        elif hasattr(child, "layerId"): # Layer
            result[child.layerId()] = current_path
    return result

layer_groups = get_layer_group(root)

layers_data = []
for lyr in project.mapLayers().values():
    lid = lyr.id()
    name = lyr.name()
    source = lyr.source()
    group = layer_groups.get(lid, "ROOT")
    is_vector = isinstance(lyr, QgsVectorLayer)
    
    feat_count = lyr.featureCount() if is_vector else None
    geom_type = lyr.geometryType() if is_vector else None
    
    fields = [f.name() for f in lyr.fields()] if is_vector else []
    sample_attrs = {}
    if is_vector and feat_count and feat_count > 0:
        feat = next(lyr.getFeatures(), None)
        if feat:
            sample_attrs = {f: str(feat[f]) for f in fields[:10]}
            
    layers_data.append({
        "id": lid,
        "name": name,
        "group": group,
        "source": source,
        "feature_count": feat_count,
        "geom_type": geom_type,
        "fields": fields,
        "sample": sample_attrs
    })

print("AUDIT_RESULT:" + json.dumps(layers_data))
'''

if __name__ == "__main__":
    resp = send_qgis_mcp("execute_code", {"code": audit_code})
    output = resp.get("result", {}).get("stdout", "")
    if "AUDIT_RESULT:" in output:
        raw_json = output.split("AUDIT_RESULT:")[1].strip()
        data = json.loads(raw_json)
        print(f"Total layers inspected: {len(data)}")
        
        # Analyze duplicates by source or name
        by_source = defaultdict(list)
        by_name = defaultdict(list)
        for l in data:
            by_source[l["source"]].append(l)
            by_name[l["name"]].append(l)
            
        print("\n--- DUPLICATE BY IDENTICAL SOURCE ---")
        for src, group in by_source.items():
            if len(group) > 1:
                print(f"\nSource: {src}")
                for item in group:
                    print(f"  - [{item['group']}] '{item['name']}' (count={item['feature_count']}, id={item['id']})")
                    
        print("\n--- DUPLICATE BY SIMILAR / IDENTICAL NAME ---")
        for name, group in by_name.items():
            if len(group) > 1:
                print(f"\nName: '{name}' (x{len(group)})")
                for item in group:
                    print(f"  - [{item['group']}] Source: {item['source']} (count={item['feature_count']})")
                    
        # Output entire audit data to a scratch file
        with open(r"tools\layer_audit_report.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("\nWrote full audit to tools/layer_audit_report.json")
    else:
        print("Raw response:", resp)
