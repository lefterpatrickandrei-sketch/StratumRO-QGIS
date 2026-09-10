# -*- coding: utf-8 -*-
"""
Modul Produs Cadastral (Standard ANCPI) pentru StratumRO.
Conformitate legislativă:
  - Legea cadastrului și publicității imobiliare nr. 7/1996
  - Ordinul ANCPI nr. 700/2014 & Ordinul nr. 600/2023 (Regulament avizare și recepție)

Caracteristici fundamentale:
  1. Geometrie strict 2D a amprentei la sol (Sc) cu regularizare CAD la 90 de grade.
  2. Noduri minime (4 noduri pentru corpuri dreptunghiulare, 6-8 noduri pentru L/T).
  3. REGULĂ FIZICĂ STRICTĂ: Zero arbori pe suprafața sau conturul construcțiilor.
  4. Livrabile standard: GeoPackage (EPSG:3844) și AutoCAD DXF structurat pe layere ANCPI:
     CONSTRUCTII, ANEXE, ARBORI, STALPI, TEXTE.
"""

import os
import math
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
import geopandas as gpd

from .vectorizer import CadastralVectorizer
from .cad_exporter import CadastralDxfExporter


class CadastralProductGenerator:
    """Generează pachetul cadastral oficial conform standardelor ANCPI."""

    def __init__(self, crs: str = "EPSG:3844"):
        self.crs = crs
        self.vectorizer = CadastralVectorizer(crs=self.crs)
        self.dxf_exporter = CadastralDxfExporter(dxf_version="R2010")

    def generate_cadastral_package(
        self,
        raw_buildings: List[Dict[str, Any]],
        raw_outbuildings: List[Dict[str, Any]],
        tree_points: List[Dict[str, Any]],
        pole_points: List[Dict[str, Any]],
        output_gpkg: str,
        output_dxf: str
    ) -> Dict[str, Any]:
        """
        Produce livrabilele cadastrale complete:
        - Filtrare geometrică și ortogonalizare 90° pentru clădiri principale și anexe.
        - Excludere spațială strictă a vegetației din corpul construcțiilor.
        - Generare GPKG multi-strat și DXF ANCPI.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_gpkg)), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_dxf)), exist_ok=True)

        # 1. Formatare și regularizare clădiri principale (C1)
        cad_buildings = self.vectorizer.format_hybrid_buildings(raw_buildings, tolerance=1.4)
        formatted_main = []
        for i, b in enumerate(cad_buildings, start=1):
            h_med = float(b.get("inaltime_med_m", 0.0))
            # Estimare regim de înălțime cadastral (P, P+1E, P+2E)
            if h_med < 4.0:
                regim = "P"
            elif h_med < 7.5:
                regim = "P+1E"
            elif h_med < 10.5:
                regim = "P+2E"
            elif h_med < 14.0:
                regim = "P+3E"
            else:
                regim = f"P+{int(round(h_med / 3.2)) - 1}E"

            b_copy = dict(b)
            b_copy["id_cadastral"] = f"C{i}"
            b_copy["categorie_cadastru"] = "CLADIRE_PRINCIPALA"
            b_copy["regim_inaltime"] = regim
            b_copy["suprafata_sol_mp"] = b.get("area_m2")
            b_copy["validare_ancpi"] = "ADMIS"
            formatted_main.append(b_copy)

        main_union = unary_union([b["geometry"] for b in formatted_main]) if formatted_main else None
        formatted_anexe = []
        anexe_geoms = []

        for j, a in enumerate(raw_outbuildings, start=1):
            geom = a.get("geometry")
            if geom is None or geom.is_empty:
                continue
            cleaned = self.vectorizer.clean_cad_polygon(geom, tolerance=0.7)
            if cleaned is None or cleaned.is_empty or cleaned.area < 8.0:
                continue

            # Tăiere dacă se atinge sau suprapune cu o clădire principală C1
            if main_union is not None and cleaned.intersects(main_union):
                cleaned = cleaned.difference(main_union)
                if cleaned.geom_type == 'MultiPolygon':
                    subs = [s for s in cleaned.geoms if s.area >= 8.0]
                    cleaned = max(subs, key=lambda s: s.area) if subs else None
                if cleaned is None or cleaned.area < 8.0:
                    continue

            # Tăiere dacă se suprapune cu altă anexă
            for prev_ag in anexe_geoms:
                if cleaned.intersects(prev_ag):
                    cleaned = cleaned.difference(prev_ag)
                    if cleaned.geom_type == 'MultiPolygon':
                        subs = [s for s in cleaned.geoms if s.area >= 8.0]
                        cleaned = max(subs, key=lambda s: s.area) if subs else None
                    if cleaned is None or cleaned.area < 8.0:
                        break

            if cleaned is not None and cleaned.is_valid and cleaned.area >= 8.0:
                anexe_geoms.append(cleaned)
                formatted_anexe.append({
                    "id": len(formatted_anexe) + 1,
                    "id_cadastral": f"C{len(formatted_main) + len(formatted_anexe) + 1}",
                    "categorie_cadastru": "ANEXA_GOSPODAREASCA",
                    "regim_inaltime": "P",
                    "suprafata_sol_mp": round(float(cleaned.area), 2),
                    "perimetru_m": round(float(cleaned.length), 2),
                    "vertices": len(cleaned.exterior.coords) - 1,
                    "center_x": round(float(cleaned.centroid.x), 2),
                    "center_y": round(float(cleaned.centroid.y), 2),
                    "geometry": cleaned,
                    "validare_ancpi": "ADMIS"
                })

        # 3. EXCLUDERE SPAȚIALĂ STRICTĂ A COPACILOR DIN CLĂDIRI
        # Unificăm toate construcțiile cu zonă de protecție de 0.8m
        all_bldgs = formatted_main + formatted_anexe
        raw_trees_gdf = self.vectorizer.vectorize_points(tree_points, category="ARBORE")
        raw_poles_gdf = self.vectorizer.vectorize_points(pole_points, category="STALP")

        clean_trees = self.vectorizer.filter_points_outside_polygons(raw_trees_gdf, all_bldgs, buffer_m=0.8)
        clean_poles = self.vectorizer.filter_points_outside_polygons(raw_poles_gdf, all_bldgs, buffer_m=0.8)

        # 4. Salvare GeoPackage Cadastral
        cad_layers = {
            "CONSTRUCTII": formatted_main,
            "ANEXE": formatted_anexe,
            "ARBORI_ALINIAMENT": clean_trees,
            "STALPI_UTILITATI": clean_poles
        }

        try:
            if os.path.exists(output_gpkg):
                os.remove(output_gpkg)
        except Exception:
            pass

        self.vectorizer.save_multicategory_geopackage(cad_layers, output_gpkg)

        # 5. Salvare DXF ANCPI Oficial & TopoLT
        dxf_dict = {
            "CLADIRI_PRINCIPALE": formatted_main,
            "ANEXE_GOSPODARESTI": formatted_anexe,
            "ARBORI": clean_trees,
            "STALPI_TURNURI": clean_poles
        }
        self.dxf_exporter.export_multicategory_to_dxf(
            dxf_dict, output_dxf, include_labels=True, topolt_mode=True, draw_pad_table=True
        )

        output_cp = os.path.splitext(output_dxf)[0] + ".cp"
        self.dxf_exporter.export_to_cp_file(dxf_dict, output_cp)

        return {
            "gpkg_path": output_gpkg,
            "dxf_path": output_dxf,
            "cp_path": output_cp,
            "count_main": len(formatted_main),
            "count_anexe": len(formatted_anexe),
            "count_trees": len(clean_trees),
            "count_poles": len(clean_poles),
            "eliminated_trees_on_roofs": len(raw_trees_gdf) - len(clean_trees)
        }
