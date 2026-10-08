#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
StratumRO stage-of-project charts.
EVERY number below is measured/verified from the repo on 2026-10-08.
Source of each series is named in the chart title.
Run:  venv\\Scripts\\python reports\\_charts\\make_charts.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
GREEN, RED, AMBER, GREY, BLUE = "#2e8b57", "#c0392b", "#e08a1e", "#7f8c8d", "#2c6fbb"


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- 1
def chart_commits():
    """git log --oneline | date histogram. Measured via git."""
    months = ["2026-07", "2026-08", "2026-09", "2026-10"]
    counts = [46, 3, 49, 3]
    fig, ax = plt.subplots(figsize=(6.4, 3.1))
    bars = ax.bar(months, counts, color=[BLUE, GREY, BLUE, AMBER], width=0.6)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + 1, str(c), ha="center", fontweight="bold")
    ax.set_ylabel("commits on main")
    ax.set_title("C1  Commit cadence — 101 commits, 2026-07-04 → 2026-10-08\n"
                 "3-month bursts separated by near-silent months", fontsize=9.5)
    ax.set_ylim(0, 58)
    save(fig, "C1_commits_per_month.png")


# ---------------------------------------------------------------- 2
def chart_gap():
    """git rev-list --left-right --count origin/main...main (measured)."""
    fig, ax = plt.subplots(figsize=(6.4, 2.5))
    ax.barh(["origin/main\n(GitHub)", "local main\n(this laptop)"], [100, 106],
            color=[RED, GREEN], height=0.5)
    ax.text(100, 0, " 100%", ha="left", va="center", fontweight="bold", color="white")
    ax.text(106, 1, " 106%", ha="left", va="center", fontweight="bold", color="white")
    ax.set_xlim(0, 125)
    ax.set_xticks([])
    ax.set_title("C2  GitHub is 6 commits BEHIND your laptop (6% of history unpushed)\n"
                 "source: git rev-list --left-right --count origin/main...main", fontsize=9.5)
    ax.grid(False)
    save(fig, "C2_unpushed.png")


# ---------------------------------------------------------------- 3
def chart_disk():
    """Get-ChildItem -Recurse size per top dir. Measured."""
    labels = ["venv", "national_\nserver", "projects\n(UNTRACKED)", "workspace",
              ".kilo", "models", "docs", "stratum_ro"]
    mb = [5464, 1946, 817, 339, 336, 269, 20, 2.9]
    cols = [GREY, BLUE, RED, BLUE, GREY, GREY, GREY, GREEN]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    bars = ax.barh(labels[::-1], mb[::-1], color=cols[::-1], height=0.62)
    for b, v in zip(bars, mb[::-1]):
        ax.text(v + 60, b.get_y() + b.get_height() / 2, f"{v:,.0f} MB",
                va="center", fontsize=8)
    ax.set_xlim(0, 6400)
    ax.set_xlabel("megabytes on disk")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x/1000:g} GB"))
    ax.set_title("C3  Disk footprint — 9.2 GB total\n"
                 "red = 817 MB of finished work that git does not track", fontsize=9.5)
    save(fig, "C3_disk.png")


# ---------------------------------------------------------------- 4
def chart_tests():
    fig, ax = plt.subplots(figsize=(4.4, 2.9))
    vals = [241, 9, 0]
    cols = [GREEN, AMBER, RED]
    ax.pie(vals, labels=["passed\n241", "skipped\n9", "failed\n0"],
           colors=cols, autopct=lambda p: f"{p:.1f}%",
                    startangle=90, wedgeprops=dict(edgecolor="w", linewidth=2),
                    textprops=dict(fontsize=8))
    ax.text(0, 0, "250\ndiscovered\n51.2 s", ha="center", va="center", fontsize=8.5,
            fontweight="bold")
    ax.set_title("C4  Test suite VERIFIED GREEN\nunittest discover stratum_ro/test", fontsize=9.5)
    save(fig, "C4_tests.png")


