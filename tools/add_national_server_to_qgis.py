# -*- coding: utf-8 -*-
"""
Script pentru incarcarea si stilizarea straturilor din Serverul National
direct in proiectul QGIS activ, sub grupul dedicat '00_SERVER_NATIONAL_ROMANIA'.
"""

import sys
sys.path.insert(0, ".")
import json
from tools.test_layer_url_properties import send_qgis_mcp

qgis_code = '''
import os
import json
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsLayerTreeGroup,
    QgsSimpleMarkerSymbolLayer, QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer, QgsSymbol, QgsColorRampShader
)
from qgis.PyQt.QtGui import QColor

project = QgsProject.instance()
root = project.layerTreeRoot()

# 1. Creeaza sau obtine grupul 00_SERVER_NATIONAL_ROMANIA la varful arborelui
group_name = "00_SERVER_NATIONAL_ROMANIA"
group = root.findGroup(group_name)
if not group:
    group = root.insertGroup(0, group_name)

BASE_DIR = r"c:/Users/lefpa/Downloads/QGIS-AI/national_server"

layers_config = [
    {
        "name": "ANAR - Bazine Hidrografice Romania (15 bazine National)",
        "source": os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER", "BazineHidrografice.shp"),
        "type": "polygon",
        "color": QColor(166, 206, 227, 40),
        "stroke": QColor(31, 120, 180, 200),
        "width": 0.4,
        "visible": True
    },
    {
        "name": "ANCPI - Toate cele 3.186 UAT-uri din Romania (National)",
        "source": os.path.join(BASE_DIR, "01_ADMINISTRATIV_ANCPI", "Unitate_administrativa_UAT.shp"),
        "type": "polygon",
        "color": QColor(0, 0, 0, 0), # transparent fill
        "stroke": QColor(100, 100, 100, 180),
        "width": 0.25,
        "visible": True
    },
    {
        "name": "cIMeC - RAN Poligoane Situri Arheologice (16.484 situri National)",
        "source": os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg") + "|layername=02_RAN_National_Poligoane",
        "type": "polygon",
        "color": QColor(255, 127, 0, 90),
        "stroke": QColor(177, 89, 40, 240),
        "width": 0.35,
        "visible": True
    },
    {
        "name": "cIMeC - Arhiva Vasile Parvan (7.351 situri documentare)",
        "source": os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg") + "|layername=03_RAR_National_Arhiva_Parvan",
        "type": "point",
        "color": QColor(31, 120, 180, 220), # albastru ca pe cIMeC
        "stroke": QColor(8, 48, 107, 255),
        "size": 1.6,
        "visible": True
    },
    {
        "name": "cIMeC - RAN Puncte Situri Arheologice (28.988 situri clasate)",
        "source": os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg") + "|layername=01_RAN_National_Puncte",
        "type": "point",
        "color": QColor(227, 26, 28, 230), # rosu aprins ca pe cIMeC
        "stroke": QColor(128, 0, 0, 255),
        "size": 1.6,
        "visible": True
    }
]

# Curata eventualele straturi vechi din grup pentru a nu avea duplicate
for child in list(group.children()):
    if hasattr(child, "layer"):
        project.removeMapLayer(child.layer().id())

loaded_layers = []

for cfg in layers_config:
    src = cfg["source"]
    name = cfg["name"]
    
    lyr = QgsVectorLayer(src, name, "ogr")
    if not lyr.isValid():
        continue
        
    # Stilizare
    if cfg["type"] == "point":
        sym = QgsSymbol.defaultSymbol(lyr.geometryType())
        sym.setColor(cfg["color"])
        sym.setSize(cfg["size"])
        if sym.symbolLayer(0):
            sym.symbolLayer(0).setStrokeColor(cfg["stroke"])
            sym.symbolLayer(0).setStrokeWidth(0.2)
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    elif cfg["type"] == "polygon":
        sym = QgsSymbol.defaultSymbol(lyr.geometryType())
        sym.setColor(cfg["color"])
        if sym.symbolLayer(0):
            sym.symbolLayer(0).setStrokeColor(cfg["stroke"])
            sym.symbolLayer(0).setStrokeWidth(cfg["width"])
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        
    # Corectie CRS pentru UAT daca prj este generic
    if "3.186 UAT" in name and not lyr.crs().isValid():
        from qgis.core import QgsCoordinateReferenceSystem
        lyr.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

    # Adaugare in proiect si in grupul 00_SERVER_NATIONAL_ROMANIA
    project.addMapLayer(lyr, False)
    group.addLayer(lyr)
    
    # Setare vizibilitate
    node = group.findLayer(lyr.id())
    if node:
        node.setItemVisibilityChecked(cfg["visible"])
        
    loaded_layers.append({
        "name": name,
        "count": lyr.featureCount(),
        "crs": lyr.crs().authid()
    })

# Seteaza CRS proiect la EPSG:3844 sau EPSG:4326 pentru vizualizare nationala perfecta
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# Zoom canvas la toata Romania
uat_nat = [l for l in project.mapLayers().values() if "3.186 UAT" in l.name()]
if uat_nat and hasattr(iface, "mapCanvas"):
    ext = uat_nat[0].extent()
    ext.scale(1.10)
    iface.mapCanvas().setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
    iface.mapCanvas().setExtent(ext)
    iface.mapCanvas().refresh()

project.write()

print("NATIONAL_LAYERS_LOADED:" + json.dumps({
    "group": group_name,
    "count": len(loaded_layers),
    "layers": loaded_layers
}))
'''

if __name__ == "__main__":
    resp = send_qgis_mcp("execute_code", {"code": qgis_code})
    print(json.dumps(resp, indent=2))
