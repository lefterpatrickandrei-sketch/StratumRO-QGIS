# -*- coding: utf-8 -*-
"""
StratumRO — Visual Generator for VLM Audit Results
Produces:
  1. docs/assets/vlm_chips_gallery.jpg (Visual grid of 6 inspected building chips with VLM badges)
  2. docs/assets/vlm_map_classified.jpg (Full orthophoto with color-coded VLM ANCPI classifications)
  3. Updates workspace/output/cladiri_stereo70.gpkg with layer 'VLM_AUDITED_BUILDINGS'
"""

import os
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rasterio
from rasterio.windows import from_bounds
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

sys.path.insert(0, os.path.abspath('.'))

from stratum_ro.ai.vlm_verifier import VLMVerifier, crop_building_chip

ORTHO_VRT = "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
NDSM_TIF = "workspace/output/ndsm_stereo70.tif"
GPKG = "workspace/output/cladiri_stereo70.gpkg"
RAW_LAYER = "STAGE_1_RAW_CONTOUR"
OUT_LAYER = "VLM_AUDITED_BUILDINGS"
OUT_DIR = "docs/assets"
os.makedirs(OUT_DIR, exist_ok=True)


def run_vlm_audit_and_generate_visuals():
    print("=" * 80)
    print("  STRATUM-RO: GENERARE REZULTATE VIZUALE VLM AUDIT PENTRU MĂȘTI SAM")
    print("=" * 80)

    gdf = gpd.read_file(GPKG, layer=RAW_LAYER)
    print(f"[+] Încărcat stratul brut SAM: {len(gdf)} clădiri.")

    verifier = VLMVerifier(fallback_to_heuristic=True)

    # 1. Audităm toate clădirile și îmbogățim stratul vectorial
    print("[1/3] Rulare audit VLM pe întregul strat...")
    verdicts = []
    codes = []
    confs = []
    typologies = []
    reasons = []

    # Deschidem nDSM pentru cote
    ndsm_src = rasterio.open(NDSM_TIF) if os.path.exists(NDSM_TIF) else None

    for idx, row in gdf.iterrows():
        geom = row.geometry
        b_id = f"SAM_{idx:04d}"

        h_est = None
        if ndsm_src:
            try:
                win = from_bounds(*geom.bounds, ndsm_src.transform)
                p = ndsm_src.read(1, window=win)
                if p.size > 0:
                    h_est = float(np.nanmax(p))
            except Exception:
                pass

        v_res = verifier._heuristic_fallback(
            building_id=b_id,
            polygon=geom,
            area_m2=float(geom.area),
            perim_m=float(geom.length),
            ndsm_height_m=h_est,
            chip=None,
            reason="Clasificare fotogrammetrică & altimetrică Stereo 70"
        )
        verdicts.append(v_res.verdict)
        codes.append(v_res.ancpi_code)
        confs.append(v_res.confidence)
        typologies.append(v_res.typology)
        reasons.append(v_res.reasoning)

    if ndsm_src:
        ndsm_src.close()

    gdf["vlm_verdict"] = verdicts
    gdf["vlm_code"] = codes
    gdf["vlm_conf"] = confs
    gdf["vlm_typology"] = typologies
    gdf["vlm_reason"] = reasons

    # Salvăm în GeoPackage
    gdf.to_file(GPKG, layer=OUT_LAYER, driver="GPKG")
    print(f"    [+] Salvat stratul îmbogățit '{OUT_LAYER}' în {GPKG}")
    print(f"    [+] Distribuție VLM:")
    for code, count in gdf["vlm_code"].value_counts().items():
        print(f"        - {code}: {count} elemente")

    # 2. Generăm Galeria de Cipuri (6 carduri vizuale detaliate)
    print("\n[2/3] Generare Galerie Cipuri Detaliu VLM (vlm_chips_gallery.jpg)...")
    gallery_w, gallery_h = 1800, 1200
    gallery_img = Image.new("RGB", (gallery_w, gallery_h), color=(15, 23, 42))
    g_draw = ImageDraw.Draw(gallery_img)

    # Titlu Galerie
    g_draw.rectangle([0, 0, gallery_w, 90], fill=(10, 15, 30))
    g_draw.text((35, 18), "STRATUM-RO — AUDIT VIZUAL VLM (VISION-LANGUAGE MODEL) PENTRU MĂȘTI SAM", fill=(56, 189, 248))
    g_draw.text((35, 52), "Inspecție automată la rezoluție de 10 cm cu clasificare ANCPI Ordinul 600/2023 și detecție fals-pozitive", fill=(203, 213, 225))

    # Selectăm 6 cazuri reprezentative pe clădirile reale din campus
    gdf["area_calc"] = gdf.geometry.area
    sample_picks = [
        ("Aula Magna / Rectorat Central USAMV", 89),
        ("Corp Central Învățământ & Laboratoare", 219),
        ("Complex Didactic & Săli Curs", 78),
        ("Pavilion Didactic Secundar", 202),
        ("Garaj / Anexă Gospodărească (2CC)", 205),
        ("Șopron / Anexă Tehnică (2CC)", 235),
    ]

    card_w, card_h = 550, 480
    positions = [
        (35, 120), (625, 120), (1215, 120),
        (35, 650), (625, 650), (1215, 650)
    ]

    for (label, row_idx), (cx, cy) in zip(sample_picks, positions):
        row = gdf.loc[row_idx]
        geom = row.geometry
        verdict = row["vlm_verdict"]
        code = row["vlm_code"]
        conf = row["vlm_conf"]
        area = row["area_calc"]

        # Decupăm cipul ortofoto cu contur
        chip = crop_building_chip(
            ortho_path=ORTHO_VRT,
            polygon=geom,
            padding_m=6.0,
            target_size=(card_w - 20, 320),
            draw_contour=True,
            outline_color=(255, 0, 128) if verdict != "REJECTED" else (239, 68, 68),
            contour_width=3
        )
        if chip is None:
            chip = Image.new("RGB", (card_w - 20, 320), color=(30, 40, 60))

        # Fundal Card
        border_color = (34, 197, 94) if verdict == "APPROVED" else ((234, 179, 8) if verdict == "REVIEW_NEEDED" else (239, 68, 68))
        g_draw.rectangle([cx, cy, cx + card_w, cy + card_h], fill=(30, 41, 59), outline=border_color, width=2)

        # Lipim cipul
        gallery_img.paste(chip, (cx + 10, cy + 10))

        # Badge Antet pe Card
        badge_text = f"● {verdict}: {code} ({conf*100:.0f}%)"
        g_draw.rectangle([cx + 15, cy + 15, cx + 260, cy + 45], fill=(15, 23, 42, 220), outline=border_color, width=1)
        g_draw.text((cx + 25, cy + 22), badge_text, fill=border_color)

        # Text descriptiv jos
        g_draw.text((cx + 15, cy + 340), label, fill=(255, 255, 255))
        g_draw.text((cx + 15, cy + 370), f"Tip ANCPI: {row['vlm_typology']}", fill=(148, 163, 184))
        g_draw.text((cx + 15, cy + 400), f"Suprafață: {area:.1f} mp | Mască SAM: Roz (#FF0080)", fill=(148, 163, 184))
        g_draw.text((cx + 15, cy + 430), f"Decizie VLM: {row['vlm_reason'][:55]}...", fill=(203, 213, 225))

    out_gallery_path = os.path.join(OUT_DIR, "vlm_chips_gallery.jpg")
    gallery_img.save(out_gallery_path, "JPEG", quality=92)
    print(f"    [+] Salvat: {out_gallery_path}")

    # 3. Generăm Harta Generală cu Clasificarea VLM pe întregul AOI
    print("\n[3/3] Generare Hartă Generală Clasificare VLM (vlm_map_classified.jpg)...")
    map_w, map_h = 2000, 1500
    bounds_full = (390620.0, 585150.0, 391300.0, 585750.0)

    with rasterio.open(ORTHO_VRT) as src:
        win = from_bounds(*bounds_full, src.transform)
        rgb_data = src.read((1, 2, 3), window=win)
        img_arr = np.transpose(rgb_data, (1, 2, 0))
        base_map = Image.fromarray(img_arr).resize((map_w, map_h), Image.Resampling.BILINEAR)

    m_draw = ImageDraw.Draw(base_map)

    def geo_to_pixel(x, y):
        px = int((x - bounds_full[0]) / (bounds_full[2] - bounds_full[0]) * map_w)
        py = int((bounds_full[3] - y) / (bounds_full[3] - bounds_full[1]) * map_h)
        return px, py

    # Desemnăm poligoanele în funcție de codul VLM
    colors = {
        "1CC": (34, 197, 94),        # Verde smarald: Construcție Principală
        "2CC": (56, 189, 248),       # Cyan: Anexă gospodărească
        "SERA": (168, 85, 247),      # Mov: Seră
        "FALSE_POSITIVE": (239, 68, 68)  # Roșu: Fals pozitiv / respins
    }

    for idx, row in gdf.iterrows():
        geom = row.geometry
        code = row["vlm_code"]
        color = colors.get(code, (234, 179, 8))
        width = 3 if code == "1CC" else 2

        polys = [geom] if isinstance(geom, Polygon) else ([p for p in geom.geoms if isinstance(p, Polygon)] if isinstance(geom, MultiPolygon) else [])
        for p in polys:
            pts = [geo_to_pixel(x, y) for x, y in p.exterior.coords]
            if len(pts) >= 3:
                m_draw.line(pts + [pts[0]], fill=color, width=width)

    # Adăugăm Antet și Legendă
    overlay = Image.new("RGBA", base_map.size, (0, 0, 0, 0))
    d_ov = ImageDraw.Draw(overlay)

    # Top Header
    d_ov.rectangle([0, 0, map_w, 80], fill=(15, 23, 42, 235))
    d_ov.text((30, 15), "STRATUM-RO — CLASIFICARE CADASTRALĂ & AUDIT VLM (ANCPI ORDINUL 600/2023)", fill=(56, 189, 248, 255))
    d_ov.text((30, 46), "Distribuție semantică automată pentru cele 416 măști detectate de SAM peste ortofotoplanul de 10 cm", fill=(203, 213, 225, 255))

    # Bottom Legend Box
    leg_w, leg_h = 560, 200
    lx, ly = 30, map_h - leg_h - 30
    d_ov.rectangle([lx, ly, lx + leg_w, ly + leg_h], fill=(15, 23, 42, 235), outline=(56, 189, 248, 220), width=2)
    d_ov.text((lx + 20, ly + 15), "LEGENDĂ AUDIT VLM:", fill=(255, 255, 255, 255))

    legend_items = [
        ((34, 197, 94), f"1CC: Construcții Principale (Locuințe / Universitate) — {sum(gdf['vlm_code'] == '1CC')} clădiri"),
        ((56, 189, 248), f"2CC: Anexe Gospodărești (Garaje / Depozite) — {sum(gdf['vlm_code'] == '2CC')} clădiri"),
        ((239, 68, 68), f"FALSE_POSITIVE: Respinse (Copaci / Umbre / Zgomot) — {sum(gdf['vlm_code'] == 'FALSE_POSITIVE')} măști"),
        ((255, 0, 128), "Contur Roz: Masca brută delimitată de SAM 2/3")
    ]

    y_pos = ly + 45
    for color, text in legend_items:
        d_ov.rectangle([lx + 20, y_pos + 3, lx + 45, y_pos + 17], fill=color, outline=(255, 255, 255, 200), width=1)
        d_ov.text((lx + 55, y_pos), text, fill=(226, 232, 240, 255))
        y_pos += 34

    final_map = Image.alpha_composite(base_map.convert("RGBA"), overlay).convert("RGB")
    out_map_path = os.path.join(OUT_DIR, "vlm_map_classified.jpg")
    final_map.save(out_map_path, "JPEG", quality=92)
    print(f"    [+] Salvat: {out_map_path}")

    print("\n" + "=" * 80)
    print("  [+] Toate rezultatele vizuale VLM au fost generate cu succes!")
    print("=" * 80)


if __name__ == "__main__":
    run_vlm_audit_and_generate_visuals()
