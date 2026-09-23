# -*- coding: utf-8 -*-
"""
Inspect all layers in the active QGIS project and rename them to include:
- ( <main data provider> ) for direct official data
- ( <main data provider> + AI/algoritm ) for layers generated or processed by algorithms/AI
Also adds and populates the 'provider_data' attribute on 'Cladiri (+0.50m) TopoLT'.
"""
import sys
import json
import socket
import struct
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def send_qgis_mcp(command_type, params=None):
    if params is None:
        params = {}
    host = "127.0.0.1"
    port = 9876
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(20.0)
    s.connect((host, port))
    
    req = {"type": command_type, "params": params}
    payload = json.dumps(req).encode("utf-8")
    s.sendall(struct.pack(">I", len(payload)) + payload)
    
    raw_len = s.recv(4)
    if len(raw_len) != 4:
        s.close()
        raise RuntimeError("Failed to read header from QGIS MCP")
    
    resp_len = struct.unpack(">I", raw_len)[0]
    data = b""
    while len(data) < resp_len:
        chunk = s.recv(min(65536, resp_len - len(data)))
        if not chunk:
            break
        data += chunk
    s.close()
    
    return json.loads(data.decode("utf-8"))

def build_pyqgis_code():
    return '''
from qgis.core import (
    QgsProject, QgsField, QgsVectorLayer
)
from qgis.PyQt.QtCore import QVariant

project = QgsProject.instance()

# Mapping logic: base name -> new name with (data provider) or (data provider + AI/algoritm)
# We test matching by current layer name or source
renamed_count = 0

def compute_new_name(name):
    clean = name.strip()
    
    # Check if already tagged
    if "AI/algoritm" in clean or "(ANCPI)" in clean or "(ROMSILVA)" in clean:
        return clean
    
    # 1. AI / Algorithmic layers
    if "Cladiri (+0.50m) TopoLT" in clean:
        return "Cladiri (+0.50m) TopoLT (OSM + AI/algoritm StratumRO)"
    if clean == "Drumuri Nationale (DN)":
        return "Drumuri Nationale DN (ANCPI/OSM + AI/algoritm clasificare)"
    if clean == "Drumuri Judetene (DJ)":
        return "Drumuri Judetene DJ (ANCPI/OSM + AI/algoritm clasificare)"
    if clean == "Drumuri Comunale (DC)":
        return "Drumuri Comunale DC (ANCPI/OSM + AI/algoritm clasificare)"
    if clean == "Strazi Locale (ST)":
        return "Strazi Locale ST (ANCPI/OSM + AI/algoritm clasificare)"
    if "nomenclator_stradal_drumuri" in clean:
        return "RENNS Nomenclator Stradal Drumuri (ANCPI RENNS + OSM/algoritm)"
    if "numere_administrative" in clean:
        return "RENNS Numere Administrative (ANCPI RENNS + OSM/algoritm)"
    if clean == "RENNS Nomenclator Stradal":
        return "RENNS Nomenclator Stradal (ANCPI RENNS + AI/algoritm asociere)"
    if "Curti-Constructii Intravilan" in clean or clean == "Curti-Constructii Intravilan (CC)":
        return "Curti-Constructii Intravilan CC (Cadastru/OSM + AI/algoritm PUG)"
    if clean == "Fond Forestier (V_PD)":
        return "Fond Forestier V_PD (ROMSILVA/CLC + AI/algoritm PUG)"
    if "Zone Umede" in clean:
        return "Zone Umede si Ape ZHA (ANAR ROWATER + AI/algoritm PUG)"
    if "Pasuni si Fanete" in clean:
        return "Pasuni si Fanete A_P (APIA/CLC + AI/algoritm PUG)"
    if "Terenuri Arabile" in clean:
        return "Terenuri Arabile A_Ar (APIA/CLC + AI/algoritm PUG)"
    if "Banda Inundabila T100" in clean:
        return "Banda Inundabila T100 (ANAR ROWATER + AI/algoritm modelare hidraulica)"
    if "luciu_apa_zona_inundabila" in clean:
        return "Luciu Apa Zona Inundabila (ANAR ROWATER + OSM/algoritm)"
    if "hidrografie_cursuri_apa" in clean:
        return "Hidrografie Cursuri Apa (ANAR ROWATER + OSM/algoritm)"
    if "limita_uat_referinta_osm" in clean:
        return "Limita UAT Referinta (OSM + AI/algoritm)"
    if "uat_iepuresti_selectat" in clean:
        return "Limita UAT Iepuresti (ANCPI + AI/algoritm selectie)"

    # 2. Direct Official Data Providers
    if "Limita UAT ANCPI Oficiala" in clean:
        return "Limita UAT Oficiala (ANCPI)"
    if "IEP_00_limita_UAT_ANCPI_oficial" in clean:
        return "Limita UAT ANCPI Oficial (ANCPI)"
    if "ANCPI_UAT_Romania_National" in clean:
        return "ANCPI UAT Romania National (ANCPI)"
    
    if "01_RAN_National_Toata_Romania" in clean:
        return "RAN Situri Arheologice National (INP cIMeC RAN)"
    if "IEP_01_situri_arheologice_RAN" in clean:
        return "Situri Arheologice Iepuresti (INP cIMeC RAN)"
    if "RAN Situri Arheologice Protejate" in clean:
        return "Situri Arheologice Protejate (INP cIMeC RAN)"
    if clean == "ran_iepuresti":
        return "RAN Situri Iepuresti (INP cIMeC RAN)"
        
    if "Natura 2000 Situri Comunitare" in clean:
        return "Natura 2000 Situri Comunitare (EEA Natura 2000)"
    if "IEP_02_natura2000_eea" in clean:
        return "Natura 2000 Iepuresti (EEA Natura 2000)"
    if "01_natura2000_eea" in clean:
        return "Natura 2000 Situri Protected (EEA Natura 2000)"
        
    if "04_ROWATER_Bazine_Hidrografice_Romania" in clean:
        return "Bazine Hidrografice Romania (ANAR ROWATER)"
    if "04_ROWATER_Cursuri_Apa_Segmente_Romania" in clean:
        return "Cursuri Apa Segmente Romania (ANAR ROWATER)"
    if "04_ROWATER_Diguri_Romania" in clean:
        return "Diguri Protectie Romania (ANAR ROWATER)"
    if "IEP_04_rowater_bazine_hidrografice" in clean:
        return "Bazine Hidrografice Neajlov (ANAR ROWATER)"
    if "IEP_04_rowater_cursuri_apa_segmente" in clean:
        return "Cursuri Apa Neajlov (ANAR ROWATER)"
    if "IEP_04_rowater_diguri" in clean:
        return "Diguri Aparare Neajlov (ANAR ROWATER)"
    if "ROWATER Retea Hidrografica" in clean:
        return "Retea Hidrografica Neajlov (ANAR ROWATER)"
        
    if "06_APIA_Blocuri_Fizice_2025_Romania" in clean:
        return "APIA Blocuri Fizice 2025 National (APIA)"
    if "APIA Blocuri Fizice 2025 Oficial" in clean:
        return "APIA Blocuri Fizice 2025 (APIA)"
    if "IEP_06_apia_blocuri_fizice_2025" in clean:
        return "Blocuri Fizice Oficiale 2025 (APIA)"
        
    if "ROMSILVA Fond Forestier" in clean:
        return "Fond Forestier OS Ghimpati (ROMSILVA)"
        
    if "Esri Satellite" in clean:
        return "Esri Satellite (Esri Imagery)"
    if "OpenStreetMap" in clean:
        return "OpenStreetMap (OSM Contributors)"
        
    return clean

# Apply layer renaming
layers = project.mapLayers().values()
changes = []
for lyr in layers:
    old_name = lyr.name()
    new_name = compute_new_name(old_name)
    if new_name != old_name:
        lyr.setName(new_name)
        changes.append(f"{old_name} -> {new_name}")
        renamed_count += 1

# Check attribute update on Cladiri (+0.50m) TopoLT
cladiri_updated = 0
for lyr in layers:
    if "Cladiri" in lyr.name() and isinstance(lyr, QgsVectorLayer):
        field_names = [f.name() for f in lyr.fields()]
        provider_val = "OSM + AI/algoritm StratumRO"
        
        lyr.startEditing()
        if "provider_data" not in field_names:
            lyr.addAttribute(QgsField("provider_data", QVariant.String, len=60))
            lyr.updateFields()
            field_names.append("provider_data")
            
        provider_idx = lyr.fields().indexFromName("provider_data")
        for feat in lyr.getFeatures():
            feat[provider_idx] = provider_val
            lyr.updateFeature(feat)
            cladiri_updated += 1
        lyr.commitChanges()
        print(f"Updated {cladiri_updated} features in layer '{lyr.name()}' with provider_data='{provider_val}'")

print(f"Total layers renamed: {renamed_count}")
for c in changes:
    print(f"  * {c}")

if hasattr(iface, "mapCanvas"):
    iface.mapCanvas().refresh()
'''

if __name__ == "__main__":
    print(">>> Sending rename & attribute update script to QGIS via MCP...")
    code = build_pyqgis_code()
    res = send_qgis_mcp("execute_code", {"code": code})
    print("Response:", res.get("status"))
    if "result" in res:
        output = res["result"].get("output", "")
        print(output)
        if res["result"].get("error"):
            print("ERROR:", res["result"].get("error"))
    
    # Save project
    save_res = send_qgis_mcp("save_project")
    print("Save Project:", save_res.get("status"))