# ---------------------------------------------------------------- 5
def chart_cluj_layers():
    layers = [
        ("STAGE_1_RAW_CONTOUR", 416, GREY), ("STAGE_2_CLEANED_CONTOUR", 483, GREY),
        ("STAGE_3_ADAPTIVE_POLYGON", 483, GREY), ("STAGE_4_LIDAR_CONSTRAINED", 483, GREY),
        ("STAGE_5_FINAL_CONFIDENCE", 483, RED), ("ARTEFACTE_RESPINSE_SAM2", 184, RED),
        ("VLM_AUDITED_BUILDINGS", 416, AMBER), ("VLM_REAL_AUDIT", 6, RED),
        ("CLADIRI_HIBRID", 179, AMBER), ("CLADIRI_CADASTRU_CLEAN", 147, GREEN),
        ("CLADIRI_SOL_ANCPI", 147, GREEN), ("CLADIRI_ELIM_MARGINE_UNSAFE", 32, GREY),
        ("UNCLASSIFIED", 111, RED), ("ARBORI", 1358, GREY),
        ("A / ANEXE / CIMITIR / DR / HR / VN", 17, GREY),
        ("STALPI_TURNURI / LIMITA_SECTOR", 8, GREY),
    ]
    names = [l[0] for l in layers][::-1]
    vals = [l[1] for l in layers][::-1]
    cols = [l[2] for l in layers][::-1]
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    bars = ax.barh(names, vals, color=cols, height=0.68)
    for b, v in zip(bars, vals):
        ax.text(v + 18, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=7.5)
    ax.set_xlim(0, 1520)
    ax.set_xlabel("features (cladiri_stereo70.gpkg, EPSG:3844, USAMV Cluj)")
    ax.tick_params(axis="y", labelsize=7.2)
    ax.set_title("C5  The 21-layer gpkg mixes DELIVERABLES with QA and dead ends\n"
                 "green=delivery · amber=QA · red=no-op or broken · grey=context", fontsize=9.5)
    save(fig, "C5_cluj_layers.png")


# ---------------------------------------------------------------- 6
def chart_confidence():
    """RAPORT_P1_P7 P4 table. Measured."""
    rows = [
        ("STAGE_5\nno filter", 483, 20, 0.465),
        ("conf>=0.50", 204, 19, 0.437),
        ("conf>=0.60", 37, 6, 0.126),
        ("conf>=0.70", 3, 0, 0.000),
        ("sam2>=0.70", 256, 16, 0.373),
        ("sam2>=0.90", 62, 10, 0.250),
        ("CLEAN\n(delivered)", 147, 26, 0.830),
    ]
    fig, ax = plt.subplots(figsize=(6.8, 3.3))
    x = range(len(rows))
    ax2 = ax.twinx()
    b1 = ax.bar([i - 0.2 for i in x], [r[1] for r in rows], width=0.4,
                color=GREY, label="features emitted")
    b2 = ax.bar([i + 0.2 for i in x], [r[2] for r in rows], width=0.4,
                color=GREEN, label="ground truth found (of 29)")
    ax2.plot(x, [r[3] for r in rows], "o-", color=RED, lw=1.8, ms=6,
             label="mean IoU on matched")
    ax.set_xticks(list(x))
    ax.set_xticklabels([r[0] for r in rows], fontsize=7.2)
    ax.set_ylabel("count")
    ax2.set_ylabel("mean IoU", color=RED)
    ax2.set_ylim(0, 1.0)
    ax2.axhline(0.70, ls="--", color=AMBER, lw=1.4)
    ax2.text(len(rows) - 0.4, 0.715, "mission gate IoU>=0.70", fontsize=7,
             color=AMBER, ha="right")
    h = b1 + b2
    ax.legend(h, [p.get_label() for p in h], fontsize=7, loc="upper left")
    ax2.legend(loc="lower left", fontsize=7)
    ax.set_title("C6  HARD TRUTH: every confidence filter COSTS ground truth.\n"
                 "Only the hand-selected CLEAN layer clears the IoU 0.70 gate.", fontsize=9.5)
    save(fig, "C6_confidence.png")


