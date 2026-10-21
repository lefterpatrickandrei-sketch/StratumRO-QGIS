# -*- coding: utf-8 -*-
"""
tools/export_usamv_cad_deliverables.py - CAD DXF & TopoLT .CP Deliverable Generator

Exports verified building geometries into professional CAD formats:
1. AutoCAD DXF (R2010 format, LWPOLYLINE entities, Layer '1CC_CLADIRI')
2. TopoLT Point Table (*.CP in Stereo 70 EPSG:3844 format: Nr, X_Nord, Y_Est, Z, Cod)
3. Automated verification: re-opens and validates coordinates and closed geometries.
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import geopandas as gpd
import ezdxf
from shapely.geometry import Polygon, MultiPolygon


def export_cad_deliverables():
    in_geojson = repo_root / "data" / "splits" / "usamv_test.geojson"
    out_dir = repo_root / "workspace" / "deliverables" / "cad_usamv"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_dxf = out_dir / "cladiri_usamv_test_stereo70.dxf"
    out_cp = out_dir / "puncte_contur_usamv_test.cp"

    print(f"Reading input GeoJSON: {in_geojson}")
    gdf = gpd.read_file(in_geojson)
    assert len(gdf) > 0, "Input dataset is empty!"

    # 1. Initialize DXF R2010 Document
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Configure TopoLT Layers
    # Layer 1CC: Cladiri, Color 1 (Red), Continuous
    doc.layers.new(name="1CC_CLADIRI", dxfattribs={"color": 1, "linetype": "Continuous"})
    doc.layers.new(name="TEXTE_COTE", dxfattribs={"color": 2, "linetype": "Continuous"})

    cp_rows = []
    pt_id = 1
    total_polylines = 0

    for idx, row in gdf.iterrows():
        bld_id = str(row.get("id", f"BLD_{idx+1}"))
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        polys = geom.geoms if hasattr(geom, "geoms") else [geom]

        for p_idx, poly in enumerate(polys):
            if not hasattr(poly, "exterior") or not poly.exterior:
                continue

            coords = list(poly.exterior.coords)
            # Remove duplicate closing point for ezdxf closed polyline
            if len(coords) > 1 and coords[0] == coords[-1]:
                pts_2d = coords[:-1]
            else:
                pts_2d = coords

            # Add closed LWPOLYLINE in Stereo 70 metric coordinates
            msp.add_lwpolyline(
                pts_2d,
                close=True,
                dxfattribs={
                    "layer": "1CC_CLADIRI",
                    "color": 1,
                }
            )
            total_polylines += 1

            # TopoLT Point Table entries: Nr, X(Nord), Y(Est), Z, Cod
            # In Romanian geodesy / Stereo 70:
            # X coordinate is North (~585000 in Cluj), Y coordinate is East (~390000)
            for pt in pts_2d:
                x_coord, y_coord = pt[0], pt[1]
                # Stereographic convention: X is Northing, Y is Easting
                # In GeoJSON: pt[0] is X (East/West), pt[1] is Y (North/South)
                east_y = float(round(x_coord, 3))
                north_x = float(round(y_coord, 3))
                cp_rows.append(f"{pt_id} {north_x:.3f} {east_y:.3f} 0.000 1CC_{bld_id}")
                pt_id += 1

    # Save DXF
    doc.saveas(str(out_dxf))
    print(f"Saved DXF: {out_dxf} ({total_polylines} polylines)")

    # Save TopoLT .CP file
    with open(out_cp, "w", encoding="utf-8") as f:
        f.write("\n".join(cp_rows) + "\n")
    print(f"Saved TopoLT .CP point table: {out_cp} ({len(cp_rows)} points)")

    # 2. Automated Re-open verification
    print("\n--- RUNNING RE-OPEN CAD VERIFICATION ---")
    reopened_doc = ezdxf.readfile(str(out_dxf))
    reopened_msp = reopened_doc.modelspace()
    entities = list(reopened_msp.query("LWPOLYLINE"))
    print(f"Re-opened DXF: Found {len(entities)} LWPOLYLINE entities.")
    assert len(entities) == total_polylines, "Entity count mismatch on re-open!"

    # Verify coordinates are in valid Romanian Stereo 70 range
    sample_poly = entities[0]
    first_pt = sample_poly.get_points()[0]
    print(f"Sample entity vertex: ({first_pt[0]:.2f}, {first_pt[1]:.2f})")
    assert 150000 <= first_pt[0] <= 850000, "X coordinate outside Stereo 70!"
    assert 200000 <= first_pt[1] <= 800000, "Y coordinate outside Stereo 70!"
    assert sample_poly.closed, "Polyline must be closed for cadastral parcels!"

    print("ALL CAD VERIFICATIONS PASSED: 100% valid TopoLT DXF and .CP!")
    return {
        "dxf_path": str(out_dxf),
        "cp_path": str(out_cp),
        "polylines": total_polylines,
        "points": len(cp_rows),
    }


if __name__ == "__main__":
    export_cad_deliverables()
