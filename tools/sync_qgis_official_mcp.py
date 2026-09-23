# -*- coding: utf-8 -*-
"""
Sync Official Layers with Full Provenance to live QGIS Desktop session via QGIS MCP.
Organizes layer tree into the standard 6 groups, sets symbology, zooms, and saves.
"""
import sys
import json
import base64
import socket
import struct
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI")
OFFICIAL_GPKG = ROOT / "projects" / "UAT_Iepuresti" / "output" / "UAT_Iepuresti_Oficial.gpkg"
S2_RGB = ROOT / "projects" / "UAT_Iepuresti" / "output" / "sentinel2_rgb_iepuresti.tif"
SCREENSHOT_PATH = ROOT / "workspace" / "output" / "qgis_iepuresti_official_criteria_render.png"

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

def build_pyqgis_sync_code():
    gpkg_str = str(OFFICIAL_GPKG).replace("\\", "/")
    s2_str = str(S2_RGB).replace("\\", "/")
    
    code = f'''
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer, QgsCoordinateReferenceSystem,
    QgsRectangle
)

project = QgsProject.instance()
root = project.layerTreeRoot()

print(">>> QGIS MCP: Incepe sincronizarea integrala a celor 7 criterii oficiale...")

def get_or_create_group(name, parent=root):
    grp = parent.findGroup(name)
    if grp is None:
        grp = parent.addGroup(name)
    return grp

grp_admin  = get_or_create_group("00_ADMINISTRATIV_ANCPI")
grp_cad    = get_or_create_group("01_CADASTRU_CONSTRUCTII_RENNS")
grp_roads  = get_or_create_group("02_CIRCULATII_RETELE")
grp_water  = get_or_create_group("03_RESTRICTII_RISC_ROWATER")
grp_env    = get_or_create_group("04_PROTECTII_MEDIU_RAN_ROMSILVA")
grp_apia   = get_or_create_group("05_AGRICOL_APIA_2025")
grp_ortho  = get_or_create_group("06_FOND_CARTOGRAFIC")

gpkg = "{gpkg_str}"

# 1. ANCPI Limita UAT
if not [l for l in project.mapLayers().values() if l.name() == "Limita UAT ANCPI Oficiala"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_00_limita_UAT_ANCPI_oficial", "Limita UAT ANCPI Oficiala", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "0,0,0,0", "outline_color": "227,26,28,255", "outline_width": "0.9"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_admin.addLayer(lyr)

# 2. Cadastru Constructii (+0.50m) TopoLT
if not [l for l in project.mapLayers().values() if l.name() == "Cladiri (+0.50m) TopoLT Oficial"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_constructii_cadastru", "Cladiri (+0.50m) TopoLT Oficial", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "217,95,2,160", "outline_color": "127,0,0,255", "outline_width": "0.35"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_cad.addLayer(lyr)

# 3. RENNS Nomenclator Stradal
if not [l for l in project.mapLayers().values() if l.name() == "RENNS Nomenclator Stradal"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_03_renns_nomenclator_strazi", "RENNS Nomenclator Stradal", "ogr")
    if lyr.isValid():
        sym = QgsLineSymbol.createSimple({{"color": "254,178,76,255", "width": "0.6", "capstyle": "round"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_cad.addLayer(lyr)

# 4. ROWATER Cursuri de Apa & Banda Inundabila
if not [l for l in project.mapLayers().values() if l.name() == "ROWATER Retea Hidrografica"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_04_rowater_cursuri_apa", "ROWATER Retea Hidrografica", "ogr")
    if lyr.isValid():
        sym = QgsLineSymbol.createSimple({{"color": "31,120,180,255", "width": "0.7", "capstyle": "round"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_water.addLayer(lyr)

if not [l for l in project.mapLayers().values() if l.name() == "ROWATER Banda Inundabila T100"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_04_rowater_zona_inundabila_T100", "ROWATER Banda Inundabila T100", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "166,206,227,130", "outline_color": "31,120,180,255", "outline_width": "0.35"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_water.addLayer(lyr)

# 5. Protectii Mediu: Natura 2000, RAN, ROMSILVA
if not [l for l in project.mapLayers().values() if l.name() == "Natura 2000 Situri Comunitare"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_02_natura2000_eea", "Natura 2000 Situri Comunitare", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "51,160,44,100", "outline_color": "0,100,0,255", "outline_width": "0.4"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_env.addLayer(lyr)

if not [l for l in project.mapLayers().values() if l.name() == "RAN Situri Arheologice Protejate"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_01_situri_arheologice_RAN", "RAN Situri Arheologice Protejate", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "122,1,119,70", "outline_color": "73,0,106,255", "outline_width": "0.45"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_env.addLayer(lyr)

if not [l for l in project.mapLayers().values() if l.name() == "ROMSILVA Fond Forestier"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_05_romsilva_fond_forestier", "ROMSILVA Fond Forestier", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "49,163,84,130", "outline_color": "0,109,44,255", "outline_width": "0.35"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_env.addLayer(lyr)

# 6. APIA Blocuri Fizice 2025
if not [l for l in project.mapLayers().values() if l.name() == "APIA Blocuri Fizice 2025 Oficial"]:
    lyr = QgsVectorLayer(f"{{gpkg}}|layername=IEP_06_apia_blocuri_fizice_2025", "APIA Blocuri Fizice 2025 Oficial", "ogr")
    if lyr.isValid():
        sym = QgsFillSymbol.createSimple({{"color": "255,255,178,50", "outline_color": "189,189,189,200", "outline_width": "0.2"}})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(lyr, False)
        grp_apia.addLayer(lyr)

# 7. Ortofoto Sentinel-2 RGB
s2_tif = "{s2_str}"
if not [l for l in project.mapLayers().values() if l.name() == "Ortofoto Sentinel-2 RGB"]:
    s2_lyr = QgsRasterLayer(s2_tif, "Ortofoto Sentinel-2 RGB", "gdal")
    if s2_lyr.isValid():
        project.addMapLayer(s2_lyr, False)
        grp_ortho.addLayer(s2_lyr)

# Setare Canvas pe UAT Iepuresti in Stereo 70
canvas = iface.mapCanvas()
canvas.setExtent(QgsRectangle(566000.0, 300000.0, 575000.0, 312000.0))
canvas.refresh()
print(">>> QGIS MCP: Sincronizare reusita a tuturor celor 7 criterii oficiale!")
'''
    return code

