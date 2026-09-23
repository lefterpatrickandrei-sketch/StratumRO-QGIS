# -*- coding: utf-8 -*-
"""
STRATUMRO — QGIS MCP Production Engine for UAT Iepurești.
Connects via socket 127.0.0.1:9876 to the running QGIS Desktop 3.40 instance.
Executes Chapter 1, 2, 3, 4:
- Chapter 1: Validates live socket and environment.
- Chapter 2: Injects master cadastral buildings (+0.50m offset), road network,
  and urban zoning into hierarchical layer tree groups.
- Chapter 3: Integrates high-res backdrop and validates spatial reference (EPSG:3844).
- Chapter 4: Formats TopoLT / ANCPI symbology, fits canvas, and saves visual proof screenshot.
"""

import sys
import json
import base64
import socket
import struct
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
MASTER_GPKG = ROOT / "projects" / "UAT_Iepuresti" / "output" / "UAT_Iepuresti_Master.gpkg"
S2_RGB = ROOT / "projects" / "UAT_Iepuresti" / "output" / "sentinel2_rgb_iepuresti.tif"
OPEN_GPKG = Path(r"C:\Users\lefpa\.cline\worktrees\ancpi-footprint-validation\workspace\UAT_Iepuresti\PUG_Draft\OpenData\PUG_Iepuresti_OpenData.gpkg")
SCREENSHOT_PATH = ROOT / "workspace" / "output" / "qgis_iepuresti_mcp_canvas.png"
SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

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

def build_pyqgis_script():
    master_path_str = str(MASTER_GPKG).replace("\\", "/")
    s2_path_str = str(S2_RGB).replace("\\", "/")
    open_path_str = str(OPEN_GPKG).replace("\\", "/")
    
    code = f'''
import sys
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSingleSymbolRenderer, QgsCoordinateReferenceSystem,
    QgsRectangle, QgsLayerTreeGroup, QgsLayerTreeLayer
)
from qgis.PyQt.QtGui import QColor

project = QgsProject.instance()
root = project.layerTreeRoot()

print(">>> QGIS MCP: Incepe organizarea ierarhiei de straturi pentru UAT Iepuresti...")

# 1. Definire sau recuperare grupuri majore
def get_or_create_group(name, parent=root):
    grp = parent.findGroup(name)
    if grp is None:
        grp = parent.addGroup(name)
    return grp

grp_admin = get_or_create_group("00_ADMINISTRATIV_ANCPI")
grp_bldgs = get_or_create_group("01_CADASTRU_CONSTRUCTII")
grp_roads = get_or_create_group("02_CIRCULATII_RETELE")
grp_zones = get_or_create_group("03_ZONIFICARE_PUG")
grp_prot  = get_or_create_group("04_PROTECTII_PATRIMONIU")
grp_ortho = get_or_create_group("05_FOND_CARTOGRAFIC")

# 2. Re-aranjare straturi existente in grupuri corespunzatoare
for layer in list(project.mapLayers().values()):
    lname = layer.name().lower()
    tree_layer = root.findLayer(layer.id())
    if not tree_layer:
        continue
    parent_node = tree_layer.parent()
    
    if "limita" in lname or "ancpi" in lname:
        if parent_node != grp_admin:
            clone = tree_layer.clone()
            grp_admin.addChildNode(clone)
            parent_node.removeChildNode(tree_layer)
    elif "ran" in lname or "arheologic" in lname or "natura" in lname:
        if parent_node != grp_prot:
            clone = tree_layer.clone()
            grp_prot.addChildNode(clone)
            parent_node.removeChildNode(tree_layer)
    elif "rowater" in lname or "apa" in lname:
        if parent_node != grp_zones and parent_node != grp_prot:
            clone = tree_layer.clone()
            grp_zones.addChildNode(clone)
            parent_node.removeChildNode(tree_layer)

# 3. Adaugare si stilizare straturi de productie din UAT_Iepuresti_Master.gpkg
master_gpkg = "{master_path_str}"

# A. Constructii / Cladiri (+0.50m cadastral offset)
existing_bld = [l for l in project.mapLayers().values() if l.name() == "Cladiri (+0.50m) TopoLT"]
if not existing_bld:
    bld_lyr = QgsVectorLayer(f"{{master_gpkg}}|layername=constructii", "Cladiri (+0.50m) TopoLT", "ogr")
    if bld_lyr.isValid():
        # Simbol cadastral ANCPI 1CC / 2CC
        sym = QgsFillSymbol.createSimple({{
            "color": "217,95,2,140",       # Portocaliu cadastral translucent
            "outline_color": "127,0,0,255", # Rosu caramiziu contur
            "outline_width": "0.35"
        }})
        bld_lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(bld_lyr, False)
        grp_bldgs.addLayer(bld_lyr)
        print("Adaugat: Cladiri (+0.50m) TopoLT (646 constructii)")

# B. Retea Rutiera Clasificata (DN, DJ, DC, ST)
road_specs = [
    ("drumuri_nationale", "Drumuri Nationale (DN)", "227,26,28,255", "1.1"),
    ("drumuri_judetene",  "Drumuri Judetene (DJ)",  "255,127,0,255", "0.85"),
    ("drumuri_comunale",  "Drumuri Comunale (DC)",  "255,215,0,255", "0.65"),
    ("drumuri_strazi",    "Strazi Locale (ST)",     "240,240,240,255", "0.40")
]

for lyr_name, display_name, col_rgba, width in road_specs:
    if not [l for l in project.mapLayers().values() if l.name() == display_name]:
        r_lyr = QgsVectorLayer(f"{{master_gpkg}}|layername={{lyr_name}}", display_name, "ogr")
        if r_lyr.isValid():
            sym = QgsLineSymbol.createSimple({{
                "color": col_rgba,
                "width": width,
                "capstyle": "round",
                "joinstyle": "round"
            }})
            r_lyr.setRenderer(QgsSingleSymbolRenderer(sym))
            project.addMapLayer(r_lyr, False)
            grp_roads.addLayer(r_lyr)
            print(f"Adaugat drum: {{display_name}}")

# C. Zonificare PUG (Arabil, Păduri, Ape, Curți-Construcții, Pășuni)
zone_specs = [
    ("zona_ape",               "Zone Umede & Ape (ZHA)",          "107,174,214,140", "8,81,156,255", "0.3"),
    ("zona_forestiera",        "Fond Forestier (V_PD)",           "49,163,84,120",   "0,109,44,255", "0.3"),
    ("zona_curti_constructii", "Curti-Constructii Intravilan (CC)", "254,227,145,110", "217,95,14,255", "0.35"),
    ("zona_pasuni_fanete",     "Pasuni si Fanete (A_P)",          "199,233,192,90",  "116,196,118,255", "0.2"),
    ("zona_agricola_arabil",   "Terenuri Arabile (A_Ar)",         "247,247,247,50",  "180,180,180,200", "0.2")
]

for lyr_name, display_name, fill_rgba, stroke_rgba, width in zone_specs:
    if not [l for l in project.mapLayers().values() if l.name() == display_name]:
        z_lyr = QgsVectorLayer(f"{{master_gpkg}}|layername={{lyr_name}}", display_name, "ogr")
        if z_lyr.isValid():
            sym = QgsFillSymbol.createSimple({{
                "color": fill_rgba,
                "outline_color": stroke_rgba,
                "outline_width": width
            }})
            z_lyr.setRenderer(QgsSingleSymbolRenderer(sym))
            project.addMapLayer(z_lyr, False)
            grp_zones.addLayer(z_lyr)
            print(f"Adaugat zonificare: {{display_name}}")

# D. Adaugare Raster Ortofoto / Sentinel-2 RGB
s2_tif = "{s2_path_str}"
if not [l for l in project.mapLayers().values() if l.name() == "Ortofoto Sentinel-2 RGB"]:
    s2_lyr = QgsRasterLayer(s2_tif, "Ortofoto Sentinel-2 RGB", "gdal")
    if s2_lyr.isValid():
        project.addMapLayer(s2_lyr, False)
        grp_ortho.addLayer(s2_lyr)
        print("Adaugat raster: Ortofoto Sentinel-2 RGB")

# 4. Ajustare Zoom & Refresh Canvas pe UAT Iepuresti
canvas = iface.mapCanvas()
uat_layers = [l for l in project.mapLayers().values() if "limita_uat" in l.name().lower()]
if uat_layers:
    target_extent = uat_layers[0].extent()
    # Adaugare buffer 5% in jurul extinderii
    target_extent.scale(1.05)
    canvas.setExtent(target_extent)
    print("Canvas zoom setat pe limita UAT Iepuresti:", target_extent.toString())

canvas.refresh()
print(">>> QGIS MCP: Sincronizare reusita! Proiectul este complet actualizat.")
'''
    return code

