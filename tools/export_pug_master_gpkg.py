# -*- coding: utf-8 -*-
"""
StratumRO Master GeoPackage Consolidation Engine
================================================
Consolidates all official statutory layers and PUG reference zoning layers
into an authoritative SQLite GeoPackage (*.gpkg) in Stereo 70 (EPSG:3844).
Preserves full attribute fidelity, spatial indices (R-Tree), and field types.
"""

import sys
import os
sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
from tools.test_layer_url_properties import send_qgis_mcp

export_code = '''
import os
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem,
    QgsVectorFileWriter, QgsCoordinateTransformContext
)

project = QgsProject.instance()
crs_stereo70 = QgsCoordinateReferenceSystem("EPSG:3844")

OUT_DIR = r"c:/Users/lefpa/Downloads/QGIS-AI/projects/UAT_Iepuresti"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_GPKG = os.path.join(OUT_DIR, "UAT_Iepuresti_PUG_Master.gpkg")

# Remove previous gpkg if exists to build clean database
if os.path.exists(OUT_GPKG):
    try:
        os.remove(OUT_GPKG)
        print(f"[CLEAN] Sters GPKG anterior: {OUT_GPKG}")
    except Exception as e:
        print(f"[WARN] Nu s-a putut sterge GPKG vechi: {e}")

layers = project.mapLayers().values()
exported_count = 0

# Mapping layer names to clean, standardized GPKG table names
table_mapping = {
    # 01 OFICIAL STAT
    "Limita UAT Iepuresti (oficial - ANCPI)": "01_limita_uat_oficial_ancpi",
    "APIA Blocuri Fizice 2025 (oficial - APIA)": "02_parcele_agricole_oficial_apia",
    "Situri Arheologice RAN (oficial - INP cIMeC)": "03_situri_arheologice_oficial_cimec",
    "Natura 2000 Situri Comunitare (oficial - EEA)": "04_natura2000_oficial_eea",
    "Cursuri de Apa Neajlov (oficial - ANAR ROWATER)": "05_hidrografie_neajlov_oficial_anar",
    
    # 02 MODELE PUG & URBANISM (DE REFERINTA)
    "Cladiri (+0.50m) TopoLT (de referinta - osm+AI | Cerinta PUG: 1:1.000)": "10_cladiri_existente_1cc_topolt",
    "Curti-Constructii Intravilan CC (de referinta - osm+AI | Cerinta PUG: 1:1.000)": "11_intravilan_curti_constructii_cc",
    "Strazi Locale ST (de referinta - osm+AI | Cerinta PUG: 1:1.000)": "12_strazi_locale_intravilan_st",
    "RENNS Nomenclator Stradal (de referinta - osm+AI | Cerinta PUG: 1:1.000)": "13_adrese_renns_nomenclator",
    "Drumuri Nationale DN (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "14_drumuri_nationale_dn",
    "Drumuri Judetene DJ (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "15_drumuri_judetene_dj",
    "Drumuri Comunale DC (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "16_drumuri_comunale_dc",
    "Fond Forestier V_PD (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "17_fond_forestier_padure_vpd",
    "Terenuri Arabile A_Ar (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "18_terenuri_arabile_extravilan_aar",
    "Pasuni si Fanete A_P (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "19_pasuni_fanete_ap",
    "Zone Umede si Ape ZHA (de referinta - osm+AI | Cerinta PUG: 1:5.000)": "20_zone_umede_ape_zha",
    "Banda Inundabila T100 (de referinta - modelare AI | Cerinta PUG: 1:5.000)": "21_banda_inundabila_t100",

    # 00 NATIONAL TRANSPORT
    "CNAIR / MMAP — Drumuri Principale Romania (oficial - CNAIR / MMAP)": "08_cnair_drumuri_principale_national",
    "CFR / MMAP — Cai Ferate Nationale Romania (oficial - CFR / MMAP)": "09_cfr_cai_ferate_national"
}

opts = QgsVectorFileWriter.SaveVectorOptions()
opts.driverName = "GPKG"
opts.fileEncoding = "UTF-8"
opts.destCRS = crs_stereo70
transform_context = project.transformContext()

for lyr in layers:
    if not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
        continue
    name = lyr.name()
    if name not in table_mapping:
        continue
    
    table_name = table_mapping[name]
    opts.layerName = table_name
    opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(OUT_GPKG) else QgsVectorFileWriter.CreateOrOverwriteFile
    
    writer, error = QgsVectorFileWriter.writeAsVectorFormatV3(
        lyr,
        OUT_GPKG,
        transform_context,
        opts
    )
    if writer == QgsVectorFileWriter.NoError:
        exported_count += 1
        print(f"  [EXPORTAT OK] {table_name} ({lyr.featureCount()} entitati)")
    else:
        print(f"  [ERR] {name} -> Eroare: {error}")

print(f"\\n[SUCCESS] Master GeoPackage creat la: {OUT_GPKG}")
print(f"Total tabele vectoriale integrate: {exported_count}")
'''

def main():
    print("=== Consolidare Master GeoPackage (GPKG) UAT Iepurești ===")
    res = send_qgis_mcp("execute_code", {"code": export_code, "timeout": 60.0})
    print("Rezultat export:")
    print(res.get("result", {}).get("stdout"))

if __name__ == "__main__":
    main()
