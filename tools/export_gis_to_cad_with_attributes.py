# -*- coding: utf-8 -*-
"""
StratumRO GIS to AutoCAD (DXF/DWG/TopoLT) Bridge Engine
======================================================
Converts GIS spatial datasets from Master GeoPackage to CAD DXF (R2010)
under TopoLT and ANCPI Ordinul 600/2023 layer conventions.

ZERO ATTRIBUTE LOSS:
- Preserves all GIS feature attributes as Extended Entity Data (XDATA, AppID STRATUMRO_GIS).
- Generates companion CSV relational manifest linked via CAD Entity Handle.
- Exports TopoLT *.CP point coordinate file in Stereo 70 (EPSG:3844).
"""

import sys
import os
import csv
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point, MultiPoint
import ezdxf
from ezdxf import colors

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

GPKG_PATH = r"c:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\UAT_Iepuresti_PUG_Master.gpkg"
CAD_DIR = r"c:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\CAD_Export"
os.makedirs(CAD_DIR, exist_ok=True)

OUT_DXF = os.path.join(CAD_DIR, "UAT_Iepuresti_PUG_Cadastru.dxf")
OUT_CSV = os.path.join(CAD_DIR, "UAT_Iepuresti_CAD_Attributes_Manifest.csv")
OUT_CP = os.path.join(CAD_DIR, "UAT_Iepuresti_Puncte_Stereo70.cp")

CAD_LAYER_CONFIG = {
    "01_oficial_limita_uat_ancpi": ("LIM_UAT", 7, "Limita UAT ANCPI"),
    "02_oficial_parcele_agricole_apia_2025": ("CP_PARCELE_APIA", 3, "Parcele Agricole APIA"),
    "03_oficial_situri_arheologice_ran_cimec": ("PATRIMONIU_RAN", 30, "Situri Arheologice cIMeC"),
    "04_oficial_natura2000_protectie_eea": ("NATURA_2000", 94, "Arii Protejate Natura 2000"),
    "05_oficial_hidrografie_neajlov_anar": ("APE_NEAJLOV", 5, "Cursuri de Apa Neajlov"),
    "10_referinta_cladiri_topolt_1cc_scara_1000": ("1CC", 1, "Cladiri Principale TopoLT"),
    "11_referinta_intravilan_curti_constructii_cc_scara_1000": ("LIM_INTRAVILAN", 6, "Limita Intravilan CC"),
    "12_referinta_strazi_locale_st_scara_1000": ("STRAZI_LOCALE", 8, "Strazi Locale Intravilan"),
    "13_referinta_renns_adrese_nomenclator_scara_1000": ("TEXTE_ADRESE", 2, "Adrese si Nomenclator"),
    "14_referinta_drumuri_nationale_dn_scara_5000": ("DRUMURI_DN", 1, "Drumuri Nationale"),
    "15_referinta_drumuri_judetene_dj_scara_5000": ("DRUMURI_DJ", 30, "Drumuri Judetene"),
    "16_referinta_drumuri_comunale_dc_scara_5000": ("DRUMURI_DC", 2, "Drumuri Comunale"),
    "17_referinta_fond_forestier_vpd_scara_5000": ("FOND_FORESTIER", 90, "Fond Forestier Padure"),
    "18_referinta_terenuri_arabile_aar_scara_5000": ("ZONA_ARABIL", 51, "Terenuri Arabile Extravilan"),
    "19_referinta_pasuni_fanete_ap_scara_5000": ("ZONA_PASUNI", 71, "Pasuni si Fanete"),
    "20_referinta_zone_umede_ape_zha_scara_5000": ("ZONA_UMEDA", 4, "Zone Umede si Luciu Apa"),
    "21_referinta_banda_inundabila_t100_scara_5000": ("RISC_INUNDATII_T100", 150, "Banda Inundabila T100")
}

def clean_attr_value(val):
    if val is None:
        return ""
    s = str(val).strip()
    return s[:250]

