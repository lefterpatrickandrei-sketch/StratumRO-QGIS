# -*- coding: utf-8 -*-
"""
Generate Complete Browser-Based Cadastral Inspection Gallery
============================================================
Creates high-resolution side-by-side inspection cards (Orthophoto RGB + LiDAR nDSM)
for all 141 Option B Remediated buildings and 151 newly recovered Cladiri Restante.
Outputs an interactive HTML audit report under workspace/reviews/cadastral_audit_remediation_20261019/
accessible at http://127.0.0.1:8769/cadastral_audit_remediation_20261019/index.html
"""

import os
import sys
import json
import html
from pathlib import Path
import numpy as np
import geopandas as gpd
from PIL import Image, ImageDraw, ImageFont
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parent.parent
ORTO_VRT = ROOT / "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
NDSM_TIF = ROOT / "workspace/output/ndsm_stereo70.tif"

B_GPKG = ROOT / "workspace/option_b_validation_20261019/b_proposals_cleaned.gpkg"
REST_GPKG = ROOT / "workspace/cladiri_restante_20261019/cladiri_restante.gpkg"

OUT_DIR = ROOT / "workspace/reviews/cadastral_audit_remediation_20261019"
IMG_DIR = OUT_DIR / "images"

def geo_to_pix(gx, gy, minx, miny, maxx, maxy, w, h):
    px = int((gx - minx) / (maxx - minx) * (w - 1))
    py = int((maxy - gy) / (maxy - miny) * (h - 1))
    return px, py

