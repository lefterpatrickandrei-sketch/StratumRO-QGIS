# -*- coding: utf-8 -*-
"""
StratumRO — Lot 3 Canonical Cadastral Regularization & Visual Multi-Factor Verification
====================================================================================
1. Loads 20 candidate features from selected_v3/lot3_repaired.gpkg.
2. Applies orthogonalize_cad() from stratum_ro.core.geometry.regularizer.
   - Retains authentic 90-deg angles and complex wings/courtyards (no forced MRR box).
   - Regularizes jagged pixel staircases to 90 degrees.
   - Generates parametric eave retraction (-0.40m mitre join) for ground footprint.
3. Exports canonical layers to selected_v4_orthogonal/lot3_orthogonal.gpkg in EPSG:3844.
4. Generates regularization_report.json and prints factual metric table.
5. Generates high-res visual comparison grid over 5cm orthophotos:
   lot3_before_after_ortho90.png.
6. Integrates LOT3_ORTHO90_20261018_PENDING_REVIEW group into shared QGIS project.
"""
from pathlib import Path
import sys
import os
import json
import shutil
import math
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
import rasterio
from rasterio.windows import from_bounds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import stratum_ro.core.geometry.regularizer as reg

SRC_GPKG = ROOT / 'workspace/reviews/lot3_repairs_20261017/selected_v3/lot3_repaired.gpkg'
OUT_DIR = ROOT / 'workspace/reviews/lot3_repairs_20261017/selected_v4_orthogonal'
OUT_GPKG = OUT_DIR / 'lot3_orthogonal.gpkg'
COVERS_DIR = ROOT / 'workspace/reviews/lot3_repairs_20261017/covers'
T17_COVER = ROOT / 'workspace/reviews/lot3_continuation_20261017/covers/T17_expanded_ortho.tif'
PROJECT_PATH = ROOT / 'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Incarcare candidati Lot 3: {SRC_GPKG}")
    gdf_raw = gpd.read_file(SRC_GPKG, layer='REPAIRED_ROOF_CANDIDATES')
    print(f"[*] Corpuri gasite: {len(gdf_raw)}")

    roof_records = []
    sol_records = []
    before_records = []
    report_rows = []

    print("\n" + "=" * 105)
    print(f"{'BODY_ID':<8} {'V_IN':>6} -> {'V_OUT':>6} | {'ORTHO_IN':>8} -> {'ORTHO_OUT':>8} | {'HAUSDORFF':>10} | {'AREA_IN':>9} -> {'AREA_OUT':>9} | {'DIFF_%':>7}")
    print("=" * 105)

    for idx, row in gdf_raw.iterrows():
        poly = row.geometry
        bid = str(row.get('body_id') or row.get('test_id'))
        tid = bid.split(':')[0] if ':' in bid else bid

        v_before = len(poly.exterior.coords) - 1
        ortho_before = reg.compute_orthogonality_ratio(poly)
        area_before = poly.area

        # 1. Orthogonal Regularization
        reg_poly = reg.orthogonalize_cad(poly, tolerance=0.5)
        if not reg_poly.is_valid:
            reg_poly = make_valid(reg_poly)
            if hasattr(reg_poly, 'geoms'):
                polys = [g for g in reg_poly.geoms if isinstance(g, Polygon)]
                if polys:
                    reg_poly = max(polys, key=lambda g: g.area)

        v_after = len(reg_poly.exterior.coords) - 1
        ortho_after = reg.compute_orthogonality_ratio(reg_poly)
        area_after = reg_poly.area
        hausdorff = poly.hausdorff_distance(reg_poly)
        area_diff_pct = abs(area_after - area_before) / (area_before + 1e-6) * 100.0

        print(f"{bid:<8} {v_before:6d} -> {v_after:6d} | {ortho_before:8.2f} -> {ortho_after:8.2f} | {hausdorff:9.2f}m | {area_before:8.1f}m2 -> {area_after:8.1f}m2 | {area_diff_pct:6.1f}%")

        # 2. Parametric Eave Retraction (-0.40m mitre join)
        sol_poly = reg_poly.buffer(-0.40, join_style=2)
        if not sol_poly.is_valid or sol_poly.is_empty:
            sol_poly = reg_poly.buffer(-0.25, join_style=2)
        if hasattr(sol_poly, 'geoms'):
            polys = [g for g in sol_poly.geoms if isinstance(g, Polygon)]
            if polys:
                sol_poly = max(polys, key=lambda g: g.area)

        roof_records.append({
            'body_id': bid,
            'test_id': tid,
            'vertices_before': int(v_before),
            'vertices_after': int(v_after),
            'ortho_before': round(float(ortho_before), 3),
            'ortho_after': round(float(ortho_after), 3),
            'hausdorff_m': round(float(hausdorff), 3),
            'area_before_m2': round(float(area_before), 2),
            'area_after_m2': round(float(area_after), 2),
            'area_diff_pct': round(float(area_diff_pct), 2),
            'geometry_role': 'ORTHOGONAL_ROOF_HYPOTHESIS',
            'owner_verdict': 'PENDING_OWNER_REVIEW',
            'geometry': reg_poly
        })

        sol_records.append({
            'body_id': bid,
            'test_id': tid,
            'eave_offset_m': -0.40,
            'area_sol_m2': round(float(sol_poly.area), 2),
            'geometry_role': 'PARAMETRIC_EAVE_RETRACTION_HYPOTHESIS',
            'owner_verdict': 'PENDING_OWNER_REVIEW',
            'geometry': sol_poly
        })

        before_records.append({
            'body_id': bid,
            'test_id': tid,
            'area_m2': round(float(area_before), 2),
            'geometry_role': 'RAW_OBSERVED_MASK_BEFORE',
            'geometry': poly
        })

        report_rows.append({
            'body_id': bid,
            'test_id': tid,
            'vertices_before': int(v_before),
            'vertices_after': int(v_after),
            'ortho_before': round(float(ortho_before), 3),
            'ortho_after': round(float(ortho_after), 3),
            'hausdorff_m': round(float(hausdorff), 3),
            'area_before_m2': round(float(area_before), 2),
            'area_after_m2': round(float(area_after), 2),
            'area_diff_pct': round(float(area_diff_pct), 2),
            'owner_verdict': 'PENDING_OWNER_REVIEW'
        })

    print("=" * 105)

    # 3. Export to GeoPackage
    print(f"\n[*] Salvare straturi in {OUT_GPKG}")
    gdf_roof = gpd.GeoDataFrame(roof_records, crs="EPSG:3844")
    gdf_sol = gpd.GeoDataFrame(sol_records, crs="EPSG:3844")
    gdf_before = gpd.GeoDataFrame(before_records, crs="EPSG:3844")

    gdf_roof.to_file(OUT_GPKG, layer='ROOF_HYPOTHESES_ORTHO90', driver='GPKG')
    gdf_sol.to_file(OUT_GPKG, layer='FOOTPRINT_HYPOTHESES_SOL', driver='GPKG')
    gdf_before.to_file(OUT_GPKG, layer='RAW_CANDIDATES_BEFORE', driver='GPKG')

    # 4. Save JSON Report
    report_path = OUT_DIR / 'regularization_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'task': 'LOT3_ORTHOGONAL_REGULARIZATION',
            'crs': 'EPSG:3844',
            'total_cases': len(report_rows),
            'mean_ortho_after': round(float(np.mean([r['ortho_after'] for r in report_rows])), 3),
            'mean_hausdorff_m': round(float(np.mean([r['hausdorff_m'] for r in report_rows])), 3),
            'cases': report_rows
        }, f, indent=2)
    print(f"[*] Raport metric salvat: {report_path}")

    # 5. Generate Visual Comparison Grid (20 panels)
    print(f"\n[*] Generare plansa comparativa multi-panel...")
    fig, axes = plt.subplots(4, 5, figsize=(25, 20))
    axes = axes.flatten()

    for idx, r in enumerate(roof_records):
        ax = axes[idx]
        bid = r['body_id']
        tid = r['test_id']
        poly_before = before_records[idx]['geometry']
        poly_roof = r['geometry']
        poly_sol = sol_records[idx]['geometry']

        # Determine cover raster
        if tid == 'T17':
            cover_p = T17_COVER
        else:
            cover_p = COVERS_DIR / f"{tid}_5cm.tif"

        minx, miny, maxx, maxy = poly_roof.bounds
        margin = max(10.0, max(maxx - minx, maxy - miny) * 0.4)
        crop_bounds = (minx - margin, miny - margin, maxx + margin, maxy + margin)

        if cover_p.exists():
            try:
                with rasterio.open(cover_p) as src:
                    win = from_bounds(*crop_bounds, transform=src.transform)
                    img = src.read([1, 2, 3], window=win)
                    img = np.transpose(img, (1, 2, 0))
                    # Normalise to 0-1
                    if img.max() > 1.0:
                        img = np.clip(img / 255.0, 0, 1)
                    extent = [crop_bounds[0], crop_bounds[2], crop_bounds[1], crop_bounds[3]]
                    ax.imshow(img, extent=extent, origin='lower')
            except Exception:
                ax.set_facecolor('#222222')
        else:
            ax.set_facecolor('#222222')

        # Plot geometries
        # Before: dashed yellow
        bx, by = poly_before.exterior.xy
        ax.plot(bx, by, color='#ffff00', linestyle='--', linewidth=1.5, label='Inainte (selected_v3)')

        # Roof Ortho90: solid cyan
        rx, ry = poly_roof.exterior.xy
        ax.plot(rx, ry, color='#00ffff', linestyle='-', linewidth=2.0, label='Acoperis Ortho90')

        # Footprint Sol: dotted lime green
        sx, sy = poly_sol.exterior.xy
        ax.plot(sx, sy, color='#00ff00', linestyle=':', linewidth=1.5, label='Sol ANCPI (-0.40m)')

        ax.set_xlim(crop_bounds[0], crop_bounds[2])
        ax.set_ylim(crop_bounds[1], crop_bounds[3])
        ax.set_title(f"{bid} | v: {r['vertices_before']}->{r['vertices_after']} | ortho: {r['ortho_after']:.2f}\nH: {r['hausdorff_m']:.2f}m | Diff: {r['area_diff_pct']:.1f}%", fontsize=11, fontweight='bold', pad=4)
        ax.tick_params(labelsize=8)

    plt.tight_layout()
    chart_path = OUT_DIR / 'lot3_before_after_ortho90.png'
    plt.savefig(chart_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[*] Plansa comparativa salvata: {chart_path}")

    # 6. Update QGIS Project inspectie_corectii.qgs
    update_qgis_project()


def update_qgis_project():
    if not PROJECT_PATH.exists():
        print(f"[!] Proiectul QGIS nu exista la {PROJECT_PATH}")
        return

    backup_path = PROJECT_PATH.with_suffix('.qgs.backup_pre_ortho90')
    shutil.copy2(PROJECT_PATH, backup_path)
    print(f"[*] Backup creat: {backup_path}")

    # Read XML and insert the group LOT3_ORTHO90_20261018_PENDING_REVIEW
    content = PROJECT_PATH.read_text(encoding='utf-8')

    # Create IDs
    id_roof = "LOT3_ROOF_ORTHO90_20261018_01"
    id_sol = "LOT3_SOL_ANCPI_20261018_02"
    id_raw = "LOT3_RAW_BEFORE_20261018_03"
    gpkg_rel = "../lot3_repairs_20261017/selected_v4_orthogonal/lot3_orthogonal.gpkg"

    group_xml = f"""    <layer-tree-group name="LOT3_ORTHO90_20261018_PENDING_REVIEW" checked="Qt::Checked" expanded="1" groupLayer="">
      <customproperties>
        <Option/>
      </customproperties>
      <layer-tree-layer name="ROOF_HYPOTHESES_ORTHO90 (Cyan)" source="{gpkg_rel}|layername=ROOF_HYPOTHESES_ORTHO90" legend_exp="" providerKey="ogr" patch_size="-1,-1" legend_split_behavior="0" checked="Qt::Checked" id="{id_roof}" expanded="1"/>
      <layer-tree-layer name="FOOTPRINT_HYPOTHESES_SOL (-0.40m Green)" source="{gpkg_rel}|layername=FOOTPRINT_HYPOTHESES_SOL" legend_exp="" providerKey="ogr" patch_size="-1,-1" legend_split_behavior="0" checked="Qt::Checked" id="{id_sol}" expanded="1"/>
      <layer-tree-layer name="RAW_CANDIDATES_BEFORE (Yellow)" source="{gpkg_rel}|layername=RAW_CANDIDATES_BEFORE" legend_exp="" providerKey="ogr" patch_size="-1,-1" legend_split_behavior="0" checked="Qt::Unchecked" id="{id_raw}" expanded="0"/>
    </layer-tree-group>
"""

    layer_roof_xml = f"""    <maplayer type="vector" id="{id_roof}" name="ROOF_HYPOTHESES_ORTHO90 (Cyan)" minScale="1e+08" maxScale="0" geometry="Polygon" hasScaleBasedVisibilityFlag="0">
      <id>{id_roof}</id>
      <datasource>{gpkg_rel}|layername=ROOF_HYPOTHESES_ORTHO90</datasource>
      <title>ROOF_HYPOTHESES_ORTHO90 (Cyan)</title>
      <abstract></abstract>
      <keywordList><value></value></keywordList>
      <layername>ROOF_HYPOTHESES_ORTHO90 (Cyan)</layername>
      <srs>
        <spatialrefsys nativeFormat="Wkt">
          <wkt>PROJCRS["Pulkovo 1942(58) / Stereo70",BASEGEOGCRS["Pulkovo 1942(58)",DATUM["Pulkovo 1942(58)",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4179]],CONVERSION["Stereo 70",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],ID["EPSG",3844]]</wkt>
          <proj4>+proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass +units=m +no_defs</proj4>
          <srsid>27265</srsid>
          <srid>3844</srid>
          <authid>EPSG:3844</authid>
          <description>Pulkovo 1942(58) / Stereo70</description>
          <projectionacronym>sterea</projectionacronym>
          <ellipsoidacronym>EPSG:7024</ellipsoidacronym>
          <geographicflag>false</geographicflag>
        </spatialrefsys>
      </srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer pass="0" class="SimpleFill" locked="0">
              <prop k="color" v="0,0,0,0"/>
              <prop k="outline_color" v="0,229,255,255"/>
              <prop k="outline_width" v="0.6"/>
              <prop k="outline_width_unit" v="MM"/>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
"""

    layer_sol_xml = f"""    <maplayer type="vector" id="{id_sol}" name="FOOTPRINT_HYPOTHESES_SOL (-0.40m Green)" minScale="1e+08" maxScale="0" geometry="Polygon" hasScaleBasedVisibilityFlag="0">
      <id>{id_sol}</id>
      <datasource>{gpkg_rel}|layername=FOOTPRINT_HYPOTHESES_SOL</datasource>
      <title>FOOTPRINT_HYPOTHESES_SOL (-0.40m Green)</title>
      <abstract></abstract>
      <keywordList><value></value></keywordList>
      <layername>FOOTPRINT_HYPOTHESES_SOL (-0.40m Green)</layername>
      <srs>
        <spatialrefsys nativeFormat="Wkt">
          <wkt>PROJCRS["Pulkovo 1942(58) / Stereo70",BASEGEOGCRS["Pulkovo 1942(58)",DATUM["Pulkovo 1942(58)",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4179]],CONVERSION["Stereo 70",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],ID["EPSG",3844]]</wkt>
          <proj4>+proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass +units=m +no_defs</proj4>
          <srsid>27265</srsid>
          <srid>3844</srid>
          <authid>EPSG:3844</authid>
          <description>Pulkovo 1942(58) / Stereo70</description>
          <projectionacronym>sterea</projectionacronym>
          <ellipsoidacronym>EPSG:7024</ellipsoidacronym>
          <geographicflag>false</geographicflag>
        </spatialrefsys>
      </srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer pass="0" class="SimpleFill" locked="0">
              <prop k="color" v="0,0,0,0"/>
              <prop k="outline_color" v="0,255,100,255"/>
              <prop k="outline_width" v="0.45"/>
              <prop k="outline_style" v="dash"/>
              <prop k="outline_width_unit" v="MM"/>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
"""

    layer_raw_xml = f"""    <maplayer type="vector" id="{id_raw}" name="RAW_CANDIDATES_BEFORE (Yellow)" minScale="1e+08" maxScale="0" geometry="Polygon" hasScaleBasedVisibilityFlag="0">
      <id>{id_raw}</id>
      <datasource>{gpkg_rel}|layername=RAW_CANDIDATES_BEFORE</datasource>
      <title>RAW_CANDIDATES_BEFORE (Yellow)</title>
      <abstract></abstract>
      <keywordList><value></value></keywordList>
      <layername>RAW_CANDIDATES_BEFORE (Yellow)</layername>
      <srs>
        <spatialrefsys nativeFormat="Wkt">
          <wkt>PROJCRS["Pulkovo 1942(58) / Stereo70",BASEGEOGCRS["Pulkovo 1942(58)",DATUM["Pulkovo 1942(58)",ELLIPSOID["Krassowsky 1940",6378245,298.3,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4179]],CONVERSION["Stereo 70",METHOD["Oblique Stereographic",ID["EPSG",9809]],PARAMETER["Latitude of natural origin",46,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",25,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.99975,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",500000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["northing (X)",north,ORDER[1],LENGTHUNIT["metre",1]],AXIS["easting (Y)",east,ORDER[2],LENGTHUNIT["metre",1]],ID["EPSG",3844]]</wkt>
          <proj4>+proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass +units=m +no_defs</proj4>
          <srsid>27265</srsid>
          <srid>3844</srid>
          <authid>EPSG:3844</authid>
          <description>Pulkovo 1942(58) / Stereo70</description>
          <projectionacronym>sterea</projectionacronym>
          <ellipsoidacronym>EPSG:7024</ellipsoidacronym>
          <geographicflag>false</geographicflag>
        </spatialrefsys>
      </srs>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer pass="0" class="SimpleFill" locked="0">
              <prop k="color" v="0,0,0,0"/>
              <prop k="outline_color" v="255,235,59,255"/>
              <prop k="outline_width" v="0.4"/>
              <prop k="outline_style" v="dot"/>
              <prop k="outline_width_unit" v="MM"/>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
"""

    # Check if group already exists
    if 'LOT3_ORTHO90_20261018_PENDING_REVIEW' in content:
        print("[*] Grupul LOT3_ORTHO90 exista deja in proiectul QGIS.")
        return

    # Insert group at the top of <layer-tree-group>
    idx_tree = content.find('<layer-tree-group>')
    if idx_tree != -1:
        idx_custom = content.find('</customproperties>', idx_tree)
        if idx_custom != -1:
            insert_pos = idx_custom + len('</customproperties>\n')
            content = content[:insert_pos] + group_xml + content[insert_pos:]

    # Insert layers before </projectlayers>
    idx_layers = content.find('</projectlayers>')
    if idx_layers != -1:
        content = content[:idx_layers] + layer_roof_xml + layer_sol_xml + layer_raw_xml + content[idx_layers:]

    PROJECT_PATH.write_text(content, encoding='utf-8')
    print(f"[*] Proiectul QGIS inspectie_corectii.qgs a fost actualizat cu grupul LOT3_ORTHO90_20261018_PENDING_REVIEW!")


if __name__ == '__main__':
    main()
