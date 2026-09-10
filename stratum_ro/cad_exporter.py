# -*- coding: utf-8 -*-
"""
ANCPI & TopoLT Compliant CAD (.dxf / .cp) Exporter for StratumRO.
Conformitate legislativă & tehnică:
  - Ordinul ANCPI nr. 600/2023 (Anexa 1.34 / 1.35 - Plan de Amplasament și Delimitare - PAD)
  - Convenția de straturi TopoLT:
      1CC        : Clădiri principale (Culoare 1 - Roșu)
      2CC        : Anexe gospodărești / Garaje (Culoare 2 - Galben)
      CP         : Contur proprietate / Limită sector cadastral (Culoare 3 - Verde)
      VARFURI    : Puncte de contur (POINT, Culoare 4 - Cyan)
      NUMERE_PCT : Indicii numerici ai colțurilor (1..N, Culoare 7 - Alb / Galben)
      TEXTE      : Etichete construcții (C1, C2, Sc, Culoare 7 - Alb)
      TABEL_PAD  : Cadrul și textele inventarului de coordonate Stereo 70
"""

import os
import math
from typing import List, Dict, Any, Tuple, Optional
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
    """Generates standard Romanian Cadastral DXF and .CP files from vector layers."""

    def __init__(self, dxf_version: str = "R2010"):
        self.dxf_version = dxf_version

    def _setup_layers(self, doc, topolt_mode: bool = True):
        """Initializes standard ANCPI & TopoLT cadastre layers with CAD colors."""
        layers = doc.layers
        layer_defs = [
            # TopoLT standard
            ("1CC", colors.RED),
            ("2CC", colors.YELLOW),
            ("CP", colors.GREEN),
            ("VARFURI", colors.CYAN),
            ("NUMERE_PCT", colors.YELLOW),
            ("TABEL_PAD", colors.WHITE),
            # ANCPI legacy / alternate
            ("CONSTRUCTII", colors.RED),
            ("ANEXE", colors.YELLOW),
            ("PARCELE", colors.GREEN),
            ("GARDURI", colors.CYAN),
            ("ARBORI", colors.GREEN),
            ("STALPI", colors.CYAN),
            ("TEXTE", colors.WHITE)
        ]
        for name, col in layer_defs:
            if name not in layers:
                layers.add(name=name, color=col, linetype="Continuous")

    def _draw_pad_coordinate_table(
        self,
        msp,
        table_data: List[Dict[str, Any]],
        origin_x: float,
        origin_y: float,
        row_height: float = 3.5,
        col_widths: Tuple[float, float, float, float] = (14.0, 24.0, 24.0, 20.0),
        table_title: str = "INVENTAR DE COORDONATE STEREO 70 (PAD)"
    ):
        """
        Draws an official ANCPI PAD coordinate table in CAD model space using lines and text.
        Compatible with all AutoCAD / TopoLT / BricsCAD / QGIS versions.
        Columns: [ Nr. Pct. | Coordonata Nord (X) [m] | Coordonata Est (Y) [m] | Lungime latura D(i,i+1) [m] ]
        """
        w_tot = sum(col_widths)
        w0, w1, w2, w3 = col_widths

        x_cur = origin_x
        y_cur = origin_y

        # Title block
        msp.add_line((x_cur, y_cur), (x_cur + w_tot, y_cur), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})
        msp.add_line((x_cur, y_cur - row_height * 1.5), (x_cur + w_tot, y_cur - row_height * 1.5), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})
        msp.add_text(
            table_title,
            dxfattribs={"layer": "TABEL_PAD", "height": 1.6, "color": colors.WHITE}
        ).set_placement((x_cur + w_tot / 2.0, y_cur - row_height * 1.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

        y_cur -= row_height * 1.5

        # Header block
        headers = ["Nr. Pct.", "X [Nord] (m)", "Y [Est] (m)", "D(i, i+1) (m)"]
        col_starts = [x_cur, x_cur + w0, x_cur + w0 + w1, x_cur + w0 + w1 + w2]

        msp.add_line((x_cur, y_cur - row_height), (x_cur + w_tot, y_cur - row_height), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})

        for i, (h_txt, c_start, c_w) in enumerate(zip(headers, col_starts, col_widths)):
            msp.add_text(
                h_txt,
                dxfattribs={"layer": "TABEL_PAD", "height": 1.2, "color": colors.CYAN}
            ).set_placement((c_start + c_w / 2.0, y_cur - row_height / 2.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

        y_cur -= row_height

        # Rows
        for row in table_data:
            msp.add_line((x_cur, y_cur - row_height), (x_cur + w_tot, y_cur - row_height), dxfattribs={"layer": "TABEL_PAD", "color": colors.WHITE})

            vals = [
                str(row.get("nr", "")),
                f"{float(row.get('x', 0.0)):.3f}",
                f"{float(row.get('y', 0.0)):.3f}",
                f"{float(row.get('dist', 0.0)):.2f}" if row.get('dist') is not None else "-"
            ]
            for val_txt, c_start, c_w in zip(vals, col_starts, col_widths):
                msp.add_text(
                    val_txt,
                    dxfattribs={"layer": "TABEL_PAD", "height": 1.1, "color": colors.WHITE}
                ).set_placement((c_start + c_w / 2.0, y_cur - row_height / 2.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

            y_cur -= row_height

        # Outer box & vertical column dividers
        top_y = origin_y
        bot_y = y_cur
        msp.add_line((x_cur, top_y), (x_cur, bot_y), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})
        msp.add_line((x_cur + w0, top_y - row_height * 1.5), (x_cur + w0, bot_y), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})
        msp.add_line((x_cur + w0 + w1, top_y - row_height * 1.5), (x_cur + w0 + w1, bot_y), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})
        msp.add_line((x_cur + w0 + w1 + w2, top_y - row_height * 1.5), (x_cur + w0 + w1 + w2, bot_y), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})
        msp.add_line((x_cur + w_tot, top_y), (x_cur + w_tot, bot_y), dxfattribs={"layer": "TABEL_PAD", "color": colors.CYAN})

    def export_multicategory_to_dxf(
        self,
        categories_dict: Dict[str, List[Dict[str, Any]]],
        output_dxf_path: str,
        include_labels: bool = True,
        topolt_mode: bool = False,
        draw_pad_table: bool = True
    ) -> str:
        """
        Exports multiple categories into dedicated ANCPI / TopoLT layers in AutoCAD DXF.

        :param categories_dict: Dict with keys 'CLADIRI_PRINCIPALE', 'ANEXE_GOSPODARESTI', 'ARBORI', 'STALPI_TURNURI', 'PARCELE'
        :param output_dxf_path: Output .dxf file path
        :param include_labels: Whether to generate text annotations
        :param topolt_mode: If True, uses official TopoLT layers (1CC, 2CC, CP, VARFURI, NUMERE_PCT)
        :param draw_pad_table: If True, draws the official ANCPI PAD coordinate table in model space
        :return: Path to saved DXF
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_dxf_path)), exist_ok=True)
        doc = ezdxf.new(dxfversion=self.dxf_version)
        msp = doc.modelspace()
        self._setup_layers(doc, topolt_mode=topolt_mode)

        main_layer = "1CC" if topolt_mode else "CONSTRUCTII"
        anexe_layer = "2CC" if topolt_mode else "ANEXE"
        parcel_layer = "CP" if topolt_mode else "PARCELE"

        all_coords_for_bbox: List[Tuple[float, float]] = []
        pad_table_entries: List[Dict[str, Any]] = []
        global_point_idx = 1

        # 1. Export Main Buildings -> 1CC / CONSTRUCTII
        main_buildings = categories_dict.get("CLADIRI_HIBRID") or categories_dict.get("CLADIRI_PRINCIPALE", [])
        for b in main_buildings:
            polys = _extract_polygons(b.get("geometry"))
            bid = b.get("id", 1)
            total_area = b.get("area_m2", sum(p.area for p in polys))

            for poly in polys:
                if poly.area < 2.0 or len(poly.exterior.coords) < 4:
                    continue

                # Clockwise clean coordinates
                raw_coords = list(poly.exterior.coords)
                if not poly.exterior.is_ccw:
                    coords_clean = raw_coords[:-1]
                else:
                    coords_clean = raw_coords[:-1][::-1]

                pts_closed = [(round(p[0], 3), round(p[1], 3)) for p in coords_clean] + [(round(coords_clean[0][0], 3), round(coords_clean[0][1], 3))]
                msp.add_lwpolyline(pts_closed, close=True, dxfattribs={"layer": main_layer, "color": colors.RED})

                # TopoLT numbered vertices & PAD collection
                n_pts = len(coords_clean)
                for v_i, pt in enumerate(coords_clean):
                    gx, gy = round(pt[0], 3), round(pt[1], 3)
                    all_coords_for_bbox.append((gx, gy))

                    # Next point for distance calculation
                    next_pt = coords_clean[(v_i + 1) % n_pts]
                    dist_to_next = math.hypot(next_pt[0] - pt[0], next_pt[1] - pt[1])

                    # Add Point entity & Number Text
                    if topolt_mode:
                        msp.add_point((gx, gy), dxfattribs={"layer": "VARFURI", "color": colors.CYAN})
                        msp.add_text(
                            str(global_point_idx),
                            dxfattribs={"layer": "NUMERE_PCT", "height": 1.0, "color": colors.YELLOW}
                        ).set_placement((gx + 0.6, gy + 0.6), align=ezdxf.enums.TextEntityAlignment.BOTTOM_LEFT)

                    pad_table_entries.append({
                        "nr": global_point_idx,
                        "x": gx,
                        "y": gy,
                        "dist": round(dist_to_next, 2),
                        "cod": f"C{bid}"
                    })
                    global_point_idx += 1

                for interior in poly.interiors:
                    int_pts = [(round(p[0], 3), round(p[1], 3)) for p in interior.coords]
                    msp.add_lwpolyline(int_pts, close=True, dxfattribs={"layer": main_layer, "color": colors.RED})

            if include_labels and polys:
                c = max(polys, key=lambda p: p.area).centroid
                label_txt = f"C{bid}: {total_area:.1f}mp"
                msp.add_text(
                    label_txt,
                    dxfattribs={"layer": "TEXTE", "height": 1.5, "color": colors.WHITE}
                ).set_placement((round(c.x, 3), round(c.y, 3)), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

        # 2. Export Outbuildings -> 2CC / ANEXE
        outbuildings = categories_dict.get("ANEXE_GOSPODARESTI", [])
        for a_idx, a in enumerate(outbuildings, start=1):
            polys = _extract_polygons(a.get("geometry"))
            total_area = a.get("area_m2", sum(p.area for p in polys))

            for poly in polys:
                if poly.area < 2.0 or len(poly.exterior.coords) < 4:
                    continue
                coords_clean = list(poly.exterior.coords)[:-1]
                pts_closed = [(round(p[0], 3), round(p[1], 3)) for p in coords_clean] + [(round(coords_clean[0][0], 3), round(coords_clean[0][1], 3))]
                msp.add_lwpolyline(pts_closed, close=True, dxfattribs={"layer": anexe_layer, "color": colors.YELLOW})

                for v_i, pt in enumerate(coords_clean):
                    gx, gy = round(pt[0], 3), round(pt[1], 3)
                    all_coords_for_bbox.append((gx, gy))
                    if topolt_mode:
                        msp.add_point((gx, gy), dxfattribs={"layer": "VARFURI", "color": colors.CYAN})
                        msp.add_text(
                            str(global_point_idx),
                            dxfattribs={"layer": "NUMERE_PCT", "height": 0.8, "color": colors.YELLOW}
                        ).set_placement((gx + 0.5, gy + 0.5), align=ezdxf.enums.TextEntityAlignment.BOTTOM_LEFT)
                    global_point_idx += 1

            if include_labels and polys:
                c = max(polys, key=lambda p: p.area).centroid
                msp.add_text(
                    f"Anexa: {total_area:.1f}mp",
                    dxfattribs={"layer": "TEXTE", "height": 1.2, "color": colors.WHITE}
                ).set_placement((round(c.x, 3), round(c.y, 3)), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

        # 3. Export Parcels / Sectors -> CP / PARCELE
        parcels = categories_dict.get("PARCELE", []) or categories_dict.get("LIMITA_SECTOR", [])
        for p_item in parcels:
            polys = _extract_polygons(p_item.get("geometry") if isinstance(p_item, dict) else p_item)
            for poly in polys:
                pts = [(round(pt[0], 3), round(pt[1], 3)) for pt in poly.exterior.coords]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": parcel_layer, "color": colors.GREEN})
                for pt in pts:
                    all_coords_for_bbox.append(pt)

        # 4. Export Trees -> ARBORI (Circle with crown radius)
        trees = categories_dict.get("ARBORI", [])
        for t in trees:
            gx = float(t.get("center_x", t.get("x", 0.0)))
            gy = float(t.get("center_y", t.get("y", 0.0)))
            r = float(t.get("crown_radius_m", 2.0))
            all_coords_for_bbox.append((gx, gy))
            msp.add_circle((round(gx, 3), round(gy, 3)), radius=max(r, 1.0), dxfattribs={"layer": "ARBORI", "color": colors.GREEN})
            msp.add_point((round(gx, 3), round(gy, 3)), dxfattribs={"layer": "ARBORI", "color": colors.GREEN})

        # 5. Export Poles & Towers -> STALPI
        poles = categories_dict.get("STALPI_TURNURI", [])
        for p in poles:
            gx = float(p.get("center_x", p.get("x", 0.0)))
            gy = float(p.get("center_y", p.get("y", 0.0)))
            h = float(p.get("height_m", 0.0))
            st_type = p.get("type", "Stalp")
            all_coords_for_bbox.append((gx, gy))
            msp.add_circle((round(gx, 3), round(gy, 3)), radius=1.0, dxfattribs={"layer": "STALPI", "color": colors.CYAN})
            msp.add_point((round(gx, 3), round(gy, 3)), dxfattribs={"layer": "STALPI", "color": colors.CYAN})
            if include_labels:
                msp.add_text(
                    f"{st_type} (H={h:.1f}m)",
                    dxfattribs={"layer": "TEXTE", "height": 1.0, "color": colors.WHITE}
                ).set_placement((round(gx + 1.2, 3), round(gy, 3)), align=ezdxf.enums.TextEntityAlignment.BOTTOM_LEFT)

        # 6. Automatic PAD Coordinate Table Drawing
        if draw_pad_table and pad_table_entries and all_coords_for_bbox:
            max_x = max(pt[0] for pt in all_coords_for_bbox)
            max_y = max(pt[1] for pt in all_coords_for_bbox)
            table_origin_x = max_x + 8.0
            table_origin_y = max_y

            # Limit table to first 35 points to avoid drawing thousands of rows in complex AOIs
            display_entries = pad_table_entries[:35]
            self._draw_pad_coordinate_table(
                msp,
                display_entries,
                origin_x=table_origin_x,
                origin_y=table_origin_y,
                table_title="INVENTAR COORDONATE PAD (ORDINUL ANCPI 600/2023)"
            )

        doc.saveas(output_dxf_path)
        return output_dxf_path

    def export_to_cp_file(
        self,
        categories_dict: Dict[str, List[Dict[str, Any]]],
        output_cp_path: str
    ) -> str:
        """
        Exports vector data into standard TopoLT / ANCPI eTerra interchange .CP text file.
        Format: Point index, X (North), Y (East), Z (Elevation), Code (1CC/2CC/CP).
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_cp_path)), exist_ok=True)
        lines = [
            "; =====================================================================",
            "; StratumRO Cadastre & TopoLT Interchange File (.cp)",
            "; Standard conform Ordinul ANCPI nr. 600/2023",
            "; Sistem Proiectie: Stereo 70 (EPSG:3844) / Marea Neagra 1975 (EPSG:5781)",
            "; Format: Nr_Pct, X_Nord, Y_Est, Z_Cota, Cod_Layer",
            "; ====================================================================="
        ]

        pt_counter = 1

        # 1. Cladiri Principale (1CC)
        main_buildings = categories_dict.get("CLADIRI_HIBRID") or categories_dict.get("CLADIRI_PRINCIPALE", [])
        for b_i, b in enumerate(main_buildings, start=1):
            polys = _extract_polygons(b.get("geometry"))
            lines.append(f"\n[CONSTRUCTIE_1CC_C{b_i}]")
            for poly in polys:
                coords = list(poly.exterior.coords)[:-1]
                for pt in coords:
                    gx, gy = round(pt[0], 3), round(pt[1], 3)
                    lines.append(f"{pt_counter},{gx:.3f},{gy:.3f},0.000,1CC")
                    pt_counter += 1

        # 2. Anexe Gospodaresti (2CC)
        outbuildings = categories_dict.get("ANEXE_GOSPODARESTI", [])
        for a_i, a in enumerate(outbuildings, start=1):
            polys = _extract_polygons(a.get("geometry"))
            lines.append(f"\n[ANEXA_2CC_A{a_i}]")
            for poly in polys:
                coords = list(poly.exterior.coords)[:-1]
                for pt in coords:
                    gx, gy = round(pt[0], 3), round(pt[1], 3)
                    lines.append(f"{pt_counter},{gx:.3f},{gy:.3f},0.000,2CC")
                    pt_counter += 1

        with open(output_cp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return output_cp_path

    def export_buildings_to_dxf(
        self,
        buildings: List[Dict[str, Any]],
        output_dxf_path: str,
        include_labels: bool = True,
        topolt_mode: bool = False
    ) -> str:
        """Helper for single building list export."""
        return self.export_multicategory_to_dxf(
            {"CLADIRI_PRINCIPALE": buildings},
            output_dxf_path,
            include_labels=include_labels,
            topolt_mode=topolt_mode
        )