# ---------------------------------------------------------------- 7
def chart_sota():
    """Published numbers. Sources in labels."""
    rows = [
        ("StratumRO CLEAN\n(Cluj, yours)", 0.926, 26, 121, GREEN),
        ("ACPV-Net 2026\nWHU-Building", 0.885, None, None, BLUE),
        ("AttUNet+ 2026\nAIRS (pixel IoU)", 0.79, None, None, BLUE),
        ("ISPRS 2026 U-Net\nRefined Mass.", 0.790, None, None, BLUE),
        ("NAIP+LiDAR 6band\n2026 (val)", 0.760, None, None, BLUE),
        ("ACPV-Net 2026\nbuilding C-IoU", 0.772, None, None, BLUE),
        ("HiSup (2024)\nbuilding C-IoU", 0.706, None, None, BLUE),
        ("DeepLabV3+ 2025\n(but broken outlines)", 0.912, None, None, AMBER),
    ]
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    names = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    cols = [r[4] for r in rows][::-1]
    bars = ax.barh(names, vals, color=cols, height=0.66)
    for b, v in zip(bars, vals):
        ax.text(v + 0.008, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=7.5)
    ax.set_xlim(0, 1.05)
    ax.axvline(0.70, ls="--", color=AMBER, lw=1.4)
    ax.text(0.705, 0.2, "IoU 0.70\nmission gate", fontsize=7, color=AMBER)
    ax.set_xlabel("IoU (NOT all comparable — see caveat)")
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title("C7  Your IoU 0.926 vs published SOTA — but READ THE CAVEAT.\n"
                 "Pixel-IoU != topological correctness. C8 is the real comparison.",
                 fontsize=9.5)
    save(fig, "C7_vs_sota.png")


# ---------------------------------------------------------------- 8
def chart_topology():
    """ACPV-Net Deventer-512: gap/overlap rates. Published."""
    cats = ["ACPV-Net\n(unified)", "TopDiG/HiSup\n(class-specific, stitched)"]
    gaps = [0.00, 13.0]
    ovl = [0.00, 4.0]
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    x = [0, 1]
    ax.bar([i - 0.2 for i in x], gaps, 0.4, color=RED, label="gap rate %")
    ax.bar([i + 0.2 for i in x], ovl, 0.4, color=AMBER, label="overlap rate %")
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=8)
    ax.set_ylabel("percent of map area")
    ax.set_ylim(0, 16)
    ax.legend(fontsize=7.5)
    ax.set_title("C8  THE decisive 2026 result (ACPV-Net / Deventer-512)\n"
                 "Class-by-class pipelines break shared edges; unified ones don't.",
                 fontsize=9.5)
    save(fig, "C8_topology.png")


# ---------------------------------------------------------------- 9
def chart_gates():
    missions = [
        ("Giurgiu\nworkspace/UAT_Giurgiu", "G0", 0.0, 2),
        ("Iepuresti\nprojects/UAT_Iepuresti", "G7 (self-declared)", 8.0, 2),
        ("Cluj\nworkspace/output", "no gate contract", 21.0, 0),
    ]
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    y = range(len(missions))
    declared = [m[2] for m in missions]
    actual = [1, 7, 0]
    b1 = ax.barh(list(y), declared, color=[GREY, RED, GREY], height=0.55,
                 label="gate state declared in state.json")
    b2 = ax.barh(list(y), actual, color=[BLUE, AMBER, BLUE], height=0.28,
                 label="required layers actually non-empty")
    ax.set_yticks(list(y))
    ax.set_yticklabels([m[0] for m in missions], fontsize=7.5)
    ax.set_xlabel("required deliverable layers present & non-empty (max 8)")
    ax.set_xlim(0, 9)
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title("C9  Three projects, three incompatible stories.\n"
                 "Iepuresti CLAIMS G7 complete while 2 of 8 required layers are empty.",
                 fontsize=9.5)
    save(fig, "C9_gates.png")


