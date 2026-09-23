# -*- coding: utf-8 -*-
"""
STRATUMRO — EXECUTE PLAN:
1. Re-categorize all layers into the 3 strict criteria:
   - 'oficial'
   - 'osm'
   - 'osm+AI'
   (MANDATORY: NO 'oficial+ai')
2. Remove all 22 duplicate / redundant / empty memory layers and national shapefiles.
3. Reorganize layer tree into the 4 clean groups:
   - 01_DATE_OFICIALE_STAT
   - 02_MODELE_ALGORITMICE_AI
   - 03_REFERINTA_BRUTA_OSM
   - 04_FOND_CARTOGRAFIC
4. Update attribute tables to maintain complete provenance.
5. Zoom canvas to UAT extent, refresh, and save project.
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
    s.settimeout(30.0)
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

def build_pyqgis_execution_code():
    return '''
import json
from qgis.core import (
    QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer,
    QgsVectorLayer, QgsField
)
from qgis.PyQt.QtCore import QVariant

project = QgsProject.instance()
root = project.layerTreeRoot()

print(">>> [1/5] Identificare straturi de eliminat (duplicate, goale, nationale)...")

# Layers to explicitly remove (duplicates, 0 features memory layers, or national heavy layers)
layers_to_remove = []
all_layers = list(project.mapLayers().values())

for lyr in all_layers:
    name = lyr.name()
    src = lyr.source()
    is_vec = isinstance(lyr, QgsVectorLayer)
    cnt = lyr.featureCount() if is_vec else -1
    
    # 1. Empty memory layers
    if "memory?" in src and cnt == 0:
        layers_to_remove.append(lyr)
        continue
        
    # 2. National heavy layers (1.5M APIA, 3186 ANCPI, national rivers/dikes/basins)
    if "06_APIA_Blocuri_Fizice_2025_Romania" in src or "APIA Blocuri Fizice 2025 National" in name:
        layers_to_remove.append(lyr)
        continue
    if "ANCPI_UAT_Romania_National" in src or "ANCPI UAT Romania National" in name:
        layers_to_remove.append(lyr)
        continue
    if "CursuriApaRauriSegmente.shp" in src and cnt > 1000:
        layers_to_remove.append(lyr)
        continue
    if "Diguri.shp" in src or "Diguri Protectie Romania" in name:
        layers_to_remove.append(lyr)
        continue
    if "BazineHidrografice.shp" in src and cnt > 1:
        layers_to_remove.append(lyr)
        continue
    if "RAN_Romania_National_Complet" in src:
        layers_to_remove.append(lyr)
        continue
        
    # 3. Duplicate local layers
    # We keep UAT_Iepuresti_Oficial.gpkg as the canonical official source
    if "Iepuresti_oficial_EPSG3844.gpkg" in src:
        layers_to_remove.append(lyr)
        continue
    if "ran_iepuresti.geojson" in src:
        layers_to_remove.append(lyr)
        continue
    if "01_natura2000_eea.geojson" in src:
        layers_to_remove.append(lyr)
        continue
        
    # 4. Duplicate Cladiri layer pointing to Master.gpkg (we keep the one from Oficial.gpkg)
    if "UAT_Iepuresti_Master.gpkg|layername=constructii" in src:
        layers_to_remove.append(lyr)
        continue
        
    # 5. Empty diguri
    if "IEP_04_rowater_diguri" in src:
        layers_to_remove.append(lyr)
        continue

print(f"Eliminare {len(layers_to_remove)} straturi redundante...")
for lyr in layers_to_remove:
    print(f"  [-] Eliminat: '{lyr.name()}' (id={lyr.id()})")
    project.removeMapLayer(lyr.id())

print(">>> [2/5] Curatare grupuri vechi din Layer Tree...")
# Clear old groups in root
old_groups_to_delete = []
for child in root.children():
    if isinstance(child, QgsLayerTreeGroup):
        old_groups_to_delete.append(child)

for g in old_groups_to_delete:
    root.removeChildNode(g)

print(">>> [3/5] Creare cele 4 grupuri standard...")
grp_oficial = root.addGroup("01_DATE_OFICIALE_STAT")
grp_ai      = root.addGroup("02_MODELE_ALGORITMICE_AI")
grp_osm     = root.addGroup("03_REFERINTA_BRUTA_OSM")
grp_carto   = root.addGroup("04_FOND_CARTOGRAFIC")

# Mapping of remaining layers to group and canonical clean name
# Categories:
# 1) 'oficial'
# 2) 'osm'
# 3) 'osm+AI'
# NEVER 'oficial+ai'!
print(">>> [4/5] Re-denumire si asignare in grupuri conform celor 3 criterii...")

remaining_layers = list(project.mapLayers().values())

for lyr in remaining_layers:
    name = lyr.name()
    src = lyr.source()
    is_vec = isinstance(lyr, QgsVectorLayer)
    
    target_grp = None
    new_name = None
    cat_tag = None
    
    # --- 1. DATE OFICIALE (Sursa Suverana - Fara AI) ---
    if "IEP_00_limita_UAT_ANCPI_oficial" in src or "Limita UAT" in name and "Oficial" in name:
        new_name = "Limita UAT Iepuresti (oficial - ANCPI)"
        target_grp = grp_oficial
        cat_tag = "oficial"
    elif "IEP_06_apia_blocuri_fizice_2025" in src or "APIA Blocuri Fizice 2025" in name:
        new_name = "APIA Blocuri Fizice 2025 (oficial - APIA)"
        target_grp = grp_oficial
        cat_tag = "oficial"
    elif "IEP_01_situri_arheologice_RAN" in src or "Situri Arheologice" in name:
        new_name = "Situri Arheologice RAN (oficial - INP cIMeC)"
        target_grp = grp_oficial
        cat_tag = "oficial"
    elif "IEP_02_natura2000_eea" in src or "Natura 2000" in name:
        new_name = "Natura 2000 Situri Comunitare (oficial - EEA)"
        target_grp = grp_oficial
        cat_tag = "oficial"
    elif "IEP_04_rowater_cursuri_apa" in src or "Retea Hidrografica" in name or "Cursuri Apa" in name:
        new_name = "Cursuri de Apa Neajlov (oficial - ANAR ROWATER)"
        target_grp = grp_oficial
        cat_tag = "oficial"
    elif "IEP_04_rowater_bazine_hidrografice" in src or "Bazine Hidrografice Neajlov" in name:
        new_name = "Bazin Hidrografic Neajlov (oficial - ANAR ROWATER)"
        target_grp = grp_oficial
        cat_tag = "oficial"
    elif "IEP_05_romsilva_fond_forestier" in src or "ROMSILVA Fond Forestier" in name or "OS Ghimpati" in name and "ROMSILVA" in name:
        new_name = "Fond Forestier OS Ghimpati (oficial - ROMSILVA)"
        target_grp = grp_oficial
        cat_tag = "oficial"
        
    # --- 2. MODELE ALGORITMICE / AI (Baza OSM + Procesare) ---
    elif "IEP_constructii_cadastru" in src or "Cladiri (+0.50m) TopoLT" in name:
        new_name = "Cladiri (+0.50m) TopoLT (osm+AI - StratumRO)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "drumuri_nationale" in src or "Drumuri Nationale" in name:
        new_name = "Drumuri Nationale DN (osm+AI - StratumRO)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "drumuri_judetene" in src or "Drumuri Judetene" in name:
        new_name = "Drumuri Judetene DJ (osm+AI - StratumRO)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "drumuri_comunale" in src or "Drumuri Comunale" in name:
        new_name = "Drumuri Comunale DC (osm+AI - StratumRO)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "drumuri_strazi" in src or "Strazi Locale" in name:
        new_name = "Strazi Locale ST (osm+AI - StratumRO)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "IEP_03_renns_nomenclator_strazi" in src or "RENNS Nomenclator Stradal" in name:
        new_name = "RENNS Nomenclator Stradal (osm+AI - StratumRO)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "zona_curti_constructii" in src or "Curti-Constructii" in name:
        new_name = "Curti-Constructii Intravilan CC (osm+AI - PUG)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "zona_forestiera" in src or "Fond Forestier V_PD" in name:
        new_name = "Fond Forestier V_PD (osm+AI - PUG)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "zona_ape" in src or "Zone Umede si Ape" in name or "Zone Umede & Ape" in name:
        new_name = "Zone Umede si Ape ZHA (osm+AI - PUG)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "zona_pasuni_fanete" in src or "Pasuni si Fanete" in name:
        new_name = "Pasuni si Fanete A_P (osm+AI - PUG)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "zona_agricola_arabil" in src or "Terenuri Arabile" in name:
        new_name = "Terenuri Arabile A_Ar (osm+AI - PUG)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
    elif "IEP_04_rowater_zona_inundabila_T100" in src or "Banda Inundabila T100" in name:
        new_name = "Banda Inundabila T100 (osm+AI - Modelare)"
        target_grp = grp_ai
        cat_tag = "osm+AI"
        
    # --- 3. REFERINTA BRUTA OSM ---
    elif "00_limita_uat_referinta_osm" in src or "Limita UAT Referinta" in name:
        new_name = "Limita UAT Contur (osm)"
        target_grp = grp_osm
        cat_tag = "osm"
        
    # --- 4. FOND CARTOGRAFIC ---
    elif "OpenStreetMap" in name or "openstreetmap.org" in src:
        new_name = "OpenStreetMap (osm)"
        target_grp = grp_carto
        cat_tag = "osm"
    elif "Esri Satellite" in name or "arcgisonline" in src:
        new_name = "Esri Satellite (oficial - Esri Imagery)"
        target_grp = grp_carto
        cat_tag = "oficial"
    else:
        # Fallback
        new_name = name
        target_grp = grp_ai
        cat_tag = "osm+AI"
        
    if new_name:
        lyr.setName(new_name)
    
    # Update attributes if vector
    if is_vec:
        fields = [f.name() for f in lyr.fields()]
        lyr.startEditing()
        if "criteriu_provenienta" not in fields:
            lyr.addAttribute(QgsField("criteriu_provenienta", QVariant.String, len=30))
            lyr.updateFields()
            fields.append("criteriu_provenienta")
            
        c_idx = lyr.fields().indexFromName("criteriu_provenienta")
        for feat in lyr.getFeatures():
            feat[c_idx] = cat_tag
            lyr.updateFeature(feat)
        lyr.commitChanges()
        
    # Add to assigned tree group
    if target_grp:
        target_grp.addLayer(lyr)
        print(f"  [+] Adaugat in [{target_grp.name()}]: '{new_name}' (tag={cat_tag})")

print(">>> [5/5] Salvare si refresh Canvas...")
if hasattr(iface, "mapCanvas"):
    # Zoom to UAT extent
    uat_lyr = None
    for l in project.mapLayers().values():
        if "Limita UAT Iepuresti (oficial - ANCPI)" in l.name():
            uat_lyr = l
            break
    if uat_lyr:
        ext = uat_lyr.extent()
        ext.scale(1.08)
        iface.mapCanvas().setExtent(ext)
    iface.mapCanvas().refresh()

print(">>> Curatare si reierarhizare finalizata cu succes!")
'''

if __name__ == "__main__":
    print("=" * 70)
    print(">>> EXECUTIE PLAN: CURATARE, RESTRUCTURARE & CLASIFICARE STRICTA <<<")
    print("=" * 70)
    
    code = build_pyqgis_execution_code()
    res = send_qgis_mcp("execute_code", {"code": code, "timeout": 45.0})
    print("Status:", res.get("status"))
    if "result" in res:
        print(res["result"].get("stdout", ""))
        if res["result"].get("error"):
            print("ERROR:", res["result"].get("error"))
            
    # Save project in QGIS
    save_res = send_qgis_mcp("save_project")
    print("Save Project:", save_res.get("status"))
    print("=" * 70)
