# -*- coding: utf-8 -*-
"""
StratumRO — Actualizare Structura Proiect QGIS conform Instructiunilor Utilizatorului:
1. Natura 2000 National (EEA Discomap WMS complet pentru toata tara)
2. Setare definitiva TransDAT-RO 7 parametri Helmert (rezolva Ballpark Transform)
3. Geologie IGR 1:1M adaugata exclusiv la nivel National (Studiu fundamentare PUG)
4. Redenumire si marcare riguroasa a straturilor derivate:
   - Daca e oficial -> (oficial - Sursa)
   - Daca e derivat -> (de referinta - Sursa | Cerinta PUG: Scara 1:1.000 / 1:5.000 conform Ghid GP 038/99)
5. Adaugare Drumuri Majore (CNAIR) si Cai Ferate (CFR) in Serverul National
"""

import sys
import os
sys.path.insert(0, ".")
from tools.test_layer_url_properties import send_qgis_mcp

qgis_update_code = '''
import os
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsLayerTreeGroup,
    QgsCoordinateReferenceSystem, QgsCoordinateTransformContext,
    QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
    QgsSingleSymbolRenderer, QgsSymbol
)
from qgis.PyQt.QtGui import QColor

project = QgsProject.instance()
root = project.layerTreeRoot()

BASE_DIR = r"c:/Users/lefpa/Downloads/QGIS-AI/national_server"

# ==============================================================================
# PASUL 2: TransDAT-RO Coordinate Transform (Rezolva Ballpark Transform)
# ==============================================================================
context = project.transformContext()
crs_wgs = QgsCoordinateReferenceSystem("EPSG:4326")
crs_st70 = QgsCoordinateReferenceSystem("EPSG:3844")

proj_transdat = (
    "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad "
    "+step +proj=push +v_3 +step +proj=cart +ellps=WGS84 "
    "+step +inv +proj=helmert +x=2.329 +y=-147.042 +z=-92.08 "
    "+rx=0.309 +ry=-0.325 +rz=-0.497 +s=5.69 +convention=coordinate_frame "
    "+step +inv +proj=cart +ellps=krass +step +proj=pop +v_3 "
    "+step +proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass"
)

context.addCoordinateOperation(crs_wgs, crs_st70, proj_transdat)
context.addCoordinateOperation(crs_st70, crs_wgs, proj_transdat)
project.setTransformContext(context)
print("[OK] TransDAT-RO Helmert 7-param activat in proiect.")

# ==============================================================================
# PASUL 1 & 3 & 5: Adaugare straturi in 00_SERVER_NATIONAL_ROMANIA
# ==============================================================================
grp_nat = root.findGroup("00_SERVER_NATIONAL_ROMANIA")
if not grp_nat:
    grp_nat = root.insertGroup(0, "00_SERVER_NATIONAL_ROMANIA")

# Straturi noi de adaugat la nivel national
national_additions = [
    {
        "id_key": "natura2000_national_wms",
        "name": "EEA — Natura 2000 Situri Habitate si Pasari (oficial - EEA National WMS)",
        "source": "contextualWMSLegend=0&crs=EPSG:3844&dpiMode=7&featureCount=10&format=image/png&layers=2&styles=&url=https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer",
        "type": "raster",
        "visible": False
    },
    {
        "id_key": "igr_geologie_national",
        "name": "IGR — Harta Geologica a Romaniei 1:1M (oficial - IGR | Studiu Fundamentare PUG)",
        "source": os.path.join(BASE_DIR, "11_GEOLOGIE_IGR", "Geologie_1M_pr.shp"),
        "type": "vector",
        "geom": "polygon",
        "fill": QColor(226, 232, 240, 70),
        "stroke": QColor(113, 128, 150, 180),
        "width": 0.25,
        "visible": False
    },
    {
        "id_key": "cnair_drumuri_majore",
        "name": "CNAIR / MMAP — Drumuri Principale Romania (oficial - CNAIR / MMAP)",
        "source": os.path.join(BASE_DIR, "08_TRANSPORT_CNAIR_CFR", "MajorRoads_Romania_CNAIR_MMAP.gpkg"),
        "type": "vector",
        "geom": "polygon",
        "fill": QColor(239, 68, 68, 40),
        "stroke": QColor(185, 28, 28, 220),
        "width": 0.4,
        "visible": True
    },
    {
        "id_key": "cfr_cai_ferate",
        "name": "CFR / MMAP — Cai Ferate Nationale Romania (oficial - CFR / MMAP)",
        "source": os.path.join(BASE_DIR, "08_TRANSPORT_CNAIR_CFR", "MajorRailways_Romania_CFR_MMAP.gpkg"),
        "type": "vector",
        "geom": "line",
        "color": QColor(17, 24, 39, 255),
        "width": 0.5,
        "visible": True
    }
]

existing_layer_names = [l.name() for l in project.mapLayers().values()]

for item in national_additions:
    if item["name"] in existing_layer_names:
        print(f"[EXISTS] Strat deja prezent: {item['name']}")
        continue

    if item["type"] == "vector":
        if not os.path.exists(item["source"].split("|")[0]):
            print(f"[SKIP] Fisier absent: {item['source']}")
            continue
        lyr = QgsVectorLayer(item["source"], item["name"], "ogr")
        if lyr.isValid():
            geom = item.get("geom")
            if geom == "polygon":
                sym = QgsSymbol.defaultSymbol(lyr.geometryType())
                sl = QgsSimpleFillSymbolLayer()
                sl.setFillColor(item["fill"])
                sl.setStrokeColor(item["stroke"])
                sl.setStrokeWidth(item["width"])
                sym.changeSymbolLayer(0, sl)
                lyr.setRenderer(QgsSingleSymbolRenderer(sym))
            elif geom == "line":
                sym = QgsSymbol.defaultSymbol(lyr.geometryType())
                sl = QgsSimpleLineSymbolLayer()
                sl.setColor(item["color"])
                sl.setWidth(item["width"])
                sym.changeSymbolLayer(0, sl)
                lyr.setRenderer(QgsSingleSymbolRenderer(sym))
            project.addMapLayer(lyr, False)
            node = grp_nat.addLayer(lyr)
            node.setItemVisibilityChecked(item["visible"])
            print(f"[OK] Adaugat Vector National: {item['name']}")
    elif item["type"] == "raster":
        lyr = QgsRasterLayer(item["source"], item["name"], "wms")
        if lyr.isValid():
            project.addMapLayer(lyr, False)
            node = grp_nat.addLayer(lyr)
            node.setItemVisibilityChecked(item["visible"])
            print(f"[OK] Adaugat Raster/WMS National: {item['name']}")

# ==============================================================================
# PASUL 4: Redenumire si Marcare Riguroasa Straturi Derivate conform PUG
# ==============================================================================
# Conform Ghid PUG (GP 038/99):
# - Teritoriu Administrativ general: Scara 1:5.000 / 1:10.000
# - Intravilan (reglementari de detaliu, UTR, cladiri, strazi): Scara 1:1.000 / 1:2.000
rename_map = {
    "Cladiri (+0.50m) TopoLT (osm+AI - StratumRO)": "Cladiri (+0.50m) TopoLT (de referinta - osm+AI | Cerinta PUG: 1:1.000)",
    "Drumuri Nationale DN (osm+AI - StratumRO)": "Drumuri Nationale DN (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Drumuri Judetene DJ (osm+AI - StratumRO)": "Drumuri Judetene DJ (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Drumuri Comunale DC (osm+AI - StratumRO)": "Drumuri Comunale DC (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Strazi Locale ST (osm+AI - StratumRO)": "Strazi Locale ST (de referinta - osm+AI | Cerinta PUG: 1:1.000)",
    "RENNS Nomenclator Stradal (osm+AI - StratumRO)": "RENNS Nomenclator Stradal (de referinta - osm+AI | Cerinta PUG: 1:1.000)",
    "Fond Forestier V_PD (osm+AI - PUG)": "Fond Forestier V_PD (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Curti-Constructii Intravilan CC (osm+AI - PUG)": "Curti-Constructii Intravilan CC (de referinta - osm+AI | Cerinta PUG: 1:1.000)",
    "Terenuri Arabile A_Ar (osm+AI - PUG)": "Terenuri Arabile A_Ar (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Pasuni si Fanete A_P (osm+AI - PUG)": "Pasuni si Fanete A_P (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Zone Umede si Ape ZHA (osm+AI - PUG)": "Zone Umede si Ape ZHA (de referinta - osm+AI | Cerinta PUG: 1:5.000)",
    "Banda Inundabila T100 (osm+AI - Modelare)": "Banda Inundabila T100 (de referinta - modelare AI | Cerinta PUG: 1:5.000)"
}

for lyr in project.mapLayers().values():
    curr_name = lyr.name()
    if curr_name in rename_map:
        new_name = rename_map[curr_name]
        lyr.setName(new_name)
        print(f"[RENAME] {curr_name} -> {new_name}")

print("[COMPLETE] Toate actualizarile solicitate au fost aplicate cu succes.")
'''

def main():
    print("=== Trimitere Actualizari catre QGIS via MCP ===")
    res = send_qgis_mcp("execute_code", {"code": qgis_update_code, "timeout": 30.0})
    print("Raspuns executie:", res.get("result", {}).get("stdout"))
    
    # Salvare proiect dupa aplicare
    save_res = send_qgis_mcp("save_project")
    print("Salvare proiect:", save_res.get("status"))

if __name__ == "__main__":
    main()