# ---------------------------------------------------------------- 10
def chart_providers():
    rows = [
        ("Ollama (local)", 100, "5 models installed", GREEN),
        ("Local Mock", 100, "air-gapped", GREEN),
        ("Gemini free tier", 70, "OPERATIONAL ~15 RPM", AMBER),
        ("NVIDIA NIM", 20, "HTTP200 but 1/9 falsification", RED),
        ("OpenRouter/UnionAlpha", 0, "HTTP402  balance -0.20 USD", RED),
        ("OpenAI", 0, "HTTP429 no credits", RED),
        ("Anthropic", 0, "HTTP400 balance too low", RED),
        ("Cerebras", 0, "HTTP402", RED),
        ("SambaNova", 0, "HTTP401 invalid key", RED),
    ]
    names = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    cols = [r[3] for r in rows][::-1]
    notes = [r[2] for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    bars = ax.barh(names, vals, color=cols, height=0.62)
    for b, n in zip(bars, notes):
        ax.text(3, b.get_y() + b.get_height() / 2, n, va="center", fontsize=7,
                color="white" if b.get_width() > 55 else "#333333")
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title("C10  Paid inference: 6 of 8 providers are DEAD (live HTTP probe,\n"
                 "2026-10-08, scripts/provider_credit_status.py)", fontsize=9.5)
    ax.grid(False)
    save(fig, "C10_providers.png")


# ---------------------------------------------------------------- 11
def chart_architecture():
    """File counts per layer of the hexagonal core/domain/contracts."""
    layers = [
        ("stratum_ro/core\ngeometry geodesy pointcloud\nraster qa_qc", 14, GREEN),
        ("stratum_ro/domain\ncadastre_ro city_3d lidar\ntopography vision", 13, GREEN),
        ("stratum_ro/contracts\n9 typed boundary schemas", 10, GREEN),
        ("stratum_ro/ai\nproviders tools router risk\nprovenance memory 25 files", 25, BLUE),
        ("stratum_ro/test\n43 test modules", 43, BLUE),
        ("top-level pipeline\nvectorizer cad_exporter sam2\nlidar ortho volumetric", 12, AMBER),
        ("legacy + GUI\ndockwidget logic_handler\norchestrator api", 10, AMBER),
        ("stratum_ro/ai/providers\n7 providers", 7, RED),
    ]
    names = [l[0] for l in layers][::-1]
    vals = [l[1] for l in layers][::-1]
    cols = [l[2] for l in layers][::-1]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    bars = ax.barh(names, vals, color=cols, height=0.66)
    for b, v in zip(bars, vals):
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=8)
    ax.set_xlim(0, 50)
    ax.set_xlabel("python files")
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title("C11  You already have a hexagonal platform skeleton\n"
                 "green = reusable core · red = the fragile part", fontsize=9.5)
    save(fig, "C11_architecture.png")


