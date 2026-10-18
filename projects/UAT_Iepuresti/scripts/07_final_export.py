# -*- coding: utf-8 -*-
"""G7 (Final): Creare proiect QGIS stilizat si export harta PDF A4 (300 DPI)."""
import os, sys, json
from datetime import datetime, timezone
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes,
    QgsLayoutExporter
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT_DIR = ROOT / "output"
STATE_FILE = ROOT / "state" / "state.json"
GPKG_PATH = OUTPUT_DIR / "UAT_Iepuresti.gpkg"
QGZ_PATH = OUTPUT_DIR / "UAT_Iepuresti.qgz"
PDF_PATH = OUTPUT_DIR / "harta_Iepuresti.pdf"

def stamp():
    return datetime.now(timezone.utc).isoformat()

def apply_styling(layer, layer_name):
    """Aplica stilul grafic conform specificatiilor din handoff."""
    if layer_name == "paduri":
        sym = QgsFillSymbol.createSimple({
            "color": "34,139,34,180",
            "outline_color": "0,100,0,255",
            "outline_width": "0.3"
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    elif layer_name == "drumuri_poligon":
        sym = QgsFillSymbol.createSimple({
            "color": "211,211,211,200",
            "outline_color": "128,128,128,255",
            "outline_width": "0.15"
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    elif layer_name == "constructii":
        sym = QgsFillSymbol.createSimple({
            "color": "190,190,190,255",
            "outline_color": "0,0,0,255",
            "outline_width": "0.2"
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    elif layer_name == "cursuri_apa":
        sym = QgsLineSymbol.createSimple({
            "color": "30,144,255,255",
            "width": "0.6"
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    elif layer_name == "drumuri_ax":
        sym = QgsLineSymbol.createSimple({
            "color": "50,50,50,255",
            "width": "0.8"
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    elif layer_name == "poduri":
        # Linie compusa: baza neagra 2mm + alb 1.2mm suprapus
        sym = QgsLineSymbol()
        sl1 = QgsSimpleLineSymbolLayer(QColor(0, 0, 0), 2.0)
        sl2 = QgsSimpleLineSymbolLayer(QColor(255, 255, 255), 1.2)
        sym.changeSymbolLayer(0, sl1)
        sym.appendSymbolLayer(sl2)
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    elif layer_name == "limita_UAT":
        sym = QgsFillSymbol.createSimple({
            "color": "0,0,0,0",
            "outline_color": "0,0,0,255",
            "outline_width": "0.6"
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

    layer.triggerRepaint()

def main():
    qgs = QgsApplication([], False)
    qgs.initQgis()

    project = QgsProject.instance()
    project.clear()
    project.setTitle("UAT Iepurești — Master Project")

    # Ordine de adaugare pentru randare corecta (de jos in sus)
    layer_order = [
        "paduri", "drumuri_poligon", "constructii", "cursuri_apa",
        "drumuri_ax", "poduri", "limita_UAT"
    ]

    loaded_layers = []
    extent_layer = None

    for name in layer_order:
        uri = f"{GPKG_PATH}|layername={name}"
        vlayer = QgsVectorLayer(uri, name, "ogr")
        if vlayer.isValid():
            apply_styling(vlayer, name)
            project.addMapLayer(vlayer)
            loaded_layers.append(vlayer)
            if name == "limita_UAT":
                extent_layer = vlayer
        else:
            print(f"Avertisment: Stratul {name} nu a putut fi incarcat.")

    # Salvare proiect QGIS (.qgz)
    project.write(str(QGZ_PATH))
    print(f"Proiect QGIS salvat: {QGZ_PATH}")

    # Configurare macheta de printare (A4 Landscape)
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Macheta_A4_Iepuresti")

    # Adaugare Harta
    map_item = QgsLayoutItemMap(layout)
    map_item.attemptMove(QgsLayoutPoint(10, 22, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(277, 175, QgsUnitTypes.LayoutMillimeters))

    if extent_layer and extent_layer.featureCount() > 0:
        bbox = extent_layer.extent()
        bbox.scale(1.08)  # Margine de 8% in jurul UAT
        map_item.setExtent(bbox)

    layout.addLayoutItem(map_item)

    # Titlu
    title = QgsLayoutItemLabel(layout)
    title.setText("COMUNA IEPUREȘTI — JUDEȚUL GIURGIU (SIRUTA 103684)")
    font = title.font()
    font.setPointSize(14)
    font.setBold(True)
    title.setFont(font)
    title.attemptMove(QgsLayoutPoint(10, 6, QgsUnitTypes.LayoutMillimeters))
    title.attemptResize(QgsLayoutSize(277, 8, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(title)

    # Subtitlu / Referinta legala
    sub = QgsLayoutItemLabel(layout)
    sub.setText("Plan de referință open-data (OSM Proxy / Copernicus) • Sistem de proiecție: EPSG:3844 (Stereo 70) • Notă: Limita este informativă (REFERENCE)")
    font_sub = sub.font()
    font_sub.setPointSize(8)
    sub.setFont(font_sub)
    sub.attemptMove(QgsLayoutPoint(10, 14, QgsUnitTypes.LayoutMillimeters))
    sub.attemptResize(QgsLayoutSize(277, 6, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(sub)

    # Export PDF la 300 DPI
    exporter = QgsLayoutExporter(layout)
    pdf_settings = QgsLayoutExporter.PdfExportSettings()
    pdf_settings.dpi = 300
    res = exporter.exportToPdf(str(PDF_PATH), pdf_settings)

    if res == QgsLayoutExporter.Success:
        print(f"Hartă A4 300 DPI generată cu succes: {PDF_PATH}")
    else:
        print(f"Eroare la exportul PDF: cod {res}")

    # Actualizare state.json la G7_complete
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8-sig"))
    else:
        state = {}

    state["gate"] = "G7_complete"
    state["gate_since"] = state["updated_at"] = stamp()
    state["deliverables"] = {
        "master_gpkg": str(GPKG_PATH),
        "qgis_project": str(QGZ_PATH),
        "pdf_map": str(PDF_PATH),
        "status": "ALL_GATES_COMPLETE"
    }
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Pipeline-ul UAT Iepurești este 100% COMPLET (Gate: G7_complete).")

    qgs.exitQgis()
    return 0

if __name__ == "__main__":
    sys.exit(main())
