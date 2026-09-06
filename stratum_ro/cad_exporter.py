# -*- coding: utf-8 -*-
"""
ANCPI-Compliant CAD (.dxf) Exporter for StratumRO.
Exports cadastral building footprints and topographic features to AutoCAD DXF format
strictly structured on official ANCPI layers:
  - CONSTRUCTII (Main buildings - Red)
  - ANEXE (Secondary outbuildings/garages - Yellow/Magenta)
  - ARBORI (Trees - Green circles/points)
  - STALPI (Towers and utility poles - Cyan)
  - PARCELE (Cadastral parcel limits - Green)
  - TEXTE (Cadastral text annotations - White)
"""

import os
from typing import List, Dict, Any
from shapely.geometry import Polygon, MultiPolygon, Point
import ezdxf
from ezdxf import colors


def _extract_polygons(geom) -> List[Polygon]:
    """Recursively extracts Polygon instances from any Shapely geometry."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        res = []
        for g in geom.geoms:
            res.extend(_extract_polygons(g))
        return res
    return []


class CadastralDxfExporter:
    """Generates standard Romanian Cadastral DXF files from vector layers."""

    def __init__(self, dxf_version: str = "R2010"):
        self.dxf_version = dxf_version

    def _setup_ancpi_layers(self, doc):
        """Initializes standard ANCPI cadastre layers with CAD colors."""
        layers = doc.layers
        layer_defs = [
            ("CONSTRUCTII", colors.RED),
            ("ANEXE", colors.YELLOW),
            ("ARBORI", colors.GREEN),
            ("STALPI", colors.CYAN),
            ("PARCELE", colors.GREEN),
            ("GARDURI", colors.CYAN),
            ("TEXTE", colors.WHITE)
        ]
        for name, col in layer_defs:
            if name not in layers:
                layers.add(name=name, color=col, linetype="Continuous")

    def export_multicategory_to_dxf(
        self,
        categories_dict: Dict[str, List[Dict[str, Any]]],
        output_dxf_path: str,
        include_labels: bool = True
    ) -> str:
        """
        Exports multiple categories into dedicated ANCPI layers in AutoCAD DXF.

        :param categories_dict: Dict with keys 'CLADIRI_PRINCIPALE', 'ANEXE_GOSPODARESTI', 'ARBORI', 'STALPI_TURNURI'
        :param output_dxf_path: Output .dxf file path
        :param include_labels: Whether to generate text annotations
        :return: Path to saved DXF
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_dxf_path)), exist_ok=True)
        doc = ezdxf.new(dxfversion=self.dxf_version)
        msp = doc.modelspace()
        self._setup_ancpi_layers(doc)

        # 1. Export Main Buildings -> CONSTRUCTII
        main_buildings = categories_dict.get("CLADIRI_HIBRID") or categories_dict.get("CLADIRI_PRINCIPALE", [])
        for b in main_buildings:
            polys = _extract_polygons(b.get("geometry"))
            bid = b.get("id", 1)
            total_area = b.get("area_m2", sum(p.area for p in polys))

            for poly in polys:
                if poly.area < 2.0 or len(poly.exterior.coords) < 4:
                    continue
                points = [(round(p[0], 3), round(p[1], 3)) for p in poly.exterior.coords]
                msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "CONSTRUCTII", "color": colors.RED})

                for interior in poly.interiors:
                    int_pts = [(round(p[0], 3), round(p[1], 3)) for p in interior.coords]
                    msp.add_lwpolyline(int_pts, close=True, dxfattribs={"layer": "CONSTRUCTII", "color": colors.RED})

            if include_labels and polys:
                c = max(polys, key=lambda p: p.area).centroid
                msp.add_text(
                    f"C{bid}: {total_area:.1f}mp",
                    dxfattribs={"layer": "TEXTE", "height": 1.5, "color": colors.WHITE}
                ).set_placement((round(c.x, 3), round(c.y, 3)), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

        # 2. Export Outbuildings -> ANEXE
        outbuildings = categories_dict.get("ANEXE_GOSPODARESTI", [])
        for a_idx, a in enumerate(outbuildings, start=1):
            polys = _extract_polygons(a.get("geometry"))
            total_area = a.get("area_m2", sum(p.area for p in polys))

            for poly in polys:
                if poly.area < 2.0 or len(poly.exterior.coords) < 4:
                    continue
                points = [(round(p[0], 3), round(p[1], 3)) for p in poly.exterior.coords]
                msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "ANEXE", "color": colors.YELLOW})

            if include_labels and polys:
                c = max(polys, key=lambda p: p.area).centroid
                msp.add_text(
                    f"Anexa: {total_area:.1f}mp",
                    dxfattribs={"layer": "TEXTE", "height": 1.2, "color": colors.WHITE}
                ).set_placement((round(c.x, 3), round(c.y, 3)), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

        # 3. Export Trees -> ARBORI (Circle with crown radius)
        trees = categories_dict.get("ARBORI", [])
        for t in trees:
            gx = float(t.get("center_x", t.get("x", 0.0)))
            gy = float(t.get("center_y", t.get("y", 0.0)))
            r = float(t.get("crown_radius_m", 2.0))
            msp.add_circle((round(gx, 3), round(gy, 3)), radius=max(r, 1.0), dxfattribs={"layer": "ARBORI", "color": colors.GREEN})
            msp.add_point((round(gx, 3), round(gy, 3)), dxfattribs={"layer": "ARBORI", "color": colors.GREEN})

        # 4. Export Poles & Towers -> STALPI
        poles = categories_dict.get("STALPI_TURNURI", [])
        for p in poles:
            gx = float(p.get("center_x", p.get("x", 0.0)))
            gy = float(p.get("center_y", p.get("y", 0.0)))
            h = float(p.get("height_m", 0.0))
            st_type = p.get("type", "Stalp")

            msp.add_circle((round(gx, 3), round(gy, 3)), radius=1.0, dxfattribs={"layer": "STALPI", "color": colors.CYAN})
            msp.add_point((round(gx, 3), round(gy, 3)), dxfattribs={"layer": "STALPI", "color": colors.CYAN})
            if include_labels:
                msp.add_text(
                    f"{st_type} (H={h:.1f}m)",
                    dxfattribs={"layer": "TEXTE", "height": 1.0, "color": colors.WHITE}
                ).set_placement((round(gx + 1.2, 3), round(gy, 3)), align=ezdxf.enums.TextEntityAlignment.BOTTOM_LEFT)

        doc.saveas(output_dxf_path)
        return output_dxf_path

    def export_buildings_to_dxf(
        self,
        buildings: List[Dict[str, Any]],
        output_dxf_path: str,
        include_labels: bool = True
    ) -> str:
        """Legacy helper: exports single building list."""
        return self.export_multicategory_to_dxf(
            {"CLADIRI_PRINCIPALE": buildings},
            output_dxf_path,
            include_labels=include_labels
        )