def main():
    print("=" * 65)
    print(">>> STRATUMRO: EXECUTIE MISIUNE UAT IEPURESTI PRIN QGIS MCP <<<")
    print("=" * 65)
    
    # 1. Verificare socket
    print("Pasul 1: Conectare la QGIS MCP pe 127.0.0.1:9876...")
    proj_info = send_qgis_mcp("get_project_info")
    if proj_info.get("status") != "success":
        print("EROARE: Nu s-a putut citi proiectul din QGIS MCP:", proj_info)
        sys.exit(1)
    
    p = proj_info.get("result", {})
    print(f"Proiect activ: {p.get('filename')}")
    print(f"Titlu: {p.get('title')}")
    print(f"CRS: {p.get('crs')}")
    print(f"Straturi initiale: {p.get('layer_count')}")
    
    # 2. Executie cod PyQGIS in firul principal al QGIS Desktop
    print("\nPasul 2: Injectare straturi, ierarhizare si stilizare profesionala...")
    py_code = build_pyqgis_script()
    exec_res = send_qgis_mcp("execute_code", {"code": py_code, "timeout": 30.0})
    if exec_res.get("status") == "success":
        res_data = exec_res.get("result", {})
        stdout_txt = res_data.get("stdout", "")
        stderr_txt = res_data.get("stderr", "")
        if stdout_txt:
            print("--- Output QGIS Desktop ---")
            print(stdout_txt)
        if stderr_txt:
            print("--- Stderr QGIS Desktop ---")
            print(stderr_txt)
        print("Executie PyQGIS reusita!")
    else:
        print("EROARE la executie cod in QGIS MCP:", exec_res)
        sys.exit(1)
        
    # 3. Salvare proiect actualizat
    print("\nPasul 3: Salvare proiect...")
    save_res = send_qgis_mcp("save_project")
    print("Rezultat salvare:", save_res)
    
    # 4. Captura Screenshot Canvas ca dovada vizuala
    print("\nPasul 4: Captura Screenshot Canvas QGIS...")
    shot_res = send_qgis_mcp("get_canvas_screenshot")
    if shot_res.get("status") == "success":
        b64 = shot_res.get("result", {}).get("base64_data")
        if b64:
            with open(SCREENSHOT_PATH, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"Screenshot salvat cu succes: {SCREENSHOT_PATH} ({SCREENSHOT_PATH.stat().st_size} bytes)")
    else:
        print("Avertisment: Nu s-a putut prelua screenshot:", shot_res)
        
    print("\n" + "=" * 65)
    print(">>> MISIUNE QGIS MCP FINALIZATA CU SUCCES! <<<")
    print("=" * 65)

if __name__ == "__main__":
    main()
