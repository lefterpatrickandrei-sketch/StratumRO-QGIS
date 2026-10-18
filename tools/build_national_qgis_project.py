# -*- coding: utf-8 -*-
"""
StratumRO National QGIS Project Builder
=======================================
Generates the Master QGIS Project 'ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs'
in Stereo 70 (EPSG:3844) referencing all authoritative national datasets
structured for instant navigation in the QGIS Browser panel (/browser).

Run with QGIS Python:
  & "C:\Program Files\QGIS 3.40.0\bin\python-qgis.bat" tools/build_national_qgis_project.py
"""

import os
import sys

# Initialize QGIS Core
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsLayerTreeGroup,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSymbol
)
from qgis.PyQt.QtGui import QColor

BASE_DIR = r"c:/Users/lefpa/Downloads/QGIS-AI/national_server"
PROJECT_FILE = os.path.join(BASE_DIR, "ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs")

def main():
    print(f"=== Creare Proiect QGIS Master National: {PROJECT_FILE} ===")
    
    # Initialize QGIS Application without GUI
    qgs = QgsApplication([], False)
    qgs.initQgis()

    try:
        project = QgsProject.instance()
        project.clear()
        project.setTitle("StratumRO — Depozit Național de Date Oficiale (România)")

        # Set Project CRS to Stereo 70 (EPSG:3844)
        crs = QgsCoordinateReferenceSystem("EPSG:3844")
        project.setCrs(crs)

        root = project.layerTreeRoot()
        root.clear()

        # Definition of Groups and Layers
        groups_def = [
            ("01_ADMINISTRATIV_SI_CADASTRU", [
                {
                    "name": "ANCPI — Toate cele 3.186 UAT-uri din România",
                    "path": os.path.join(BASE_DIR, "01_ADMINISTRATIV_ANCPI", "Unitate_administrativa_UAT.shp"),
                    "type": "vector",
                    "geom": "polygon",
                    "fill": QColor(0, 0, 0, 0),
                    "stroke": QColor(74, 85, 104, 220),
                    "width": 0.35,
                    "visible": True
                },
                {
                    "name": "APIA — Parcele de Referință Blocuri Fizice 2025 (1.54M parcele)",
                    "path": "/vsizip/" + os.path.join(BASE_DIR, "03_AGRICOL_APIA_LPIS_2025", "blocuri_fizice_2025_Romania_Complet.zip"),
                    "type": "vector",
                    "geom": "polygon",
                    "fill": QColor(246, 224, 94, 40),
                    "stroke": QColor(56, 161, 105, 180),
                    "width": 0.25,
                    "visible": False
                }
            ]),
            ("02_PATRIMONIU_ARHEOLOGIC_RAN", [
                {
                    "name": "cIMeC — RAN Poligoane Situri Arheologice (16.484 situri)",
                    "path": os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg") + "|layername=02_RAN_National_Poligoane",
                    "type": "vector",
                    "geom": "polygon",
                    "fill": QColor(237, 137, 54, 90),
                    "stroke": QColor(192, 86, 33, 240),
                    "width": 0.4,
                    "visible": True
                },
                {
                    "name": "cIMeC — RAN Puncte Situri Clasate (28.988 situri)",
                    "path": os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg") + "|layername=01_RAN_National_Puncte",
                    "type": "vector",
                    "geom": "point",
                    "color": QColor(229, 62, 62, 230),
                    "stroke": QColor(155, 44, 44, 255),
                    "size": 1.6,
                    "visible": True
                },
                {
                    "name": "cIMeC — RAR Arhiva Vasile Pârvan (7.351 situri)",
                    "path": os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg") + "|layername=03_RAR_National_Arhiva_Parvan",
                    "type": "vector",
                    "geom": "point",
                    "color": QColor(49, 130, 206, 230),
                    "stroke": QColor(44, 82, 130, 255),
                    "size": 1.5,
                    "visible": True
                }
            ]),
            ("03_HIDROGRAFIE_SI_INUNDATII", [
                {
                    "name": "ANAR — Cursuri de Apă / Râuri (13.078 segmente)",
                    "path": os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER", "CursuriApaRauriSegmente.shp"),
                    "type": "vector",
                    "geom": "line",
                    "color": QColor(49, 130, 206, 240),
                    "width": 0.4,
                    "visible": True
                },
                {
                    "name": "ANAR — Bazine Hidrografice Naționale (15 bazine)",
                    "path": os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER", "BazineHidrografice.shp"),
                    "type": "vector",
                    "geom": "polygon",
                    "fill": QColor(190, 227, 248, 45),
                    "stroke": QColor(43, 108, 176, 220),
                    "width": 0.5,
                    "visible": True
                },
                {
                    "name": "ANAR — Diguri Naționale de Apărare (3.063 diguri)",
                    "path": os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER", "Diguri.shp"),
                    "type": "vector",
                    "geom": "line",
                    "color": QColor(128, 90, 213, 230),
                    "width": 0.45,
                    "visible": True
                },
                {
                    "name": "ANAR — Hazard Inundații RO-FLOODS HHI T100 (WMS)",
                    "path": "contextualWMSLegend=0&crs=EPSG:3844&dpiMode=7&featureCount=10&format=image/png&layers=rofloods:HHI_T100_extensie&styles=&url=https://inundatii.ro/geoserver/wms",
                    "type": "raster",
                    "visible": False
                }
            ]),
            ("04_MEDIU_SI_ARII_PROTEJATE", [
                {
                    "name": "EEA — Natura 2000 Situri Comunitare (GeoJSON)",
                    "path": os.path.join(BASE_DIR, "05_MEDIU_NATURA2000_EEA", "natura2000_eea_referinta.geojson"),
                    "type": "vector",
                    "geom": "polygon",
                    "fill": QColor(72, 187, 120, 80),
                    "stroke": QColor(34, 84, 61, 230),
                    "width": 0.4,
                    "visible": True
                },
                {
                    "name": "EEA — Natura 2000 Sites Discomap (WMS)",
                    "path": "contextualWMSLegend=0&crs=EPSG:3844&dpiMode=7&featureCount=10&format=image/png&layers=1&styles=&url=https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer",
                    "type": "raster",
                    "visible": False
                }
            ]),
            ("05_INFRASTRUCTURA_TRANSPORT", [
                {
                    "name": "CNAIR / MMAP — Drumuri Principale România (Autostrăzi, DN, DJ)",
                    "path": os.path.join(BASE_DIR, "08_TRANSPORT_CNAIR_CFR", "MajorRoads_Romania_CNAIR_MMAP.gpkg"),
                    "type": "vector",
                    "geom": "line",
                    "color": QColor(197, 48, 48, 240),
                    "width": 0.6,
                    "visible": True
                },
                {
                    "name": "CFR / MMAP — Căi Ferate Naționale România",
                    "path": os.path.join(BASE_DIR, "08_TRANSPORT_CNAIR_CFR", "MajorRailways_Romania_CFR_MMAP.gpkg"),
                    "type": "vector",
                    "geom": "line",
                    "color": QColor(26, 32, 44, 255),
                    "width": 0.5,
                    "visible": True
                }
            ]),
            ("06_GEOLOGIE_IGR", [
                {
                    "name": "IGR — Harta Geologică a României 1:1.000.000",
                    "path": os.path.join(BASE_DIR, "11_GEOLOGIE_IGR", "Geologie_1M_pr.shp"),
                    "type": "vector",
                    "geom": "polygon",
                    "fill": QColor(226, 232, 240, 100),
                    "stroke": QColor(113, 128, 150, 180),
                    "width": 0.25,
                    "visible": False
                }
            ]),
            ("07_FOND_FORESTIER_SI_LAND_COVER", [
                {
                    "name": "Copernicus — Tree Cover Density / Păduri (WMS)",
                    "path": "contextualWMSLegend=0&crs=EPSG:3844&dpiMode=7&featureCount=10&format=image/png&layers=TCD_2018_10m&styles=&url=https://image.discomap.eea.europa.eu/arcgis/services/GioLandPublic/TreeCoverDensity_2018/ImageServer/WMSServer",
                    "type": "raster",
                    "visible": False
                },
                {
                    "name": "Copernicus — Corine Land Cover (CLC 2018 WMS)",
                    "path": "contextualWMSLegend=0&crs=EPSG:3844&dpiMode=7&featureCount=10&format=image/png&layers=CORINE_Land_Cover_2018&styles=&url=https://image.discomap.eea.europa.eu/arcgis/services/Corine/CLC2018_WM/MapServer/WMSServer",
                    "type": "raster",
                    "visible": False
                }
            ]),
            ("08_ORTOFOTOPLAN_SI_SATELIT", [
                {
                    "name": "ANCPI — Ortofotoplan Național de Înaltă Rezoluție (WMS)",
                    "path": "contextualWMSLegend=0&crs=EPSG:3844&dpiMode=7&featureCount=10&format=image/png&layers=INSPIRE:Orthophoto&styles=&url=https://geoportal.ancpi.ro/arcgis/services/INSPIRE/Orthophoto/ImageServer/WMSServer",
                    "type": "raster",
                    "visible": True
                },
                {
                    "name": "OpenStreetMap Standard (XYZ)",
                    "path": "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0",
                    "type": "raster",
                    "visible": False
                },
                {
                    "name": "Esri World Imagery (XYZ)",
                    "path": "type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}&zmax=19&zmin=0",
                    "type": "raster",
                    "visible": False
                }
            ])
        ]

        total_layers = 0

        for grp_name, layers in groups_def:
            grp = root.addGroup(grp_name)
            for lcfg in layers:
                name = lcfg["name"]
                path = lcfg["path"]
                ltype = lcfg["type"]
                visible = lcfg.get("visible", True)

                # Check file existence for local paths
                if not path.startswith("http") and not path.startswith("contextual") and not path.startswith("type="):
                    check_path = path.replace("/vsizip/", "").split("|")[0]
                    if not os.path.exists(check_path):
                        print(f"  [SKIP] Strat indisponibil local: {name} ({check_path})")
                        continue

                if ltype == "vector":
                    lyr = QgsVectorLayer(path, name, "ogr")
                    if not lyr.isValid():
                        print(f"  [ERR] Nu s-a putut incarca vectorul: {name}")
                        continue

                    # Apply Styling
                    geom = lcfg.get("geom")
                    if geom == "polygon":
                        sym = QgsSymbol.defaultSymbol(lyr.geometryType())
                        sym_layer = QgsSimpleFillSymbolLayer()
                        sym_layer.setFillColor(lcfg["fill"])
                        sym_layer.setStrokeColor(lcfg["stroke"])
                        sym_layer.setStrokeWidth(lcfg["width"])
                        sym.changeSymbolLayer(0, sym_layer)
                        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
                    elif geom == "line":
                        sym = QgsSymbol.defaultSymbol(lyr.geometryType())
                        sym_layer = QgsSimpleLineSymbolLayer()
                        sym_layer.setColor(lcfg["color"])
                        sym_layer.setWidth(lcfg["width"])
                        sym.changeSymbolLayer(0, sym_layer)
                        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
                    elif geom == "point":
                        sym = QgsSymbol.defaultSymbol(lyr.geometryType())
                        sym_layer = QgsSimpleMarkerSymbolLayer()
                        sym_layer.setColor(lcfg["color"])
                        sym_layer.setStrokeColor(lcfg["stroke"])
                        sym_layer.setSize(lcfg["size"])
                        sym.changeSymbolLayer(0, sym_layer)
                        lyr.setRenderer(QgsSingleSymbolRenderer(sym))

                    project.addMapLayer(lyr, False)
                    node = grp.addLayer(lyr)
                    node.setItemVisibilityChecked(visible)
                    total_layers += 1
                    print(f"  [OK] Adaugat Vector: {name}")

                elif ltype == "raster":
                    provider = "wms"
                    lyr = QgsRasterLayer(path, name, provider)
                    if lyr.isValid():
                        project.addMapLayer(lyr, False)
                        node = grp.addLayer(lyr)
                        node.setItemVisibilityChecked(visible)
                        total_layers += 1
                        print(f"  [OK] Adaugat Raster/Service: {name}")
                    else:
                        print(f"  [WARN] Rasterul/Serviciul nu a raspuns la initializare: {name}")

        # Save Project
        success = project.write(PROJECT_FILE)
        if success:
            print(f"\n[SUCCESS] Proiectul QGIS Master National a fost salvat cu succes!")
            print(f"  Locatie: {PROJECT_FILE}")
            print(f"  Total straturi integrate: {total_layers}")
            print(f"  Sistem de Coordonate: EPSG:3844 Stereo 70")
        else:
            print(f"\n[ERR] Nu s-a putut salva fisierul de proiect {PROJECT_FILE}")

    finally:
        qgs.exitQgis()

if __name__ == "__main__":
    main()