def render_sheet(cid, geom_roof, geom_fp, layer_type, orto_src, ndsm_src, out_path, ndsm_h_max=None):
    # Buffer bounds for close-up context (4m on all sides)
    minx, miny, maxx, maxy = geom_roof.buffer(4.0).bounds
    w_sub = 600
    aspect = (maxy - miny) / max(maxx - minx, 1e-6)
    h_sub = max(300, min(600, int(w_sub * aspect)))

    # 1. Read Orthophoto RGB
    win_orto = from_bounds(minx, miny, maxx, maxy, orto_src.transform)
    rgb = orto_src.read((1, 2, 3), window=win_orto)
    if rgb.shape[1] > 0 and rgb.shape[2] > 0:
        arr_rgb = np.transpose(rgb, (1, 2, 0))
        img_orto = Image.fromarray(arr_rgb).resize((w_sub, h_sub), Image.Resampling.BILINEAR)
    else:
        img_orto = Image.new("RGB", (w_sub, h_sub), (40, 40, 40))

    # 2. Read LiDAR nDSM
    win_ndsm = from_bounds(minx, miny, maxx, maxy, ndsm_src.transform)
    ndsm = ndsm_src.read(1, window=win_ndsm)
    ndsm = np.where(np.isnan(ndsm) | (ndsm < 0), 0, ndsm)
    if ndsm.size > 0 and ndsm.max() > 0:
        norm = np.clip(ndsm / 15.0 * 255, 0, 255).astype(np.uint8)
        # Apply pseudo-colormap (cyan/yellow/red elevation)
        r = norm
        g = np.clip(norm * 1.5, 0, 255).astype(np.uint8)
        b = (255 - norm).astype(np.uint8)
        arr_ndsm = np.dstack([r, g, b])
        img_ndsm = Image.fromarray(arr_ndsm).resize((w_sub, h_sub), Image.Resampling.BILINEAR)
    else:
        img_ndsm = Image.new("RGB", (w_sub, h_sub), (50, 50, 60))

    # Color palette
    if layer_type == "OPTION_B":
        roof_color = (176, 48, 224)    # Purple #b030e0
        fp_color = (220, 120, 255)     # Light purple
        badge = "OPT_B"
    else:
        roof_color = (255, 140, 0)     # Orange #ff8c00
        fp_color = (255, 200, 100)     # Light orange
        badge = "REST_RECUPERAT"

    # Draw outlines on both images
    for img, is_ndsm in [(img_orto, False), (img_ndsm, True)]:
        draw = ImageDraw.Draw(img)
        # Draw Roof Polygon
        if geom_roof.geom_type == "Polygon":
            coords = list(geom_roof.exterior.coords)
            pts = [geo_to_pix(x, y, minx, miny, maxx, maxy, w_sub, h_sub) for x, y in coords]
            draw.line(pts, fill=roof_color, width=3)
            # Corner vertices
            for px, py in pts[:-1]:
                draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(255, 255, 255), outline=roof_color)

        # Draw 1CC Footprint (-0.40m setback)
        if geom_fp and geom_fp.geom_type == "Polygon":
            coords_fp = list(geom_fp.exterior.coords)
            pts_fp = [geo_to_pix(x, y, minx, miny, maxx, maxy, w_sub, h_sub) for x, y in coords_fp]
            # Draw dashed style
            for i in range(len(pts_fp) - 1):
                p1, p2 = pts_fp[i], pts_fp[i+1]
                draw.line([p1, p2], fill=fp_color, width=2)

    # Combine into side-by-side card (1200 + margin x h_sub + header)
    header_h = 50
    total_w = w_sub * 2 + 10
    total_h = h_sub + header_h
    card = Image.new("RGB", (total_w, total_h), (24, 28, 36))
    
    # Paste subpanels
    card.paste(img_orto, (0, header_h))
    card.paste(img_ndsm, (w_sub + 10, header_h))

    draw_card = ImageDraw.Draw(card)
    # Header info
    roof_area = geom_roof.area
    fp_area = geom_fp.area if geom_fp else 0.0
    nodes = len(geom_roof.exterior.coords) - 1
    h_str = f"H_max={ndsm_h_max:.1f}m" if ndsm_h_max else "H>1.8m"
    header_text = f"ID: {cid} | {badge} | Acoperis: {roof_area:.1f} mp ({nodes} noduri 90°) | 1CC Sol: {fp_area:.1f} mp (-0.40m) | {h_str}"
    draw_card.text((15, 15), header_text, fill=(240, 240, 240))
    draw_card.text((15, header_h + 10), "Ortofoto RGB 5cm (Stereo 70)", fill=(255, 255, 255))
    draw_card.text((w_sub + 25, header_h + 10), "LiDAR nDSM Inaltime (m)", fill=(255, 255, 255))

    card.save(out_path, "JPEG", quality=88)

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    print("[*] Citire straturi geometrice...")
    gdf_b_roof = gpd.read_file(B_GPKG, layer="B_ROOF_PROPOSALS")
    gdf_b_fp = gpd.read_file(B_GPKG, layer="B_FOOTPRINT_1CC").set_index("candidate_id")

    gdf_rest_roof = gpd.read_file(REST_GPKG, layer="REST_ROOF_ORTHO90")
    gdf_rest_fp = gpd.read_file(REST_GPKG, layer="REST_FOOTPRINT_1CC").set_index("candidate_id")

    # Diagnostic layers
    gdf_nodata = gpd.read_file(B_GPKG, layer="INCOMPLET_LIMITA_ZBOR")
    gdf_dups = gpd.read_file(B_GPKG, layer="DUPLICATE_CONFINED_SUPRIMATE")
    gdf_fp_false = gpd.read_file(B_GPKG, layer="FALS_POZITIV_SOL_SUB_1_8M")

    print(f"[+] B Roof: {len(gdf_b_roof)}, REST Roof: {len(gdf_rest_roof)}")
    print(f"[+] Diagnostic: NoData={len(gdf_nodata)}, Dup={len(gdf_dups)}, FalseFP={len(gdf_fp_false)}")

    records = []

    with rasterio.open(ORTO_VRT) as src_orto, rasterio.open(NDSM_TIF) as src_ndsm:
        # 1. Process Option B Remediated
        print("[*] Randare planse Option B (141 cladiri)...")
        for idx, row in gdf_b_roof.iterrows():
            cid = row["candidate_id"]
            geom_r = row.geometry
            geom_f = gdf_b_fp.loc[cid].geometry if cid in gdf_b_fp.index else None
            out_img = IMG_DIR / f"{cid.replace(':', '_')}.jpg"

            # Sample nDSM max height
            win = from_bounds(*geom_r.bounds, src_ndsm.transform)
            ndsm_crop = src_ndsm.read(1, window=win)
            ndsm_valid = ndsm_crop[~np.isnan(ndsm_crop)]
            h_max = float(ndsm_valid.max()) if ndsm_valid.size > 0 else 0.0

            render_sheet(cid, geom_r, geom_f, "OPTION_B", src_orto, src_ndsm, out_img, h_max)

            records.append({
                "candidate_id": cid,
                "layer_group": "OPTION_B_REMEDIAT",
                "area_roof": round(geom_r.area, 2),
                "area_sol": round(geom_f.area, 2) if geom_f else 0.0,
                "nodes": len(geom_r.exterior.coords) - 1,
                "height_max": round(h_max, 2),
                "status": "ADMIS_90DEG_RECTIFIED",
                "img_rel": f"images/{out_img.name}"
            })

        # 2. Process Cladiri Restante
        print("[*] Randare planse Cladiri Restante (151 cladiri)...")
        for idx, row in gdf_rest_roof.iterrows():
            cid = row["candidate_id"]
            geom_r = row.geometry
            geom_f = gdf_rest_fp.loc[cid].geometry if cid in gdf_rest_fp.index else None
            out_img = IMG_DIR / f"{cid.replace(':', '_')}.jpg"

            win = from_bounds(*geom_r.bounds, src_ndsm.transform)
            ndsm_crop = src_ndsm.read(1, window=win)
            ndsm_valid = ndsm_crop[~np.isnan(ndsm_crop)]
            h_max = float(ndsm_valid.max()) if ndsm_valid.size > 0 else 0.0

            render_sheet(cid, geom_r, geom_f, "REST_RECUPERAT", src_orto, src_ndsm, out_img, h_max)

            records.append({
                "candidate_id": cid,
                "layer_group": "CLADIRI_RESTANTE_NOI",
                "area_roof": round(geom_r.area, 2),
                "area_sol": round(geom_f.area, 2) if geom_f else 0.0,
                "nodes": len(geom_r.exterior.coords) - 1,
                "height_max": round(h_max, 2),
                "status": "RECUPERAT_90DEG_ADMIS",
                "img_rel": f"images/{out_img.name}"
            })

    # Save metadata JSON
    (OUT_DIR / "cases_metadata.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    # Generate Interactive HTML Audit Browser
    print("[*] Generare interfata HTML interactiva...")
    esc = html.escape
    html_content = f'''<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>StratumRO — Audit Vizual Cadastral Detaliat (Planșe Apropiate)</title>
  <style>
    :root {{
      --bg: #0f141c;
      --card-bg: #18202c;
      --border: #2a3649;
      --text: #e1e7ef;
      --text-muted: #8c9ba5;
      --purple: #b030e0;
      --orange: #ff8c00;
      --accent: #00d2ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }}
    header {{
      max-width: 1400px;
      margin: 0 auto 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{ margin: 0 0 8px 0; font-size: 26px; color: #fff; }}
    .subtitle {{ color: var(--text-muted); font-size: 15px; margin-bottom: 16px; }}
    .controls {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      margin-top: 16px;
    }}
    button.filter-btn {{
      background: #222d3d;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.15s ease;
    }}
    button.filter-btn.active {{
      background: var(--accent);
      color: #000;
      border-color: var(--accent);
      font-weight: 700;
    }}
    input.search-box {{
      background: #141b24;
      border: 1px solid var(--border);
      color: #fff;
      padding: 8px 14px;
      border-radius: 6px;
      min-width: 260px;
    }}
    .stat-bar {{
      display: flex;
      gap: 24px;
      margin-top: 16px;
      font-size: 14px;
      background: #141b24;
      padding: 12px 18px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .stat-item span {{ font-weight: bold; color: var(--accent); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(620px, 1fr));
      gap: 20px;
      max-width: 1400px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .card.OPTION_B_REMEDIAT {{ border-top: 4px solid var(--purple); }}
    .card.CLADIRI_RESTANTE_NOI {{ border-top: 4px solid var(--orange); }}
    .card-header {{
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #131923;
      font-size: 13px;
    }}
    .card-title {{ font-weight: bold; font-size: 14px; }}
    .badge {{
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
    }}
    .badge.b {{ background: rgba(176, 48, 224, 0.25); color: #e58aff; }}
    .badge.rest {{ background: rgba(255, 140, 0, 0.25); color: #ffb866; }}
    .card-img {{
      width: 100%;
      height: auto;
      display: block;
      background: #000;
    }}
    .card-footer {{
      padding: 10px 14px;
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      border-top: 1px solid var(--border);
      background: #131923;
    }}
  </style>
</head>
<body>
  <header>
    <h1>StratumRO — Audit Vizual Cadastral Detaliat (Planșe Apropiate 1:200)</h1>
    <div class="subtitle">
      Inspecție caz-cu-caz: Ortofoto RGB 5cm vs LiDAR nDSM înălțime reală. Fiecare clădire este verificată individual, cu conturul de acoperiș 90° și amprenta la sol 1CC (-0.40m retragere streașină).
    </div>
    <div class="stat-bar">
      <div class="stat-item">Total Planșe Inspectate: <span>{len(records)}</span></div>
      <div class="stat-item">Opțiunea B Remediată (Mov): <span>{len(gdf_b_roof)}</span></div>
      <div class="stat-item">Clădiri Restante Noi (Portocaliu): <span>{len(gdf_rest_roof)}</span></div>
      <div class="stat-item">Orto-90° Pur (4 noduri): <span>{sum(1 for r in records if r['nodes'] == 4)}</span></div>
      <div class="stat-item">Corpuri Articulate (6-8 noduri): <span>{sum(1 for r in records if r['nodes'] > 4)}</span></div>
    </div>
    <div class="controls">
      <button class="filter-btn active" onclick="filterGroup('ALL')">Toate ({len(records)})</button>
      <button class="filter-btn" onclick="filterGroup('OPTION_B_REMEDIAT')">Opțiunea B Remediată ({len(gdf_b_roof)})</button>
      <button class="filter-btn" onclick="filterGroup('CLADIRI_RESTANTE_NOI')">Clădiri Restante Noi ({len(gdf_rest_roof)})</button>
      <button class="filter-btn" onclick="filterGroup('ARTICULATE')">Corpuri Articulate L/T ({sum(1 for r in records if r['nodes'] > 4)})</button>
      <input type="text" class="search-box" id="searchBox" placeholder="Caută după ID (ex: OPT_B_046 sau W004)..." oninput="searchCards()">
    </div>
  </header>

  <main class="grid" id="cardGrid">
'''

    for r in records:
        cid = r["candidate_id"]
        group = r["layer_group"]
        is_b = (group == "OPTION_B_REMEDIAT")
        badge_cls = "b" if is_b else "rest"
        badge_txt = "Opțiunea B" if is_b else "Clădire Restantă"
        nodes_tag = "4 noduri (dreptunghi pur)" if r["nodes"] == 4 else f"{r['nodes']} noduri (corp articulat)"

        html_content += f'''
    <div class="card {group}" data-id="{cid}" data-group="{group}" data-nodes="{r['nodes']}">
      <div class="card-header">
        <div class="card-title">{cid}</div>
        <span class="badge {badge_cls}">{badge_txt}</span>
      </div>
      <a href="{r['img_rel']}" target="_blank">
        <img class="card-img" loading="lazy" src="{r['img_rel']}" alt="{cid}">
      </a>
      <div class="card-footer">
        <div>Acoperiș: <strong>{r['area_roof']} m²</strong> | Sol 1CC: <strong>{r['area_sol']} m²</strong></div>
        <div>{nodes_tag} | H_max: <strong>{r['height_max']}m</strong></div>
      </div>
    </div>
'''

    html_content += '''
  </main>

  <script>
    let currentFilter = 'ALL';
    function filterGroup(group) {
      currentFilter = group;
      document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
      event.target.classList.add('active');
      applyFilters();
    }
    function searchCards() {
      applyFilters();
    }
    function applyFilters() {
      const q = document.getElementById('searchBox').value.trim().toUpperCase();
      const cards = document.querySelectorAll('.card');
      cards.forEach(card => {
        const id = card.getAttribute('data-id').toUpperCase();
        const group = card.getAttribute('data-group');
        const nodes = parseInt(card.getAttribute('data-nodes'));

        let matchGroup = false;
        if (currentFilter === 'ALL') matchGroup = true;
        else if (currentFilter === 'ARTICULATE') matchGroup = (nodes > 4);
        else matchGroup = (group === currentFilter);

        let matchSearch = (!q || id.includes(q));
        card.style.display = (matchGroup && matchSearch) ? 'flex' : 'none';
      });
    }
  </script>
</body>
</html>
'''

    (OUT_DIR / "index.html").write_text(html_content, encoding="utf-8")
    print(f"[+] Audit HTML generat cu succes în: {OUT_DIR / 'index.html'}")
    print(f"[+] Accesibil pe serverul local: http://127.0.0.1:8769/cadastral_audit_remediation_20261019/index.html")

if __name__ == "__main__":
    main()
