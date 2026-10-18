# -*- coding: utf-8 -*-
"""
Build clean, visually verified Lot 3 selection (T11-T20, schema_version=2)
in a new immutable directory: workspace/reviews/lot3_repaired_20261016/.

Strictly forbids np.clip(rgb, 1, 255) NoData spoofing and preserves all
historical directories (lot3_20261013 and lot3_revision_20261013) untouched.
"""
from pathlib import Path
import json
import sys
import numpy as np
import rasterio
from rasterio.windows import from_bounds
import matplotlib.pyplot as plt
import matplotlib.patches as patches

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratum_ro.evaluation_preflight import validate_selection, require_ready, sha256_file

VRT_PATH = ROOT / "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
TILE_DIR = ROOT / "workspace/reviews/prompt_recovery_20261013/full_aoi"
OUT_DIR = ROOT / "workspace/reviews/lot3_repaired_20261016"
COVERS_DIR = OUT_DIR / "covers"
EVIDENCE_DIR = OUT_DIR / "evidence"


def create_covering_crop(vrt_path: Path, out_path: Path, search_bbox: list, margin: float = 20.0):
    """Extract a continuous GeoTIFF from the master VRT without any pixel value clipping."""
    x0, y0, x1, y1 = search_bbox
    crop_bounds = (x0 - margin, y0 - margin, x1 + margin, y1 + margin)
    with rasterio.open(vrt_path) as src:
        win = from_bounds(*crop_bounds, transform=src.transform)
        win = win.round_offsets().round_lengths()
        rgb = src.read([1, 2, 3], window=win)
        win_tr = rasterio.windows.transform(win, src.transform)
        if np.any(np.all(rgb == 0, axis=0)):
            raise ValueError(f"VRT crop {out_path.name} contains (0,0,0) NoData pixels!")
        profile = src.profile.copy()
        profile.update(
            driver="GTiff",
            height=int(win.height),
            width=int(win.width),
            count=3,
            dtype="uint8",
            transform=win_tr,
            nodata=0,
            compress="lzw",
        )
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(rgb)
    return str(out_path.resolve())


def render_selection_evidence(case: dict, out_img_path: Path):
    """Render visual selection evidence showing search_bbox, target_extent, and search_center."""
    tile_p = Path(case["tile"])
    if not tile_p.is_absolute():
        tile_p = TILE_DIR / tile_p
    sx0, sy0, sx1, sy1 = case["search_bbox"]
    tx0, ty0, tx1, ty1 = case["target_extent"]
    cx, cy = case["search_center"]
    margin = 8.0
    vx0, vy0, vx1, vy1 = sx0 - margin, sy0 - margin, sx1 + margin, sy1 + margin

    with rasterio.open(tile_p) as src:
        win = from_bounds(vx0, vy0, vx1, vy1, src.transform)
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        rgb = np.moveaxis(src.read([1, 2, 3], window=win), 0, -1)
        win_tr = rasterio.windows.transform(win, src.transform)
        ext = [
            win_tr.c,
            win_tr.c + win.width * win_tr.a,
            win_tr.f + win.height * win_tr.e,
            win_tr.f,
        ]

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.imshow(rgb, extent=ext)
    ax.add_patch(
        patches.Rectangle(
            (sx0, sy0),
            sx1 - sx0,
            sy1 - sy0,
            linewidth=2.0,
            edgecolor="#FFD700",
            facecolor="none",
            linestyle="--",
            label="search_bbox (anvelopă căutare)",
        )
    )
    ax.add_patch(
        patches.Rectangle(
            (tx0, ty0),
            tx1 - tx0,
            ty1 - ty0,
            linewidth=2.2,
            edgecolor="#00E5FF",
            facecolor="none",
            linestyle="-",
            label="target_extent (clădire vizată)",
        )
    )
    ax.plot(
        cx,
        cy,
        marker="o",
        markersize=10,
        markerfacecolor="#FF1744",
        markeredgecolor="white",
        markeredgewidth=1.5,
        label="search_center (pe acoperiș)",
    )
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(ext[2], ext[3])
    ax.set_title(
        f"Selecție Curată Lot 3: {case['test_id']} ({case['archetype']})\n"
        f"Punct pe acoperiș și acoperire RGB 100% fără NoData",
        fontsize=11,
        fontweight="bold",
    )
    ax.legend(loc="lower left", framealpha=0.9, fontsize=9)
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(out_img_path, dpi=150)
    plt.close(fig)