def main():
    print("=" * 65)
    print(">>> QGIS MCP: SINCRONIZARE CRITERII OFICIALE IN QGIS DESKTOP <<<")
    print("=" * 65)
    
    # 1. Conectare
    print("Conectare la QGIS MCP pe 127.0.0.1:9876...")
    proj_info = send_qgis_mcp("get_project_info")
    print(f"Proiect activ: {proj_info.get('result', {}).get('filename')}")
    
    # 2. Executie PyQGIS
    print("Injectare straturi oficiale si ierarhizare pe cele 6 directoare...")
    code = build_pyqgis_sync_code()
    res = send_qgis_mcp("execute_code", {"code": code, "timeout": 30.0})
    if res.get("status") == "success":
        print(res.get("result", {}).get("stdout"))
    else:
        print("EROARE:", res)
        sys.exit(1)
        
    # 3. Salvare proiect
    print("Salvare proiect in QGIS Desktop...")
    save_res = send_qgis_mcp("save_project")
    print("Salvat:", save_res.get("result"))
    
    # 4. Randare Map Canvas
    print("Randare imagine de verificare...")
    rnd_res = send_qgis_mcp("render_map_base64", {"width": 1600, "height": 1000})
    if rnd_res.get("status") == "success":
        b64 = rnd_res.get("result", {}).get("base64_data")
        with open(SCREENSHOT_PATH, "wb") as f:
            f.write(base64.b64decode(b64))
        print(f"Randare salvată cu succes: {SCREENSHOT_PATH} ({SCREENSHOT_PATH.stat().st_size} bytes)")
    
    print("=" * 65)
    print(">>> PROCES FINALIZAT CU SUCCES! <<<")
    print("=" * 65)

if __name__ == "__main__":
    main()
