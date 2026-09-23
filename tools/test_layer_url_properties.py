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

test_code = '''
import json
from qgis.core import QgsProject

project = QgsProject.instance()
layers = project.mapLayers().values()
tested = []

official_links = {
    "Limita UAT Iepuresti (oficial - ANCPI)": "https://data.gov.ro/dataset/unitati-administrativ-teritoriale",
    "APIA Blocuri Fizice 2025 (oficial - APIA)": "https://data.gov.ro/dataset/parcele-de-referinta-2025-blocuri-fizice-apia",
    "Situri Arheologice RAN (oficial - INP cIMeC)": "https://ran.cimec.ro/",
    "Natura 2000 Situri Comunitare (oficial - EEA)": "https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer",
    "Cursuri de Apa Neajlov (oficial - ANAR ROWATER)": "https://data.gov.ro/dataset/hidrografie",
    "Fond Forestier OS Ghimpati (oficial - ROMSILVA)": "https://inspectorulpadurii.ro/"
}

for lyr in layers:
    name = lyr.name()
    if name in official_links:
        url = official_links[name]
        
        # 1. Set attribution and attribution url
        lyr.setAttribution(f"Oficial: {url}")
        lyr.setAttributionUrl(url)
        
        # 2. Set layer metadata
        meta = lyr.metadata()
        meta.setIdentifier(url)
        meta.setAbstract(f"Strat oficial preluat de la autoritatea competenta: {url}")
        lyr.setMetadata(meta)
        
        # 3. Custom properties for quick access
        lyr.setCustomProperty("official_url", url)
        lyr.setCustomProperty("sursa_oficiala", "Portal Oficial de Stat")
        
        tested.append({
            "name": name,
            "url": lyr.attributionUrl(),
            "attr": lyr.attribution(),
            "meta_id": lyr.metadata().identifier()
        })

print("TEST_METADATA_RESULT:" + json.dumps(tested))
'''

if __name__ == "__main__":
    resp = send_qgis_mcp("execute_code", {"code": test_code})
    print(json.dumps(resp, indent=2))