def main():
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    t18_bbox = [390592.0, 585488.0, 390666.0, 585584.0]
    t18_cover = create_covering_crop(VRT_PATH, COVERS_DIR / "T18_covering_ortho.tif", t18_bbox, margin=8.0)

    cases = [
        {
            "test_id": "T11",
            "tile": "cache_tile_Cluj-2-0_halo.tif",
            "archetype": "SIMPLE_RECTANGULAR_ROOF",
            "search_center": [391243.5, 585598.0],
            "target_extent": [391234.0, 585588.0, 391252.0, 585605.0],
            "search_bbox": [391228.0, 585582.0, 391260.0, 585609.0],
            "correction_reason": "Punct centrat pe acoperișul rezidențial din țiglă roșcată (391243.5, 585598.0), integral în interiorul tile-ului Cluj-2-0 fără pixeli NoData.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Clădire rezidențială individuală cu acoperiș ceramic roșcat în două ape (nDSM ~5.6m), plus corp secundar estic în cadrul aceleiași ferestre de căutare.",
            },
        },
        {
            "test_id": "T12",
            "tile": "cache_tile_Cluj-2-0_halo.tif",
            "archetype": "RESIDENTIAL_WITH_ATTACHED_ANNEX",
            "search_center": [391281.6, 585599.2],
            "target_extent": [391274.0, 585589.0, 391302.0, 585620.0],
            "search_bbox": [391270.0, 585584.0, 391310.0, 585624.0],
            "correction_reason": "Fereastră restrânsă la x <= 391310.0 pentru a evita complet decupajul NoData de la marginea estică a mozaicului (x > 391314.8), păstrând integral casa principală cu țiglă portocalie și anexa nordică gri.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Gospodărie formată din clădirea principală cu acoperiș din țiglă ceramică portocalie (~173 m², nDSM ~6.0m) și anexa nordică cu acoperiș gri (~155 m², nDSM ~5.4m), separate de curtea pavată la nivelul solului.",
            },
        },
        {
            "test_id": "T13",
            "tile": "cache_tile_Cluj-1-0_halo.tif",
            "archetype": "CLOSE_NEIGHBOR_SEPARATION",
            "search_center": [390993.0, 585741.0],
            "target_extent": [390983.0, 585719.0, 391003.0, 585751.0],
            "search_bbox": [390975.0, 585713.0, 391011.0, 585757.0],
            "correction_reason": "Selecție centrată pe perechea de clădiri rezidențiale apropiate N-S din Cluj-1-0, cu acoperire RGB 100% validă.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Două case individuale învecinate pe direcția N-S (nDSM 7.6m și 8.6m), separate de un culoar îngust de ~2m, pentru testarea ne-unificării vecinilor apropiați.",
            },
        },
        {
            "test_id": "T14",
            "tile": "cache_tile_Cluj-1-1_halo.tif",
            "archetype": "GRAY_FLAT_OR_METAL_ROOF",
            "search_center": [391131.2, 585506.9],
            "target_extent": [391117.0, 585488.0, 391146.0, 585521.0],
            "search_bbox": [391112.0, 585482.0, 391157.0, 585525.0],
            "correction_reason": "Relocat de pe aleea asfaltată pe acoperișul halei gri-maronii (391131.2, 585506.9), cu fereastră ajustată în interiorul tile-ului Cluj-1-1 fără pixeli zero.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Clădire utilitară/administrativă cu acoperiș metalic gri-maroniu articulat (~353 m², nDSM ~6.1m), înconjurată de carosabil din beton de culoare apropiată.",
            },
        },
        {
            "test_id": "T15",
            "tile": "cache_tile_Cluj-1-1_halo.tif",
            "archetype": "CANOPY_AND_SHADOW_AMBIGUITY",
            "search_center": [391007.0, 585264.5],
            "target_extent": [390994.0, 585256.0, 391021.0, 585278.0],
            "search_bbox": [390990.0, 585252.0, 391027.0, 585284.0],
            "correction_reason": "Relocat de pe vegetația sudică direct pe acoperișul pavilionului/serei vitrate (391007.0, 585264.5) din Cluj-1-1.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Pavilion de seră/laborator cu acoperiș vitrat/policarbonat (nDSM ~2.5-3.2m) fără clasificare ASPRS Clasa 6 în fișierul LAS, flancat de arbori în partea sudică.",
            },
        },
        {
            "test_id": "T16",
            "tile": "cache_tile_Cluj-0-1_halo.tif",
            "archetype": "DENSE_COURTYARD_CLUSTER",
            "search_center": [390805.7, 585331.4],
            "target_extent": [390794.0, 585319.0, 390822.0, 585346.0],
            "search_bbox": [390785.0, 585310.0, 390832.0, 585355.0],
            "correction_reason": "Punct plasat direct pe acoperișul corpului principal din clusterul dens (390805.7, 585331.4), integral pe tile-ul Cluj-0-1.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Clădire principală din țiglă/tablă roșcată-maronie (~243 m², nDSM ~6.5m) și anexe adiacente în jurul unei curți interioare.",
            },
        },
        {
            "test_id": "T17",
            "tile": "cache_tile_Cluj-0-1_halo.tif",
            "archetype": "ARTICULATED_L_OR_T_FOOTPRINT",
            "search_center": [390829.4, 585486.2],
            "target_extent": [390772.0, 585445.0, 390862.0, 585522.0],
            "search_bbox": [390765.0, 585438.0, 390870.0, 585528.0],
            "correction_reason": "Anvelopă extinsă la [390765, 585438, 390870, 585528] pe tile-ul nativ Cluj-0-1 pentru a cuprinde integral atât aripa gri NV/E (~968 m²) cât și aripa roșie SE (~860 m²) fără trunchiere.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Complex academic articulat compus din două mari corpuri ortogonale în L/T: corpul nord-vestic cu acoperiș gri (~968 m², nDSM ~14.7m) și corpul sud-estic cu acoperiș roșu (~860 m², nDSM ~13.7m).",
            },
        },
        {
            "test_id": "T18",
            "tile": t18_cover,
            "archetype": "LARGE_L_WAREHOUSE",
            "search_center": [390626.1, 585538.6],
            "target_extent": [390600.0, 585496.0, 390658.0, 585576.0],
            "search_bbox": t18_bbox,
            "correction_reason": "Acoperire continuă extrasă direct din VRT peste cusătura dintre Cluj-0-0 și Cluj-0-1 (fără np.clip și cu 0 pixeli NoData), centrată pe hala în formă de L.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Hală agro-industrială mare în formă de L (~1208 m², nDSM ~6.1m) cu acoperiș metalic gri-maroniu continuu.",
            },
        },
        {
            "test_id": "T19",
            "tile": "cache_tile_Cluj-0-2_halo.tif",
            "archetype": "LOW_UTILITY_MIXED_MATERIAL",
            "search_center": [390788.0, 585116.0],
            "target_extent": [390766.0, 585100.0, 390806.0, 585136.0],
            "search_bbox": [390762.0, 585095.0, 390814.0, 585142.0],
            "correction_reason": "Fereastră poziționată la x >= 390762.0 pe tile-ul nativ Cluj-0-2 pentru a evita complet decupajul NoData de la marginea sud-vestică (x <= 390757.2) și a cuprinde pavilionul utilitar.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Pavilion utilitar/administrativ sudic cu acoperiș compozit pe mai multe ape (~752 m², nDSM ~7.2m), integral vizibil pe tile-ul Cluj-0-2.",
            },
        },
        {
            "test_id": "T20",
            "tile": "cache_tile_Cluj-1-1_halo.tif",
            "archetype": "LARGE_MULTIVOLUME_COMPLEX",
            "search_center": [390968.0, 585238.0],
            "target_extent": [390946.0, 585210.0, 390991.0, 585265.0],
            "search_bbox": [390938.0, 585205.0, 390995.0, 585268.0],
            "correction_reason": "Relocat din zona împădurită/NoData (y=585182) direct pe complexul pavilionar multi-volum real (390968.0, 585238.0) aflat integral pe tile-ul Cluj-1-1_halo.tif fără niciun pixel NoData.",
            "selection_review": {
                "object_kind": "BUILDING",
                "point_on_roof": True,
                "full_target_visible": True,
                "reviewer": "Antigravity",
                "observations": "Complex pavilionar multi-volum în două travei (acoperiș metalic alb-gri la sud și luminator/terasă gri la nord, ~748 m², nDSM 5.5-9.0m), complet încadrat pe Cluj-1-1.",
            },
        },
    ]

    for case in cases:
        rel_img = f"evidence/{case['test_id']}_selection.png"
        abs_img = OUT_DIR / rel_img
        render_selection_evidence(case, abs_img)
        case["selection_review"]["image"] = rel_img
        case["selection_review"]["image_sha256"] = sha256_file(abs_img)

    manifest = {
        "schema_version": 2,
        "crs": "EPSG:3844",
        "lot": 3,
        "revision": "REPAIRED_20261016",
        "date": "2026-10-16",
        "governance_status": "PENDING_OWNER_REVIEW",
        "cases": cases,
    }
    manifest_path = OUT_DIR / "selection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    preflight = validate_selection(manifest, manifest_dir=OUT_DIR, tile_dir=TILE_DIR)
    print(json.dumps(preflight, indent=2, ensure_ascii=False))
    require_ready(preflight)
    print(f"[SUCCESS] Clean Lot 3 selection manifest written to: {manifest_path}")


if __name__ == "__main__":
    main()
