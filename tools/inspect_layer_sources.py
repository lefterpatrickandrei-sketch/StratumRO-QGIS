import sys
sys.path.insert(0, ".")
from tools.test_layer_url_properties import send_qgis_mcp

code = '''
import json
from qgis.core import QgsProject

p = QgsProject.instance()
info = {}
for l in p.mapLayers().values():
    info[l.name()] = {
        "source": l.source(),
        "provider": l.providerType(),
        "count": l.featureCount(),
        "crs": l.crs().authid(),
        "attr_url": l.attributionUrl(),
        "attr": l.attribution(),
        "meta_id": l.metadata().identifier()
    }
print("ALL_LAYERS_INFO:" + json.dumps(info))
'''

if __name__ == "__main__":
    resp = send_qgis_mcp("execute_code", {"code": code})
    stdout = resp.get("result", {}).get("stdout", "")
    for line in stdout.splitlines():
        if line.startswith("ALL_LAYERS_INFO:"):
            data = json.loads(line[len("ALL_LAYERS_INFO:"):])
            print(json.dumps(data, indent=2))