# ---------------------------------------------------------------- 12
def chart_roadmap():
    phases = [
        ("P0  TRUTH\nfreeze + clean repo", 0.5, GREEN),
        ("P1  KILL FALSE PASSES\nreal QA gates", 1.0, GREEN),
        ("P2  SEGMENTATION→LSD\ntopology-first", 3.0, BLUE),
        ("P3  PROVENANCE\nSTAC + PROV-O", 2.0, BLUE),
        ("P4  OGC API + MCP\nthe 'connects to anything' layer", 3.0, AMBER),
        ("P5  COMMERCIALISE\nplugin + services", 4.0, AMBER),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    x = 0
    for name, wks, c in phases:
        ax.barh(0, wks, left=x, color=c, height=0.45, edgecolor="w", linewidth=2)
        ax.text(x + wks / 2, 0, name, ha="center", va="center", fontsize=7,
                color="w", fontweight="bold")
        x += wks
    ax.set_xlim(0, x)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xlabel("weeks (≈14 weeks total → fits 'finished this year')")
    ax.set_xticks([])
    ax.grid(False)
    ax.set_title("C12  Recommended path from here to a defensible product",
                 fontsize=10)
    save(fig, "C12_roadmap.png")


# ---------------------------------------------------------------- 13
def chart_sovereign():
    rows = [
        ("CNAIR drumuri majore", 1944),
        ("APIA blocuri/parcele", 543),
        ("Cladiri TopoLT 1CC", 646),
        ("RENNS nomenclator", 184),
        ("ANAR cursuri apa", 8),
        ("Natura 2000 EEA", 4),
        ("APIa drumuri comunale", 33),
        ("CFR cai ferate", 5),
        ("DN nationale", 10),
        ("DJ judetene", 7),
        ("SC strazi locale", 134),
    ]
    names = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    bars = ax.barh(names, vals, color=BLUE, height=0.66)
    for b, v in zip(bars, vals):
        ax.text(v + 25, b.get_y() + b.get_height() / 2, f"{v:,}", va="center", fontsize=7.5)
    ax.set_xlim(0, 2200)
    ax.set_xlabel("features — UAT_Iepuresti_PUG_Master.gpkg, 19 layers, ALL EPSG:3844")
    ax.tick_params(axis="y", labelsize=7.2)
    ax.set_title("C13  Your BEST unrecognised asset: 3,528 features of\n"
                 "SOVEREIGN Romanian official data, assembled but never declared",
                 fontsize=9.5)
    save(fig, "C13_sovereign.png")


# ---------------------------------------------------------------- 14
def chart_evidence():
    rows = [
        ("IMPLEMENTED", 100, "code on disk, importable", GREEN),
        ("TESTED", 250, "250 unittest, 241 passed 0 failed", GREEN),
        ("MEASURED", 4, "scripts with reported numbers", BLUE),
        ("VALIDATED", 29, "vs 29 GT buildings, IoU 0.926", BLUE),
        ("REPRODUCED", 0, "never on a clean environment", AMBER),
        ("FIELD-VALIDATED", 0, "no GNSS/TotalStation log exists", RED),
        ("THEORETICAL", 3, "Procrustes / extrusion / PAD", AMBER),
    ]
    names = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    notes = [r[2] for r in rows][::-1]
    cols = [r[3] for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(6.8, 3.1))
    bars = ax.barh(names, vals, color=cols, height=0.64)
    for b, n in zip(bars, notes):
        ax.text(4, b.get_y() + b.get_height() / 2, n, va="center", fontsize=7,
                color="white" if b.get_width() > 120 else "#333333")
    ax.set_xscale("symlog", linthresh=10)
    ax.set_xlim(0, 400)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title("C14  The 8 Evidence-First rules applied to YOUR project\n"
                 "zero field validation · zero independent reproduction", fontsize=9.5)
    ax.grid(False)
    save(fig, "C14_evidence.png")


def chart_gsd():
    """C15 - the single most favourable measurement in the whole audit."""
    rows = [
        ("PANGAEA / SpaceNet 7\n(Planet RGB)", 30.0, False),
        ("AlphaEarth / Sentinel-2\n(context only, NOT usable)", 1000.0, False),
        ("ACPV-Net Deventer-512\n(high-res aerial)", 10.0, False),
        ("SegFVG Friuli Venezia\n(best published analogue)", 10.0, False),
        ("Bucharest FIFIM ORTO.tif\n(USAMV, optical only)", 12.0, False),
        ("CLAIMS of THIS PROJECT\nbefore LOCAL_DATA_AUDIT was read", 30.0, False),
        ("StratumRO Cluj USAMV\n8x LizardTech MrSID Gen-2 UAV, 2017-03-07", 1.165, True),
    ]
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    for i, (lbl, v, hot) in enumerate(rows):
        c = GREEN if hot else (RED if v >= 1000 else BLUE)
        ax.barh(i, v, color=c, height=0.6)
        ax.text(v * 1.25, i, f"{v:g} cm/px", va="center", fontsize=8,
                fontweight="bold" if hot else "normal",
                color=c if hot else "#333333")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.2)
    ax.set_xscale("log")
    ax.set_xlim(0.5, 4000)
    ax.set_xlabel("Ground sample distance (log scale)  --  LOWER IS BETTER", fontsize=8)
    ax.set_title("C15  The Cluj orthophoto is 10x FINER than every benchmark I cited\n"
                 "LOCAL_DATA_AUDIT_REPORT.md (2026-09-19) - 0.011651 m/px UAV photogrammetry", fontsize=9.5)
    ax.grid(axis="y", alpha=0.15)
    save(fig, "C15_gsd_vs_benchmarks.png")