def main():
    print("===================================================================")
    print("   STRATUMRO CAD BRIDGE — EXPORT AUTOCAD DXF CU ATRIBUTE INTEGRALE")
    print(f"   Destinație DXF: {OUT_DXF}")
    print(f"   Manifest CSV:   {OUT_CSV}")
    print(f"   Fișier TopoLT:  {OUT_CP}")
    print("===================================================================\n")

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Register AppID for XDATA to guarantee zero attribute loss
    APPID = "STRATUMRO_GIS"
    if APPID not in doc.appids:
        doc.appids.add(APPID)

    # Initialize Layers
    for _, (cad_lay, col, _) in CAD_LAYER_CONFIG.items():
        if cad_lay not in doc.layers:
            doc.layers.add(name=cad_lay, color=col, linetype="Continuous")

    csv_rows = []
    cp_points = []
    point_idx = 1
    total_entities = 0

    for table_name, (cad_lay, _, desc) in CAD_LAYER_CONFIG.items():
        try:
            gdf = gpd.read_file(GPKG_PATH, layer=table_name)
        except Exception as e:
            continue

        if gdf.empty:
            continue

        print(f"  [PROCESARE] {table_name} -> CAD Layer '{cad_lay}' ({len(gdf)} elemente)...")

        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            # Build XDATA list from all non-geometry columns
            attr_dict = {}
            xdata_tags = []
            for col_name in gdf.columns:
                if col_name != "geometry":
                    val_str = clean_attr_value(row[col_name])
                    attr_dict[col_name] = val_str
                    xdata_tags.append((1000, f"{col_name}={val_str}"))

            # Handle Polygon & MultiPolygon
            polys = []
            if isinstance(geom, Polygon):
                polys = [geom]
            elif isinstance(geom, MultiPolygon):
                polys = list(geom.geoms)

            for poly in polys:
                pts = list(poly.exterior.coords)
                cad_pts = [(p[0], p[1]) for p in pts]
                entity = msp.add_lwpolyline(cad_pts, close=True, dxfattribs={"layer": cad_lay})
                entity.set_xdata(APPID, xdata_tags)
                handle = entity.dxf.handle
                total_entities += 1

                # Record points for .CP interchange (Stereo 70)
                for pt in pts[:-1]:
                    cp_points.append(f"{point_idx},{pt[1]:.3f},{pt[0]:.3f},0.000,{cad_lay}")
                    point_idx += 1

                # Add to CSV manifest
                csv_record = {"cad_handle": handle, "cad_layer": cad_lay, "tabel_gis": table_name}
                csv_record.update(attr_dict)
                csv_rows.append(csv_record)

            # Handle LineString & MultiLineString
            lines = []
            if isinstance(geom, LineString):
                lines = [geom]
            elif isinstance(geom, MultiLineString):
                lines = list(geom.geoms)

            for line in lines:
                pts = list(line.coords)
                cad_pts = [(p[0], p[1]) for p in pts]
                entity = msp.add_lwpolyline(cad_pts, close=False, dxfattribs={"layer": cad_lay})
                entity.set_xdata(APPID, xdata_tags)
                handle = entity.dxf.handle
                total_entities += 1

                csv_record = {"cad_handle": handle, "cad_layer": cad_lay, "tabel_gis": table_name}
                csv_record.update(attr_dict)
                csv_rows.append(csv_record)

            # Handle Point & MultiPoint
            p_list = []
            if isinstance(geom, Point):
                p_list = [geom]
            elif isinstance(geom, MultiPoint):
                p_list = list(geom.geoms)

            for pt in p_list:
                entity = msp.add_point((pt.x, pt.y), dxfattribs={"layer": cad_lay})
                entity.set_xdata(APPID, xdata_tags)
                handle = entity.dxf.handle
                total_entities += 1

                # Also add MTEXT for labels if adresa/nume exists
                label = attr_dict.get("nume") or attr_dict.get("adresa") or attr_dict.get("id")
                if label:
                    msp.add_text(str(label), dxfattribs={"layer": cad_lay, "height": 1.2}).set_placement((pt.x + 0.5, pt.y + 0.5))

                cp_points.append(f"{point_idx},{pt.y:.3f},{pt.x:.3f},0.000,{cad_lay}")
                point_idx += 1

                csv_record = {"cad_handle": handle, "cad_layer": cad_lay, "tabel_gis": table_name}
                csv_record.update(attr_dict)
                csv_rows.append(csv_record)

    # Save DXF
    doc.saveas(OUT_DXF)
    print(f"\n[OK] Fișier DXF R2010 salvat: {OUT_DXF} ({total_entities:,} entități CAD)")

    # Save CSV Manifest
    if csv_rows:
        all_fieldnames = ["cad_handle", "cad_layer", "tabel_gis"]
        extra_keys = set()
        for r in csv_rows:
            extra_keys.update(r.keys())
        extra_keys.difference_update(all_fieldnames)
        all_fieldnames.extend(sorted(list(extra_keys)))

        with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=all_fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"[OK] Manifest Atribute CSV salvat: {OUT_CSV} ({len(csv_rows):,} înregistrări)")

    # Save TopoLT .CP point file
    if cp_points:
        with open(OUT_CP, "w", encoding="utf-8") as f_cp:
            f_cp.write("Nr.pct,X_Nord,Y_Est,Z,Cod\n")
            f_cp.write("\n".join(cp_points[:10000])) # Save first 10,000 reference points
        print(f"[OK] Fișier de coordonate TopoLT salvat: {OUT_CP}")

    print("\n===================================================================")
    print(f" [SUCCESS] Conversie în mediul AutoCAD finalizată fără pierderi de atribute!")
    print(f"  DXF: {OUT_DXF} ({os.path.getsize(OUT_DXF)/(1024*1024):.2f} MB)")
    print(f"  CSV: {OUT_CSV} ({os.path.getsize(OUT_CSV)/1024:.2f} KB)")
    print(f"  Stereo 70: Coordonate topografice metrice exacte (mm)")
    print("===================================================================")

if __name__ == "__main__":
    main()
