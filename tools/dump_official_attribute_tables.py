# -*- coding: utf-8 -*-
"""
Script de extragere si salvare a tabelelor de atribute pentru toate straturile oficiale
din GeoPackage folosind sqlite3 nativ, pentru auditul independent read-only.
"""

import os
import sys
import json
import sqlite3

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"c:\Users\lefpa\Downloads\QGIS-AI"
GPKG_OFICIAL = os.path.join(ROOT, "projects", "UAT_Iepuresti", "output", "UAT_Iepuresti_Oficial.gpkg")
OUT_JSON = os.path.join(ROOT, "projects", "UAT_Iepuresti", "output", "audit_tabele_atribute_oficiale.json")

def dump_attributes_sqlite():
    conn = sqlite3.connect(GPKG_OFICIAL)
    cursor = conn.cursor()

    # Gasire straturi
    cursor.execute("SELECT table_name, data_type, srs_id FROM gpkg_contents WHERE data_type='features'")
    tables = cursor.fetchall()
    
    report = {
        "geopackage": GPKG_OFICIAL,
        "official_layers": {}
    }

    official_tables = [
        "IEP_00_limita_UAT_ANCPI_oficial",
        "IEP_01_situri_arheologice_RAN",
        "IEP_02_natura2000_eea",
        "IEP_04_rowater_cursuri_apa",
        "IEP_06_apia_blocuri_fizice_2025"
    ]

    for t_name, d_type, srs_id in tables:
        if t_name not in official_tables:
            continue

        # Info coloane
        cursor.execute(f"PRAGMA table_info('{t_name}')")
        cols = cursor.fetchall()
        columns = []
        col_names = []
        for c in cols:
            cid, name, col_type, notnull, dflt_value, pk = c
            if name.lower() != "geom":
                columns.append({
                    "cid": cid,
                    "name": name,
                    "type": col_type,
                    "notnull": bool(notnull),
                    "is_pk": bool(pk)
                })
                col_names.append(name)
        
        # Count
        cursor.execute(f"SELECT count(*) FROM '{t_name}'")
        count = cursor.fetchone()[0]

        # Select all attributes (excluding raw BLOB geom for clean reading)
        cols_sql = ", ".join([f"[{c}]" for c in col_names])
        cursor.execute(f"SELECT {cols_sql} FROM '{t_name}'")
        rows = cursor.fetchall()
        
        features = []
        for r in rows:
            feat_dict = dict(zip(col_names, r))
            features.append(feat_dict)

        report["official_layers"][t_name] = {
            "table_name": t_name,
            "srs_id": srs_id,
            "crs": "EPSG:3844" if srs_id in (3844, 1) else f"SRS_ID:{srs_id}",
            "feature_count": count,
            "column_count": len(columns),
            "columns_schema": columns,
            "sample_rows": features[:20],
            "total_rows_extracted": len(features)
        }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    conn.close()
    print(f"[OK] Audit tabele atribute generat cu succes in: {OUT_JSON}")
    for k, v in report["official_layers"].items():
        print(f"  - Strat: {k} | Entitati: {v['feature_count']} | Coloane: {v['column_count']} | CRS: {v['crs']}")

if __name__ == "__main__":
    dump_attributes_sqlite()
