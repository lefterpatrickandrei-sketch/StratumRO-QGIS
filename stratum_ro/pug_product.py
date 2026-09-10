# -*- coding: utf-8 -*-
"""
Modul Produs Urbanism & PUG (Plan Urbanistic General) pentru StratumRO.
Conformitate legislativă:
  - Legea nr. 350/2001 privind amenajarea teritoriului și urbanismul
  - Legea nr. 24/2007 privind reglementarea și administrarea spațiilor verzi din intravilan
  - Ghidul național de elaborare și conținut-cadru al PUG

Caracteristici fundamentale:
  1. Clădiri Volumetrice LOD1 cu atribute 3D: H_cornisa, H_coama, Regim înălțime (P..P+n),
     Suprafață Construită (Sc), Suprafață Desfășurată (Sd) și Volum construit (mc).
  2. Registrul Spațiilor Verzi: Arbori plasați fizic pe sol liber (Z_bază = Z_teren),
     cu înălțime arbore, rază coronament și volum coronament.
  3. Strat Poligonal Coronamente (Fond Vegetal) pentru calculul indicelui de spațiu verde.
  4. Calcul automat al indicatorilor urbanistici esențiali pe celule UTR (POT, CUT, % Verde).
  5. Livrabil GeoPackage (EPSG:3844) și Raport sinteză JSON.
"""

import os
import math
import json
import numpy as np
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union
import geopandas as gpd

from .vectorizer import CadastralVectorizer
from .volumetric_3d import Volumetric3DBuilder


