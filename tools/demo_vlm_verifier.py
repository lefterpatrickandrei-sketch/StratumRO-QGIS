# -*- coding: utf-8 -*-
"""
StratumRO — Demonstration script for VLM Verifier.
Audits sample building masks created by SAM from the USAMV Cluj pilot area.
"""

import os
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
import geopandas as gpd

sys.path.insert(0, os.path.abspath('.'))

from stratum_ro.ai.vlm_verifier import VLMVerifier

ORTHO_VRT = "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
NDSM_TIF = "workspace/output/ndsm_stereo70.tif"
GPKG = "workspace/output/cladiri_stereo70.gpkg"
LAYER = "STAGE_1_RAW_CONTOUR"


def run_demo():
    print("=" * 75)
    print("  STRATUM-RO: DEMO VLM VERIFIER PENTRU MĂȘTI SAM (AUDIT SEMANTIC)")
    print("=" * 75)

    verifier = VLMVerifier(fallback_to_heuristic=True)

    print(f"\n[+] Citire poligoane brute SAM din: {GPKG} (Strat: {LAYER})")
    gdf = gpd.read_file(GPKG, layer=LAYER)
    print(f"[+] Total clădiri brute detectate de SAM: {len(gdf)}")

    # Sortăm după arie pentru a alege clădiri de mărimi variate:
    # 1 mare (Aulă/Corp universitar), 1 medie (casă), 1 mică (anexă), 1 foarte mică (posibil zgomot/copac)
    gdf["area"] = gdf.geometry.area
    sample_indices = [
        gdf["area"].idxmax(),                          # Cea mai mare clădire (> 2000 mp)
        gdf[gdf["area"].between(150, 250)].index[0],   # Clădire rezidențială medie (150-250 mp)
        gdf[gdf["area"].between(20, 45)].index[0],     # Anexă gospodărească (20-45 mp)
        gdf["area"].idxmin(),                          # Cea mai mică amprentă detectată (16 mp)
    ]

    samples = gdf.loc[sample_indices]

    print("\n" + "-" * 75)
    print("  REZULTATE AUDIT VLM (SEMANTIC & CADASTRAL ANCPI ORDINUL 600/2023)")
    print("-" * 75)

    for i, (idx, row) in enumerate(samples.iterrows(), 1):
        geom = row.geometry
        bldg_id = f"SAM_CANDIDATE_{idx:04d}"

        res = verifier.verify_building(
            polygon=geom,
            ortho_path=ORTHO_VRT,
            building_id=bldg_id
        )

        badge = "🟢 APROBAT" if res.verdict == "APPROVED" else ("🟡 REVIZUIRE" if res.verdict == "REVIEW_NEEDED" else "🔴 RESPINS")
        print(f"\n[{i}/4] ID: {res.building_id}")
        print(f"     Status VLM:        {badge} (Verdict: {res.verdict})")
        print(f"     Cod ANCPI:         {res.ancpi_code} ({res.typology})")
        print(f"     Încredere:         {res.confidence * 100:.1f}%")
        print(f"     Suprafață:         {geom.area:.1f} mp (Perimetru: {geom.length:.1f} m)")
        print(f"     Tip Acoperiș:      {res.roof_type}")
        print(f"     Streașină Vizibilă: {'DA' if res.eave_visible else 'NU'}")
        print(f"     Motivație Geodezică: {res.reasoning}")
        print(f"     Provider Folosit:  {res.provider_used}")

    print("\n" + "=" * 75)
    print("  [+] Demonstrație finalizată cu succes!")
    print("=" * 75)


if __name__ == "__main__":
    run_demo()
