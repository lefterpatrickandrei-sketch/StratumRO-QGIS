# -*- coding: utf-8 -*-
"""
StratumRO — Export Screenshots pentru cele 29 de Clădiri Ground Truth
====================================================================
Generează planșe grafice de înaltă rezoluție (screenshot-uri de inspecție)
pentru fiecare din cele 29 de clădiri oficiale din Cluj USAMV:
  - Ortofotoplan RGB de înaltă rezoluție în fundal (context 12m)
  - Contur Oficial Terestru ANCPI (Ground Truth) - Galben
  - Contur AI Vectorizat CAD la 90° (StratumRO Clean) - Cyan
  - Amprentă la Sol Retrasă (Sol ANCPI -40cm) - Portocaliu
  - Noduri CAD numerotate
  - Card tehnic cu IoU, suprafață, abatere Hausdorff, coordonate Stereo 70
  - Scară grafică metrică și orientare spre Nord
  - Galerie HTML de prezentare interactivă (INDEX_29_CLADIRI.html)
"""

import os
import sys
import math
import json
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from shapely.geometry import Polygon, MultiPolygon

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

OUTPUT_DIR = r"C:\Users\lefpa\Downloads\StratumRO_29_Cladiri_Screenshots"
GT_PATH = os.path.join(PROJECT_ROOT, "data", "ground_truth", "tier1_teren.geojson")
GPKG_PATH = os.path.join(PROJECT_ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
ORTHO_VRT = os.path.join(PROJECT_ROOT, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")


def extract_polygons(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    elif isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return []


def generate_screenshots():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 75)
    print("  STRATUM-RO — GENERARE SCREENSHOT-URI PENTRU CELE 29 CLĂDIRI GT")
    print("=" * 75)
    print(f"[*] Destinație: {OUTPUT_DIR}")

    # Încărcare date
    gt_gdf = gpd.read_file(GT_PATH)
    clean_gdf = gpd.read_file(GPKG_PATH, layer="CLADIRI_CADASTRU_CLEAN")
    sol_gdf = gpd.read_file(GPKG_PATH, layer="CLADIRI_SOL_ANCPI")

    print(f"[+] Ground Truth încărcat: {len(gt_gdf)} clădiri")
    print(f"[+] Clădiri AI Clean încărcate: {len(clean_gdf)} entități")
    print(f"[+] Clădiri AI Sol încărcate: {len(sol_gdf)} entități")

    src_ortho = rasterio.open(ORTHO_VRT)

    summary_records = []

    plt.style.use("dark_background")

    for idx, gt_row in gt_gdf.iterrows():
        b_idx = idx + 1
        gt_geom = gt_row.geometry
        gt_id = str(gt_row.get("id", f"REF_{b_idx:03d}"))
        gt_area = float(gt_geom.area)

        # Găsim cel mai bun candidat AI prin IoU
        best_clean = None
        best_clean_iou = 0.0
        for _, c_row in clean_gdf.iterrows():
            c_geom = c_row.geometry
            if gt_geom.intersects(c_geom):
                inter = gt_geom.intersection(c_geom).area
                union = gt_geom.union(c_geom).area
                iou = inter / union if union > 0 else 0
                if iou > best_clean_iou:
                    best_clean_iou = iou
                    best_clean = c_row

        best_sol = None
        best_sol_iou = 0.0
        for _, s_row in sol_gdf.iterrows():
            s_geom = s_row.geometry
            if gt_geom.intersects(s_geom):
                inter = gt_geom.intersection(s_geom).area
                union = gt_geom.union(s_geom).area
                iou = inter / union if union > 0 else 0
                if iou > best_sol_iou:
                    best_sol_iou = iou
                    best_sol = s_row

        # Bounding box extins pentru context
        minx, miny, maxx, maxy = gt_geom.bounds
        if best_clean is not None:
            cminx, cminy, cmaxx, cmaxy = best_clean.geometry.bounds
            minx = min(minx, cminx)
            miny = min(miny, cminy)
            maxx = max(maxx, cmaxx)
            maxy = max(maxy, cmaxy)

        # Păstrăm un aspect ratio echilibrat cu padding minim 10m
        pad_x = max(10.0, (maxx - minx) * 0.25)
        pad_y = max(10.0, (maxy - miny) * 0.25)
        crop_minx = minx - pad_x
        crop_maxx = maxx + pad_x
        crop_miny = miny - pad_y
        crop_maxy = maxy + pad_y

        # Citire fereastră ortofoto
        win = from_bounds(crop_minx, crop_miny, crop_maxx, crop_maxy, src_ortho.transform)
        rgb_data = src_ortho.read(window=win)

        # Matrice extent pentru imshow: [left, right, bottom, top]
        img_extent = [crop_minx, crop_maxx, crop_miny, crop_maxy]

        # Normalizare RGB pentru afișare corectă
        if rgb_data.shape[0] >= 3:
            rgb_img = np.moveaxis(rgb_data[:3], 0, -1)
            # Clipare și conversie
            rgb_img = np.clip(rgb_img, 0, 255).astype(np.uint8)
        else:
            rgb_img = np.zeros((100, 100, 3), dtype=np.uint8)

        # Calcul metrici
        ai_area = best_clean.geometry.area if best_clean is not None else 0.0
        area_diff = ai_area - gt_area
        hausdorff = gt_geom.hausdorff_distance(best_clean.geometry) if best_clean is not None else 999.0
        centroid = gt_geom.centroid

        # Creare figură profesională
        fig = plt.figure(figsize=(14, 10), dpi=150)
        ax = fig.add_axes([0.05, 0.05, 0.90, 0.82])  # [left, bottom, width, height]

        # 1. Randare ortofoto
        ax.imshow(rgb_img, extent=img_extent, origin="upper")

        # 2. Randare Ground Truth (Oficial ANCPI) - Galben
        for p in extract_polygons(gt_geom):
            gx, gy = p.exterior.xy
            ax.plot(gx, gy, color="#FFD700", linewidth=3.0, linestyle="-", label="Teren Cadastru ANCPI (Ground Truth)", zorder=4)
            # Desenare colțuri discrete
            ax.scatter(gx[:-1], gy[:-1], color="#FFD700", s=35, edgecolors="#000000", linewidth=0.8, zorder=5)

        # 3. Randare AI Clean (Acoperiș CAD 90°) - Cyan
        if best_clean is not None:
            for p in extract_polygons(best_clean.geometry):
                cx, cy = p.exterior.xy
                ax.plot(cx, cy, color="#00FFFF", linewidth=2.5, linestyle="-", label="StratumRO CAD 90° (Acoperiș)", zorder=6)
                ax.scatter(cx[:-1], cy[:-1], color="#00FFFF", s=30, edgecolors="#000000", linewidth=0.8, zorder=7)
                # Numerotare primele 15 noduri pentru lizibilitate
                for n_i, (pt_x, pt_y) in enumerate(zip(cx[:-1], cy[:-1])):
                    if n_i < 20:
                        ax.annotate(str(n_i + 1), (pt_x, pt_y), textcoords="offset points", xytext=(4, 4),
                                    fontsize=8, color="#FFFFFF", fontweight="bold",
                                    bbox=dict(boxstyle="circle,pad=0.2", fc="#004488", ec="#00FFFF", lw=0.6), zorder=8)

        # 4. Randare AI Sol ANCPI (Fundație retrasă) - Portocaliu întrerupt
        if best_sol is not None:
            for p in extract_polygons(best_sol.geometry):
                sx, sy = p.exterior.xy
                ax.plot(sx, sy, color="#FF8C00", linewidth=1.8, linestyle="--", label="StratumRO Sol ANCPI (-40cm)", zorder=5)

        # Setări axe
        ax.set_xlim(crop_minx, crop_maxx)
        ax.set_ylim(crop_miny, crop_maxy)
        ax.set_aspect("equal")
        ax.tick_params(axis="both", which="both", colors="#AAAAAA", labelsize=9)
        ax.set_xlabel("Coordonata Est / Y [m] (Stereo 70)", fontsize=10, color="#CCCCCC", labelpad=6)
        ax.set_ylabel("Coordonata Nord / X [m] (Stereo 70)", fontsize=10, color="#CCCCCC", labelpad=6)
        ax.grid(color="#444444", linestyle=":", linewidth=0.6, alpha=0.6)

        # Titlu și Stare
        match_status = "VALIDAT (TP)" if best_clean_iou >= 0.50 else ("PARȚIAL" if best_clean_iou > 0.0 else "OMISIUNE (FN)")
        status_color = "#00FF66" if best_clean_iou >= 0.50 else ("#FFCC00" if best_clean_iou > 0.0 else "#FF3333")

        title_text = f"CLĂDIREA #{b_idx:02d} — {gt_id} | Status: {match_status}"
        fig.text(0.05, 0.94, title_text, fontsize=16, fontweight="bold", color="#FFFFFF")

        sub_title = f"Campus USAMV Cluj-Napoca • Sistem de Proiecție: Stereografic 1970 (EPSG:3844) • GSD Ortofoto: 12 cm"
        fig.text(0.05, 0.91, sub_title, fontsize=10, color="#AAAAAA")

        # Badge status în dreapta sus
        fig.text(0.95, 0.935, f" IoU: {best_clean_iou*100:.1f}% ", fontsize=13, fontweight="bold",
                 color="#000000", ha="right", va="center",
                 bbox=dict(boxstyle="round,pad=0.4", fc=status_color, ec="#FFFFFF", lw=1.2))

        # Caseta Tehnică Informativă (Card stânga jos)
        info_lines = [
            f"• Suprafață Teren GT: {gt_area:.2f} mp",
            f"• Suprafață AI Clean: {ai_area:.2f} mp (Δ: {area_diff:+.2f} mp)",
            f"• Suprapunere IoU:    {best_clean_iou*100:.1f}%",
            f"• Abatere Hausdorff:  {hausdorff:.2f} m" if best_clean is not None else "• Abatere Hausdorff:  N/A",
            f"• Centroid Stereo 70: N={centroid.y:.2f}m, E={centroid.x:.2f}m",
            f"• Noduri GT / AI:     {len(gt_geom.exterior.coords)-1} noduri / {len(best_clean.geometry.exterior.coords)-1 if best_clean is not None else 0} noduri"
        ]
        info_box_text = "\n".join(info_lines)
        ax.text(0.02, 0.03, info_box_text, transform=ax.transAxes, fontsize=9,
                color="#FFFFFF", fontfamily="monospace", va="bottom",
                bbox=dict(boxstyle="square,pad=0.6", fc="#111111", ec="#555555", lw=0.8, alpha=0.88), zorder=10)

        # Săgeată Nord
        ax.annotate("N", xy=(0.95, 0.88), xytext=(0.95, 0.78),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(facecolor="#FFFFFF", edgecolor="#000000", width=3, headwidth=10),
                    ha="center", va="bottom", fontsize=13, fontweight="bold", color="#FFFFFF", zorder=10)

        # Bară de scară metrică (10m)
        scale_len_m = 10.0
        scale_x0 = crop_maxx - pad_x * 0.8 - scale_len_m
        scale_y0 = crop_miny + pad_y * 0.25
        ax.plot([scale_x0, scale_x0 + scale_len_m], [scale_y0, scale_y0], color="#FFFFFF", lw=4.0, zorder=10)
        ax.text(scale_x0 + scale_len_m / 2, scale_y0 + 1.2, f"{int(scale_len_m)} m", color="#FFFFFF",
                fontsize=9, fontweight="bold", ha="center", va="bottom", zorder=10)

        # Legendă
        legend = ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0), framealpha=0.85, facecolor="#111111", edgecolor="#555555", fontsize=9)
        legend.get_frame().set_linewidth(0.8)

        # Salvare fișier
        out_filename = f"Cladirea_{b_idx:02d}_{gt_id}.png"
        out_path = os.path.join(OUTPUT_DIR, out_filename)
        plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#181818")
        plt.close(fig)

        print(f"  [{b_idx:02d}/29] Generat: {out_filename} (IoU: {best_clean_iou*100:.1f}%, Status: {match_status})")

        summary_records.append({
            "index": b_idx,
            "filename": out_filename,
            "id": gt_id,
            "gt_area": round(gt_area, 2),
            "ai_area": round(ai_area, 2),
            "diff_area": round(area_diff, 2),
            "iou": round(best_clean_iou * 100, 1),
            "hausdorff": round(hausdorff, 2) if hausdorff < 900 else None,
            "status": match_status,
            "status_color": status_color
        })

    src_ortho.close()

    # Creare pagină HTML interactivă de inspecție
    html_path = os.path.join(OUTPUT_DIR, "INDEX_29_CLADIRI.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(generate_html_gallery(summary_records))

    print("=" * 75)
    print(f"[OK] Toate cele 29 de screenshot-uri au fost generate cu succes în:")
    print(f"     {OUTPUT_DIR}")
    print(f"[OK] Galerie HTML disponibilă la:")
    print(f"     {html_path}")
    print("=" * 75)


def generate_html_gallery(records):
    tp_count = sum(1 for r in records if r["status"] == "VALIDAT (TP)")
    mean_iou = np.mean([r["iou"] for r in records if r["iou"] > 0])
    cards_html = []
    for r in records:
        card = f"""
        <div class="card">
            <div class="card-header">
                <h3>Clădirea #{r['index']:02d} — {r['id']}</h3>
                <span class="badge" style="background-color: {r['status_color']}; color: #000;">IoU: {r['iou']}%</span>
            </div>
            <a href="{r['filename']}" target="_blank">
                <img src="{r['filename']}" alt="{r['id']}" loading="lazy"/>
            </a>
            <div class="card-body">
                <p><strong>Status:</strong> {r['status']}</p>
                <p><strong>Arie Teren:</strong> {r['gt_area']} mp | <strong>AI:</strong> {r['ai_area']} mp (Δ {r['diff_area']:+} mp)</p>
                <p><strong>Abatere Hausdorff:</strong> {r['hausdorff'] if r['hausdorff'] else 'N/A'} m</p>
            </div>
        </div>
        """
        cards_html.append(card)

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>StratumRO — Inspecție Vizuală 29 Clădiri Ground Truth</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            margin: 0;
            padding: 24px;
        }}
        h1 {{ color: #58a6ff; margin-bottom: 6px; }}
        .header-box {{
            background: #161b22;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #30363d;
            margin-bottom: 24px;
        }}
        .stats {{
            display: flex;
            gap: 24px;
            margin-top: 12px;
        }}
        .stat-item {{
            background: #21262d;
            padding: 10px 18px;
            border-radius: 6px;
            font-weight: bold;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
            gap: 24px;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: hidden;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .card:hover {{
            transform: translateY(-3px);
            border-color: #58a6ff;
        }}
        .card-header {{
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #21262d;
        }}
        .card-header h3 {{
            margin: 0;
            font-size: 15px;
            color: #f0f6fc;
        }}
        .badge {{
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .card img {{
            width: 100%;
            height: auto;
            display: block;
            border-bottom: 1px solid #30363d;
            cursor: pointer;
        }}
        .card-body {{
            padding: 12px 16px;
            font-size: 13px;
            line-height: 1.5;
        }}
        .card-body p {{ margin: 4px 0; }}
    </style>
</head>
<body>
    <div class="header-box">
        <h1>StratumRO — Inspecție Vizuală Cele 29 de Clădiri (Tier 1 Ground Truth)</h1>
        <p>Campus USAMV Cluj-Napoca • Stereo 70 (EPSG:3844) • Ortofotoplan UAV 12 cm GSD</p>
        <div class="stats">
            <div class="stat-item">Total Imobile Oficiale: 29</div>
            <div class="stat-item" style="color: #3fb950;">Validate (IoU &ge; 50%): {tp_count} / 29</div>
            <div class="stat-item" style="color: #58a6ff;">IoU Mediu pe Detecții: {mean_iou:.1f}%</div>
            <div class="stat-item">Format: Planșe High-Res PNG + Metadate</div>
        </div>
    </div>
    <div class="grid">
        {"".join(cards_html)}
    </div>
</body>
</html>
"""


if __name__ == "__main__":
    generate_screenshots()
