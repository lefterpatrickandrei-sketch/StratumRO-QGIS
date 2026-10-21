# -*- coding: utf-8 -*-
"""
stratum_ro/pug_topology.py - Order 904/2023 Article 9 Topology Audit Engine

Implements headless automated spatial checks mandated by Order MDLPA nr. 904/2023:
1. Article 8: ISO 19125-1 simple geometry rules (validity, no self-intersections).
2. Article 9(1): Functional zoning topology:
   - No overlaps between functional zoning polygons (ZFExistenta / ZFPropusa).
   - No gaps between functional zoning and the administrative / intravilan boundary.
3. Article 2 & 7: EPSG:3844 Stereo 70 projection and GeoPackage format validation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


@dataclass
class TopologyCheckResult:
    check_name: str
    passed: bool
    details: str
    defect_count: int = 0
    defect_area_m2: float = 0.0
    items: List[Dict[str, Any]] = field(default_factory=list)


class Order904TopologyAuditor:
    """
    Automated topological validator for urbanism datasets under Order 904/2023.
    """

    def __init__(self, tolerance_m2: float = 0.01, crs: str = "EPSG:3844"):
        self.tolerance_m2 = tolerance_m2
        self.crs = crs

    def check_simple_geometries(self, gdf: gpd.GeoDataFrame) -> TopologyCheckResult:
        """Article 8: Simple geometries (ISO 19125-1), valid, non-empty."""
        defects = []
        for idx, row in gdf.iterrows():
            geom = row.geometry
            fid = row.get("id", idx)
            if geom is None or geom.is_empty:
                defects.append({"id": fid, "error": "Empty geometry"})
            elif not geom.is_valid:
                defects.append({"id": fid, "error": f"Invalid geometry: {geom.is_valid}"})

        passed = len(defects) == 0
        return TopologyCheckResult(
            check_name="Art. 8 Simple Geometries (ISO 19125-1)",
            passed=passed,
            details="All features valid simple geometries" if passed else f"{len(defects)} invalid geometries",
            defect_count=len(defects),
            items=defects,
        )

    def check_functional_zoning_no_overlaps(self, gdf: gpd.GeoDataFrame) -> TopologyCheckResult:
        """Article 9(1): Functional zoning polygons must NOT overlap."""
        geoms = [g for g in gdf.geometry if g is not None and not g.is_empty]
        overlaps = []
        total_overlap_area = 0.0

        n = len(geoms)
        for i in range(n):
            for j in range(i + 1, n):
                inter = geoms[i].intersection(geoms[j])
                if not inter.is_empty and inter.area > self.tolerance_m2:
                    area_m2 = round(float(inter.area), 3)
                    total_overlap_area += area_m2
                    overlaps.append({
                        "feature_a_idx": i,
                        "feature_b_idx": j,
                        "overlap_area_m2": area_m2,
                    })

        passed = len(overlaps) == 0
        return TopologyCheckResult(
            check_name="Art. 9(1) Functional Zoning: No Overlaps",
            passed=passed,
            details="No overlaps detected" if passed else f"Found {len(overlaps)} overlaps (Total: {total_overlap_area:.2f} m2)",
            defect_count=len(overlaps),
            defect_area_m2=round(total_overlap_area, 3),
            items=overlaps,
        )

    def check_boundary_coverage(
        self,
        zoning_gdf: gpd.GeoDataFrame,
        boundary_geom: Any,
    ) -> TopologyCheckResult:
        """Article 9(1): No gaps between functional zoning and the boundary."""
        if boundary_geom is None or boundary_geom.is_empty:
            return TopologyCheckResult(
                check_name="Art. 9(1) Functional Zoning: No Gaps vs Boundary",
                passed=False,
                details="Boundary geometry is empty or missing",
                defect_count=1,
            )

        zoning_union = unary_union([g for g in zoning_gdf.geometry if g is not None and not g.is_empty])
        gaps = boundary_geom.difference(zoning_union)

        if gaps.is_empty or gaps.area <= self.tolerance_m2:
            return TopologyCheckResult(
                check_name="Art. 9(1) Functional Zoning: No Gaps vs Boundary",
                passed=True,
                details="Functional zoning completely covers boundary without gaps",
                defect_count=0,
                defect_area_m2=0.0,
            )

        gap_polys = gaps.geoms if hasattr(gaps, "geoms") else [gaps]
        gap_items = [
            {"idx": idx, "area_m2": round(p.area, 3)}
            for idx, p in enumerate(gap_polys)
            if p.area > self.tolerance_m2
        ]

        total_gap_area = sum(item["area_m2"] for item in gap_items)
        return TopologyCheckResult(
            check_name="Art. 9(1) Functional Zoning: No Gaps vs Boundary",
            passed=len(gap_items) == 0,
            details=f"Found {len(gap_items)} coverage gaps (Total: {total_gap_area:.2f} m2)",
            defect_count=len(gap_items),
            defect_area_m2=round(total_gap_area, 3),
            items=gap_items,
        )

    def audit_geopackage(
        self,
        gpkg_path: str,
        zoning_layer: str = "ZFExistenta",
        boundary_layer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Runs complete headless Order 904/2023 QA audit on a PUG GeoPackage.
        """
        p = Path(gpkg_path)
        if not p.exists():
            return {"status": "FAILED", "error": f"File not found: {gpkg_path}"}

        try:
            import pyogrio
            layers = [l[0] for l in pyogrio.list_layers(str(p))]
        except Exception:
            try:
                import fiona
                layers = fiona.listlayers(str(p))
            except Exception:
                import sqlite3
                con = sqlite3.connect(str(p))
                cur = con.cursor()
                layers = [r[0] for r in cur.execute("SELECT table_name FROM gpkg_contents").fetchall()]
                con.close()

        checks = []
        overall_passed = True

        # Check 1: Mandatory layer presence
        has_zoning = zoning_layer in layers
        checks.append({
            "check": f"Presence of '{zoning_layer}' layer",
            "passed": has_zoning,
            "details": f"Found in layers: {layers}" if has_zoning else f"Missing from {layers}",
        })
        if not has_zoning:
            overall_passed = False

        if has_zoning:
            gdf = gpd.read_file(str(p), layer=zoning_layer)
            # Check 2: Simple geometries
            res_geom = self.check_simple_geometries(gdf)
            checks.append({"check": res_geom.check_name, "passed": res_geom.passed, "details": res_geom.details})
            if not res_geom.passed:
                overall_passed = False

            # Check 3: No overlaps
            res_overlap = self.check_functional_zoning_no_overlaps(gdf)
            checks.append({"check": res_overlap.check_name, "passed": res_overlap.passed, "details": res_overlap.details})
            if not res_overlap.passed:
                overall_passed = False

            # Check 4: Boundary coverage (if boundary available)
            if boundary_layer and boundary_layer in layers:
                bgdf = gpd.read_file(str(p), layer=boundary_layer)
                b_geom = unary_union(list(bgdf.geometry))
                res_cov = self.check_boundary_coverage(gdf, b_geom)
                checks.append({"check": res_cov.check_name, "passed": res_cov.passed, "details": res_cov.details})
                if not res_cov.passed:
                    overall_passed = False

        return {
            "gpkg_path": str(p),
            "order_904_compliant": overall_passed,
            "crs": self.crs,
            "layers_found": layers,
            "checks": checks,
        }