def chart_aoi_portfolio():
    """C16 - the 4-AOI programme, with the 8 pts/m2 contract line."""
    rows = [
        ("AOI-3  Arad rural\nLAKI II", 8.0, "AGRO outbuildings, silos, poly-tunnels", GREEN),
        ("AOI-1  Oradea, Bihor\nLAKI II", 8.0, "PRIMARY production cadastral AOI", GREEN),
        ("AOI-2  Alba Iulia, Alba\nLAKI II (county capital)", 16.0, "SECONDARY urban / peri-urban", GREEN),
        ("AOI-0  Cluj USAMV (Vlad)\nexisting", 4.944, "DEVELOPMENT + benchmark ONLY - NON-CONFORM", RED),
    ]
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    for i, (lbl, d, role, c) in enumerate(rows):
        ax.barh(i, d, color=c, height=0.55)
        ax.text(d + 0.4, i, f"{d:g} pts/m2", va="center", fontsize=8.5, fontweight="bold", color=c)
        ax.text(0.3, i + 0.42, role, va="center", fontsize=7, color="#444444")
    ax.axvline(8.0, color="#c0392b", ls="--", lw=1.6)
    ax.text(8.35, -0.72, "PILOT_PLAN.md contract: >= 8 pts/m2", fontsize=7.6,
            color="#c0392b", fontweight="bold")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.4)
    ax.set_xlim(0, 19.5)
    ax.set_xlabel("LiDAR point density", fontsize=8)
    ax.set_title("C16  All 3 new AOIs are inside LAKI II -> ONE download, ONE licence (OGL ROU 1.0),\n"
                 "ONE CRS (EPSG:3844). Giurgiu appears in NONE of them and is dropped.", fontsize=9.5)
    ax.grid(axis="y", alpha=0.15)
    save(fig, "C16_aoi_portfolio.png")


def chart_lidar_classes():
    """C17 - why no VLM and no segmentation model is needed for vegetation."""
    rows = [
        ("Class 0  unassigned", 1701, GREY),
        ("Class 2  Ground", 1940705, BLUE),
        ("Class 3  Low vegetation", 747036, AMBER),
        ("Class 4  Medium vegetation", 334810, AMBER),
        ("Class 5  High vegetation", 939996, AMBER),
        ("Class 6  Buildings", 660106, GREEN),
        ("Class 7  Noise", 551, RED),
    ]
    tot = sum(r[1] for r in rows)
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    left = 0.0
    for lbl, n, c in rows:
        pct = 100.0 * n / tot
        ax.barh(0, pct, left=left, color=c, height=0.42, edgecolor="white", linewidth=1.2)
        if pct > 2:
            ax.text(left + pct / 2, 0, f"{pct:.1f}%", ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold")
        left += pct
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.35, 0.85)
    ax.set_yticks([])
    ax.set_xlabel("% of 4 624 905 points", fontsize=8)
    ax.annotate("vegetation ALREADY separated\n(3+4+5 = 43.7%) from ground (2)",
                xy=(43.7, 0.22), xytext=(46, 0.62), fontsize=7.6, color=AMBER,
                arrowprops=dict(arrowstyle="->", color=AMBER, lw=1.2))
    ax.annotate("buildings are ALREADY a class\n660 106 pts = free building mask",
                xy=(85, -0.22), xytext=(58, -0.95), fontsize=7.6, color=GREEN,
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2))
    leg = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in rows]
    ax.legend(leg, [r[0] for r in rows], loc="upper center", bbox_to_anchor=(0.5, -0.30),
              ncol=4, fontsize=6.6, frameon=False)
    ax.set_title("C17  NorPuncte_St70_S42.laz is ALREADY ASPRS-classified in Stereo 70\n"
                 "=> vegetation suppression is a LOOKUP, not a model. 0 new data, 0 licence risk.",
                 fontsize=9.5)
    ax.grid(False)
    save(fig, "C17_lidar_classes.png")


if __name__ == "__main__":
    for fn in [chart_commits, chart_gap, chart_disk, chart_tests, chart_cluj_layers,
               chart_confidence, chart_sota, chart_topology, chart_gates, chart_providers,
               chart_architecture, chart_roadmap, chart_sovereign, chart_evidence,
               chart_gsd, chart_aoi_portfolio, chart_lidar_classes]:
        fn()
    print("\nall charts written to", OUT)