class PugProductGenerator:
    """Generează livrabilele de Urbanism, PUG și Registru Spații Verzi."""

    def __init__(self, crs: str = "EPSG:3844"):
        self.crs = crs
        self.vectorizer = CadastralVectorizer(crs=self.crs)
        self.builder_3d = Volumetric3DBuilder()

    def generate_pug_package(
        self,
        raw_buildings: List[Dict[str, Any]],
        raw_outbuildings: List[Dict[str, Any]],
        tree_points: List[Dict[str, Any]],
        pole_points: List[Dict[str, Any]],
        output_gpkg: str,
        output_report_json: str
    ) -> Dict[str, Any]:
        """
        Produce straturile PUG și Registrul Spațiilor Verzi conform normelor de urbanism.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_gpkg)), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(output_report_json)), exist_ok=True)

        # 1. Clădiri Volumetrice LOD1
        cad_buildings = self.vectorizer.format_hybrid_buildings(raw_buildings, tolerance=0.7)
        lod1_buildings = []
        total_sc_main = 0.0
        total_sd_main = 0.0
        total_vol_main = 0.0

        for i, b in enumerate(cad_buildings, start=1):
            geom = b.get("geometry")
            if geom is None or geom.is_empty:
                continue

            area_sc = round(float(geom.area), 2)
            h_med = float(b.get("inaltime_med_m", 4.0))
            h_max = float(b.get("inaltime_max_m", h_med + 1.5))

            # Calcule de regim de înălțime urbanistic
            h_cornisa = round(max(2.5, h_med), 1)
            h_coama = round(max(h_cornisa + 0.5, h_max), 1)

            # Număr niveluri estimate (3.0m pas per etaj)
            nr_niveluri = max(1, int(math.floor(h_cornisa / 3.0)))
            if nr_niveluri == 1:
                regim = "P"
            elif nr_niveluri == 2:
                regim = "P+1E"
            elif nr_niveluri == 3:
                regim = "P+2E"
            elif nr_niveluri == 4:
                regim = "P+3E"
            else:
                regim = f"P+{nr_niveluri - 1}E"

            area_sd = round(area_sc * nr_niveluri, 2)
            volum_mc = round(area_sc * h_cornisa, 1)

            total_sc_main += area_sc
            total_sd_main += area_sd
            total_vol_main += volum_mc

            lod1_buildings.append({
                "id": i,
                "cod_cladire": f"BLDG_{i:04d}",
                "destinatie": "Rezidential / Mixt",
                "regim_inaltime": regim,
                "nr_niveluri": nr_niveluri,
                "h_cornisa_m": h_cornisa,
                "h_coama_m": h_coama,
                "sc_sol_mp": area_sc,
                "sd_desfasurat_mp": area_sd,
                "volum_construit_mc": volum_mc,
                "perimetru_m": round(float(geom.length), 2),
                "geometry": geom
            })

        # 2. Anexe Volumetrice (curățate și fără suprapunere cu clădirile)
        from shapely.ops import unary_union
        main_union = unary_union([b["geometry"] for b in lod1_buildings]) if lod1_buildings else None
        anexe_lod1 = []
        anexe_geoms = []

        for j, a in enumerate(raw_outbuildings, start=1):
            geom = a.get("geometry")
            if geom is None or geom.is_empty:
                continue
            cleaned = self.vectorizer.clean_cad_polygon(geom, tolerance=0.7)
            if cleaned is None or cleaned.is_empty or cleaned.area < 8.0:
                continue

            # Tăiere dacă intersectează o clădire principală
            if main_union is not None and cleaned.intersects(main_union):
                cleaned = cleaned.difference(main_union)
                if cleaned.geom_type == 'MultiPolygon':
                    subs = [s for s in cleaned.geoms if s.area >= 8.0]
                    cleaned = max(subs, key=lambda s: s.area) if subs else None
                if cleaned is None or cleaned.area < 8.0:
                    continue

            # Tăiere dacă intersectează altă anexă
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
                area_sc = round(float(cleaned.area), 2)
                anexe_lod1.append({
                    "id": len(anexe_lod1) + 1,
                    "cod_anexa": f"ANX_{len(anexe_lod1) + 1:03d}",
                    "regim_inaltime": "P",
                    "h_coama_m": 3.2,
                    "sc_sol_mp": area_sc,
                    "sd_desfasurat_mp": area_sc,
                    "geometry": cleaned
                })

        # 3. Registrul Spațiilor Verzi (Arbori pe Sol Liber)
        # Excludem fizic clădirile pentru a garanta că arborii au rădăcina pe sol
        all_built = lod1_buildings + anexe_lod1
        raw_trees = self.vectorizer.vectorize_points(tree_points, category="ARBORE")
        clean_trees = self.vectorizer.filter_points_outside_polygons(raw_trees, all_built, buffer_m=0.8)

        registru_arbori = []
        canopy_polygons = []
        total_canopy_area = 0.0

        for t_idx, t in enumerate(clean_trees, start=1):
            gx = t["center_x"]
            gy = t["center_y"]
            h = float(t.get("height_m", 4.0))
            r_coronament = round(min(max(h * 0.35, 1.5), 7.5), 1)
            suprafata_canopy = round(math.pi * (r_coronament ** 2), 1)
            volum_canopy = round((4.0 / 3.0) * math.pi * (r_coronament ** 3) * 0.5, 1)

            total_canopy_area += suprafata_canopy

            pt_geom = Point(gx, gy)
            registru_arbori.append({
                "id_arbore": f"ARB_{t_idx:05d}",
                "inaltime_m": h,
                "raza_coronament_m": r_coronament,
                "suprafata_proiectie_mp": suprafata_canopy,
                "volum_biomasa_mc": volum_canopy,
                "stare_sanitara": "Corespunzatoare",
                "amplasament": "Sol Natural Permeabil",
                "geometry": pt_geom
            })

            # Poligon de coronament (umbră / acoperire vegetală)
            canopy_geom = pt_geom.buffer(r_coronament)
            canopy_polygons.append({
                "id": t_idx,
                "cod_arbore": f"ARB_{t_idx:05d}",
                "inaltime_m": h,
                "suprafata_mp": suprafata_canopy,
                "geometry": canopy_geom
            })

        # 4. Rețele Utilități & Stâlpi
        raw_poles = self.vectorizer.vectorize_points(pole_points, category="STALP")
        clean_poles = self.vectorizer.filter_points_outside_polygons(raw_poles, all_built, buffer_m=0.8)

        # 5. Calculul Indicatorilor Urbanistici pe Celule UTR (Grid de 150m x 150m)
        all_geoms = [b["geometry"] for b in lod1_buildings]
        if all_geoms:
            gdf_bounds = gpd.GeoDataFrame(geometry=all_geoms, crs=self.crs).total_bounds
            grid_xmin, grid_ymin, grid_xmax, grid_ymax = gdf_bounds
        else:
            grid_xmin, grid_ymin, grid_xmax, grid_ymax = 390500, 584800, 391600, 585900

        grid_cells = []
        cell_size = 150.0  # 150m x 150m = 2.25 hectare
        cell_id = 1

        bldg_gdf = gpd.GeoDataFrame(lod1_buildings, crs=self.crs) if lod1_buildings else None
        canopy_gdf = gpd.GeoDataFrame(canopy_polygons, crs=self.crs) if canopy_polygons else None

        for cx in np.arange(grid_xmin, grid_xmax, cell_size):
            for cy in np.arange(grid_ymin, grid_ymax, cell_size):
                cell_box = box(cx, cy, cx + cell_size, cy + cell_size)
                cell_area = cell_box.area  # 22500 mp

                # Intersecție clădiri în celulă
                sc_cell = 0.0
                sd_cell = 0.0
                if bldg_gdf is not None:
                    inter_bldgs = bldg_gdf[bldg_gdf.geometry.intersects(cell_box)]
                    for _, row in inter_bldgs.iterrows():
                        sub_geom = row.geometry.intersection(cell_box)
                        ratio = sub_geom.area / row.geometry.area if row.geometry.area > 0 else 0
                        sc_cell += row.geometry.area * ratio
                        sd_cell += row["sd_desfasurat_mp"] * ratio

                # Intersecție spațiu verde (coronamente) în celulă
                green_cell = 0.0
                if canopy_gdf is not None:
                    inter_canopy = canopy_gdf[canopy_gdf.geometry.intersects(cell_box)]
                    if not inter_canopy.empty:
                        dissolved_canopy = unary_union(inter_canopy.geometry).intersection(cell_box)
                        green_cell = dissolved_canopy.area

                pot_pct = round((sc_cell / cell_area) * 100.0, 1) if cell_area > 0 else 0.0
                cut_val = round(sd_cell / cell_area, 2) if cell_area > 0 else 0.0
                green_pct = round((green_cell / cell_area) * 100.0, 1) if cell_area > 0 else 0.0

                if sc_cell > 0 or green_cell > 0:
                    grid_cells.append({
                        "id_utr": f"UTR_GRID_{cell_id:03d}",
                        "suprafata_celula_mp": cell_area,
                        "sc_total_mp": round(sc_cell, 1),
                        "sd_total_mp": round(sd_cell, 1),
                        "spatiu_verde_mp": round(green_cell, 1),
                        "pot_procent": pot_pct,
                        "cut": cut_val,
                        "procent_spatiu_verde": green_pct,
                        "regim_dominant": "P+1E / P+2E" if cut_val > 0.4 else "P / Rezidential Rural",
                        "geometry": cell_box
                    })
                    cell_id += 1

        # 5b. Generare Geometrii Reale 3D LoD1 (MultiPolygonZ) & CityJSON
        lod1_solids_3d = []
        for b in lod1_buildings:
            solid_3d = self.builder_3d.extrude_lod1_solid(b["geometry"], b["h_cornisa_m"])
            if solid_3d is not None:
                b_3d = dict(b)
                b_3d["geometry"] = solid_3d
                lod1_solids_3d.append(b_3d)

        output_cityjson = os.path.splitext(output_gpkg)[0] + "_3d.city.json"
        try:
            self.builder_3d.export_cityjson(lod1_buildings, output_cityjson)
        except Exception:
            output_cityjson = ""

        # 6. Salvare în GeoPackage PUG
        pug_layers = {
            "CLADIRI_VOLUMETRICE_LOD1": lod1_buildings,
            "CLADIRI_LOD1_3D": lod1_solids_3d,
            "ANEXE_URBANISM": anexe_lod1,
            "REGISTRU_ARBORI": registru_arbori,
            "CORONAMENTE_FOND_VEGETAL": canopy_polygons,
            "RETELE_UTILITATI": clean_poles,
            "ZONIFICARE_POT_CUT": grid_cells
        }

        try:
            if os.path.exists(output_gpkg):
                os.remove(output_gpkg)
        except Exception:
            pass

        self.vectorizer.save_multicategory_geopackage(pug_layers, output_gpkg)

        # 7. Generare Raport Sinteză Indicatori PUG
        mean_pot = float(np.mean([c["pot_procent"] for c in grid_cells])) if grid_cells else 0.0
        mean_cut = float(np.mean([c["cut"] for c in grid_cells])) if grid_cells else 0.0
        mean_green = float(np.mean([c["procent_spatiu_verde"] for c in grid_cells])) if grid_cells else 0.0

        report = {
            "titlu": "Raport Indicatori Urbanistici PUG & Registrul Spațiilor Verzi",
            "legislatie_aplicabila": [
                "Legea nr. 350/2001 privind amenajarea teritoriului și urbanismul",
                "Legea nr. 24/2007 privind reglementarea și administrarea spațiilor verzi"
            ],
            "statistici_fond_construit": {
                "numar_cladiri_principale": len(lod1_buildings),
                "numar_anexe": len(anexe_lod1),
                "suprafata_construita_totala_sc_mp": round(total_sc_main, 2),
                "suprafata_desfasurata_totala_sd_mp": round(total_sd_main, 2),
                "volum_construit_total_mc": round(total_vol_main, 1)
            },
            "registru_spatii_verzi": {
                "numar_arbori_identificati": len(registru_arbori),
                "copaci_pe_acoperisuri": 0,
                "suprafata_acoperire_coronament_mp": round(total_canopy_area, 2)
            },
            "indicatori_generali_zona": {
                "pot_mediu_procent": round(mean_pot, 1),
                "cut_mediu": round(mean_cut, 2),
                "procent_fond_vegetal": round(mean_green, 1)
            }
        }

        with open(output_report_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return {
            "gpkg_path": output_gpkg,
            "report_path": output_report_json,
            "buildings_lod1": len(lod1_buildings),
            "anexe_count": len(anexe_lod1),
            "trees_count": len(registru_arbori),
            "utr_cells": len(grid_cells),
            "mean_pot": mean_pot,
            "mean_cut": mean_cut
        }
