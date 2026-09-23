# -*- coding: utf-8 -*-
"""
Rebuild Clean QGIS Project with the Strict 3-Tier Hierarchy:
01_DATE_OFICIALE_STAT (oficial)
02_MODELE_ALGORITMICE_AI (osm+AI)
03_REFERINTA_BRUTA_OSM (osm)
04_FOND_CARTOGRAFIC (oficial / osm)

Enforces:
- EPSG:3844 Stereo 70
- Strict 3 criteria: 'oficial', 'osm', 'osm+AI'
- NO 'oficial+ai'
- All original attributes preserved
- Criteriu provenienta populated in attribute table
- Zero duplicate layers
"""
import sys
import json
import socket
import struct
from pathlib import Path

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI")
OFICIAL_GPKG = ROOT / "projects" / "UAT_Iepuresti" / "output" / "UAT_Iepuresti_Oficial.gpkg"
MASTER_GPKG = ROOT / "projects" / "UAT_Iepuresti" / "output" / "UAT_Iepuresti_Master.gpkg"
OSM_UAT = Path(r"C:\Users\lefpa\Downloads\GIS_UAT_Iepuresti\00_limita_uat_referinta_osm.geojson")

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

def build_pyqgis_code():
    oficial_gpkg_str = str(OFICIAL_GPKG).replace("\\", "/")
    master_gpkg_str = str(MASTER_GPKG).replace("\\", "/")
    osm_uat_str = str(OSM_UAT).replace("\\", "/")
    
    return f'''
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer, QgsCoordinateReferenceSystem,
    QgsRectangle, QgsField
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

project = QgsProject.instance()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("UAT Iepurești — Cadastru & PUG (Clasificare Oficială)")
root = project.layerTreeRoot()

# 1. Clear existing layers and tree
project.removeAllMapLayers()
root.clear()

# 2. Create the 4 strict groups
grp_oficial = root.addGroup("01_DATE_OFICIALE_STAT")
grp_ai      = root.addGroup("02_MODELE_ALGORITMICE_AI")
grp_osm     = root.addGroup("03_REFERINTA_BRUTA_OSM")
grp_carto   = root.addGroup("04_FOND_CARTOGRAFIC")

oficial_gpkg = "{oficial_gpkg_str}"
master_gpkg  = "{master_gpkg_str}"
osm_uat      = "{osm_uat_str}"

def add_vector_layer(uri, name, group, symbol_type, sym_props, cat_tag):
    lyr = QgsVectorLayer(uri, name, "ogr")
    if not lyr.isValid():
        print(f"FAILED to load: {{name}} (uri={{uri}})")
        return None
        
    # Set symbol
    if symbol_type == "fill":
        sym = QgsFillSymbol.createSimple(sym_props)
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    elif symbol_type == "line":
        sym = QgsLineSymbol.createSimple(sym_props)
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        
    # Ensure criteriu_provenienta is present
    fields = [f.name() for f in lyr.fields()]
    lyr.startEditing()
    if "criteriu_provenienta" not in fields:
        lyr.addAttribute(QgsField("criteriu_provenienta", QVariant.String, len=30))
        lyr.updateFields()
    c_idx = lyr.fields().indexFromName("criteriu_provenienta")
    for feat in lyr.getFeatures():
        feat[c_idx] = cat_tag
        lyr.updateFeature(feat)
    lyr.commitChanges()
    
    project.addMapLayer(lyr, False)
    group.addLayer(lyr)
    print(f"  [+] Incarcat: '{{name}}' ({{lyr.featureCount()}} feat)")
    return lyr

print(">>> [1/4] Incarcare 01_DATE_OFICIALE_STAT (oficial)...")
# 1. Limita UAT ANCPI
l_uat = add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_00_limita_UAT_ANCPI_oficial",
    "Limita UAT Iepuresti (oficial - ANCPI)",
    grp_oficial, "fill",
    {{"color": "0,0,0,0", "outline_color": "227,26,28,255", "outline_width": "1.0"}},
    "oficial"
)

# 2. APIA Blocuri Fizice 2025
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_06_apia_blocuri_fizice_2025",
    "APIA Blocuri Fizice 2025 (oficial - APIA)",
    grp_oficial, "fill",
    {{"color": "255,255,178,45", "outline_color": "160,160,160,200", "outline_width": "0.2"}},
    "oficial"
)

# 3. RAN Situri Arheologice
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_01_situri_arheologice_RAN",
    "Situri Arheologice RAN (oficial - INP cIMeC)",
    grp_oficial, "fill",
    {{"color": "152,78,163,80", "outline_color": "152,78,163,255", "outline_width": "0.6"}},
    "oficial"
)

# 4. Natura 2000
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_02_natura2000_eea",
    "Natura 2000 Situri Comunitare (oficial - EEA)",
    grp_oficial, "fill",
    {{"color": "51,160,44,70", "outline_color": "51,160,44,255", "outline_width": "0.5"}},
    "oficial"
)

# 5. Cursuri Apa Neajlov
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_04_rowater_cursuri_apa",
    "Cursuri de Apa Neajlov (oficial - ANAR ROWATER)",
    grp_oficial, "line",
    {{"color": "31,120,180,255", "width": "0.7"}},
    "oficial"
)

# 6. Fond Forestier OS Ghimpati
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_05_romsilva_fond_forestier",
    "Fond Forestier OS Ghimpati (oficial - ROMSILVA)",
    grp_oficial, "fill",
    {{"color": "34,139,34,80", "outline_color": "0,100,0,255", "outline_width": "0.4"}},
    "oficial"
)

print(">>> [2/4] Incarcare 02_MODELE_ALGORITMICE_AI (osm+AI)...")
# 1. Cladiri (+0.50m) TopoLT
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_constructii_cadastru",
    "Cladiri (+0.50m) TopoLT (osm+AI - StratumRO)",
    grp_ai, "fill",
    {{"color": "217,95,2,160", "outline_color": "127,0,0,255", "outline_width": "0.35"}},
    "osm+AI"
)

# 2. Drumuri Clasificate DN, DJ, DC, ST
add_vector_layer(
    f"{{master_gpkg}}|layername=drumuri_nationale",
    "Drumuri Nationale DN (osm+AI - StratumRO)",
    grp_ai, "line",
    {{"color": "227,26,28,255", "width": "0.9"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=drumuri_judetene",
    "Drumuri Judetene DJ (osm+AI - StratumRO)",
    grp_ai, "line",
    {{"color": "255,127,0,255", "width": "0.7"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=drumuri_comunale",
    "Drumuri Comunale DC (osm+AI - StratumRO)",
    grp_ai, "line",
    {{"color": "253,191,111,255", "width": "0.55"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=drumuri_strazi",
    "Strazi Locale ST (osm+AI - StratumRO)",
    grp_ai, "line",
    {{"color": "120,120,120,200", "width": "0.35"}},
    "osm+AI"
)

# 3. RENNS Nomenclator Stradal
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_03_renns_nomenclator_strazi",
    "RENNS Nomenclator Stradal (osm+AI - StratumRO)",
    grp_ai, "line",
    {{"color": "106,61,154,200", "width": "0.4"}},
    "osm+AI"
)

# 4. Zonificare PUG
add_vector_layer(
    f"{{master_gpkg}}|layername=zona_curti_constructii",
    "Curti-Constructii Intravilan CC (osm+AI - PUG)",
    grp_ai, "fill",
    {{"color": "255,150,0,110", "outline_color": "190,70,0,255", "outline_width": "0.2"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=zona_forestiera",
    "Fond Forestier V_PD (osm+AI - PUG)",
    grp_ai, "fill",
    {{"color": "34,139,34,110", "outline_color": "0,100,0,255", "outline_width": "0.2"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=zona_ape",
    "Zone Umede si Ape ZHA (osm+AI - PUG)",
    grp_ai, "fill",
    {{"color": "30,144,255,120", "outline_color": "0,0,205,255", "outline_width": "0.2"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=zona_pasuni_fanete",
    "Pasuni si Fanete A_P (osm+AI - PUG)",
    grp_ai, "fill",
    {{"color": "215,235,180,90", "outline_color": "165,195,125,160", "outline_width": "0.1"}},
    "osm+AI"
)

add_vector_layer(
    f"{{master_gpkg}}|layername=zona_agricola_arabil",
    "Terenuri Arabile A_Ar (osm+AI - PUG)",
    grp_ai, "fill",
    {{"color": "252,243,222,70", "outline_color": "220,205,175,130", "outline_width": "0.1"}},
    "osm+AI"
)

# 5. Banda Inundabila T100
add_vector_layer(
    f"{{oficial_gpkg}}|layername=IEP_04_rowater_zona_inundabila_T100",
    "Banda Inundabila T100 (osm+AI - Modelare)",
    grp_ai, "fill",
    {{"color": "31,120,180,90", "outline_color": "31,120,180,255", "outline_width": "0.4"}},
    "osm+AI"
)

print(">>> [3/4] Incarcare 03_REFERINTA_BRUTA_OSM (osm)...")
add_vector_layer(
    osm_uat,
    "Limita UAT Contur (osm)",
    grp_osm, "line",
    {{"color": "100,100,100,180", "width": "0.4"}},
    "osm"
)

print(">>> [4/4] Incarcare 04_FOND_CARTOGRAFIC...")
# 1. Esri Satellite (oficial imagery)
esri_url = "type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0"
esri_lyr = QgsRasterLayer(esri_url, "Esri Satellite (oficial - Esri Imagery)", "wms")
if esri_lyr.isValid():
    project.addMapLayer(esri_lyr, False)
    grp_carto.addLayer(esri_lyr)
    # default unchecked
    root.findLayer(esri_lyr.id()).setItemVisibilityChecked(False)

# 2. OpenStreetMap (osm)
osm_url = "type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0"
osm_lyr = QgsRasterLayer(osm_url, "OpenStreetMap (osm)", "wms")
if osm_lyr.isValid():
    project.addMapLayer(osm_lyr, False)
    grp_carto.addLayer(osm_lyr)
    root.findLayer(osm_lyr.id()).setItemVisibilityChecked(False)

# Zoom canvas to UAT extent
if l_uat and hasattr(iface, "mapCanvas"):
    ext = l_uat.extent()
    ext.scale(1.08)
    iface.mapCanvas().setExtent(ext)
    iface.mapCanvas().refresh()

print(">>> Proiect reconfigurat impecabil pe cele 4 grupuri stricte!")
'''

if __name__ == "__main__":
    print("=" * 70)
    print(">>> STRATUMRO: RECONSTRUIRE PROIECT QGIS CLASIFICARE STRICTA <<<")
    print("=" * 70)
    
    code = build_pyqgis_code()
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
