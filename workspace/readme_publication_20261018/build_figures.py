"""Rebuild README figures from committed reports; no inference or image editing.

Run from the repository root with an environment containing matplotlib.
"""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/assets/readme"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                     "svg.fonttype": "none", "svg.hashsalt": "stratumro-readme-20261018",
                     "savefig.facecolor": "white"})
NAVY, TEAL, AMBER, GRAY = "#123047", "#007F86", "#B86A08", "#617181"
sources = ["workspace/reviews/regional_roofs_20261017/scan_v1/report.json",
           "workspace/reviews/regional_roofs_20261017/masked_review_v2/mask_guard_report.json"]
scan, review = [json.loads((ROOT / p).read_text(encoding="utf-8")) for p in sources]
assert scan["windows_scanned"] + scan["windows_no_valid_rgb"] == scan["windows_planned"]
counts = review["counts"]
routes = [counts[k] for k in ("ROOF_CANDIDATES", "OPTICAL_UNKNOWN", "LIKELY_VEGETATION")]
assert sum(routes) == scan["deduplicated_observations"] == 2081

def save(fig, name):
    for ext in ("svg", "png"):
        target = OUT / f"{name}.{ext}"
        metadata = {"Creator": "StratumRO documentation"}
        if ext == "svg":
            metadata["Date"] = None
        fig.savefig(target, dpi=160, bbox_inches="tight", metadata=metadata)
        if ext == "svg":
            target.write_bytes(("\n".join(line.rstrip() for line in target.read_text(encoding="utf-8").splitlines())+"\n").encode("utf-8"))
    plt.close(fig)

fig, ax = plt.subplots(figsize=(13.5, 6.1))
ax.set(xlim=(0, 13.5), ylim=(0, 6.1)); ax.axis("off")
ax.text(.25, 5.7, "STRATUMRO / de la date la livrabile", fontsize=23, weight="bold", color=NAVY)
ax.text(.25, 5.22, "Componente existente în fluxul experimental de acoperișuri", color=GRAY)
boxes = [(0.25, "DATE", "Ortofoto + mască validă\nLiDAR / teren, opțional"),
         (3.65, "PROCESARE", "Citire pe ferestre + SAM2\nGeometrie + context"),
         (7.05, "REVIZIE", "QGIS + identificatori\nDovezi + verdict"),
         (10.45, "LIVRARE", "GIS / CAD\nRapoarte + proveniență")]
for x, title, body in boxes:
    ax.add_patch(FancyBboxPatch((x, 2.85), 2.8, 1.75, boxstyle="round,pad=0.06", facecolor="#EDF6F6", edgecolor=TEAL, linewidth=1.5))
    ax.text(x+.18, 4.12, title, color=TEAL, weight="bold", fontsize=12)
    ax.text(x+.18, 3.47, body, color=NAVY, fontsize=11, linespacing=1.6)
for x in (3.1, 6.5, 9.9):
    ax.add_patch(FancyArrowPatch((x, 3.7), (x+.5, 3.7), arrowstyle="-|>", mutation_scale=18, color=TEAL))
ax.add_patch(FancyBboxPatch((.3, .65), 12.9, 1.4, boxstyle="round,pad=0.06", facecolor="#F7F8FA", edgecolor=GRAY, linestyle="--"))
ax.text(.55, 1.58, "DIRECȚIA PRODUSULUI", weight="bold", color=GRAY)
ax.text(.55, 1.04, "Aplicație desktop proprie • cerere prin prompt • adaptoare către instrumentele geodezului", color=NAVY, fontsize=12)
ax.text(.3, .12, "Fluxul de mai sus există experimental; automatizarea generală și instalatorul desktop sunt obiective.", fontsize=10, color=GRAY)
save(fig, "system_flow")

fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5), gridspec_kw={"width_ratios": [1, 1.35]})
fig.suptitle("Scanare regională / dovezi măsurate, 17 octombrie 2026", fontsize=20, color=NAVY, weight="bold", x=.04, ha="left")
axes[0].barh([1, 0], [67, 77], color=[TEAL, "#A7B2BD"], height=.5)
axes[0].set_yticks([1, 0], ["Cu RGB valid", "Fără RGB valid\nîn nucleu"])
axes[0].set_xlim(0, 95); axes[0].set_xlabel("Ferestre din cele 144 planificate")
for y, val in ((1, 67), (0, 77)):
    axes[0].text(val+2, y, str(val), va="center", weight="bold", color=NAVY)
axes[0].set_title("Acoperire validă: 0,420 km²", loc="left", color=NAVY, pad=18)
axes[1].barh([2, 1, 0], routes, color=[TEAL, AMBER, GRAY], height=.5)
axes[1].set_yticks([2, 1, 0], ["Candidați acoperiș", "Optic incert", "Vegetație probabilă"])
axes[1].set_xlim(0, 1250); axes[1].set_xlabel("Observații, după deduplicare și rutare revizuită")
for y, val in zip([2, 1, 0], routes):
    axes[1].text(val+20, y, str(val), va="center", weight="bold", color=NAVY)
axes[1].set_title("2.081 observații / fără verdict global", loc="left", color=NAVY, pad=18)
for a in axes:
    a.spines[["top", "right", "left"]].set_visible(False)
    a.tick_params(axis="y", length=0); a.set_axisbelow(True); a.grid(axis="x", color="#E5E9EE")
fig.text(.04, .035, "Număr de observații ≠ număr de clădiri validate. Acuratețea și recall-ul nu sunt măsurate.", color=GRAY, fontsize=11)
fig.subplots_adjust(left=.14, right=.97, bottom=.23, top=.77, wspace=.7)
save(fig, "regional_evidence")

fig, ax = plt.subplots(figsize=(10, 4.8))
ax.add_patch(Rectangle((0, 0), 10, 6, facecolor="#007F8622", edgecolor=TEAL, linewidth=2.5, label="Referință: 10 × 6 m"))
ax.add_patch(Rectangle((1, 0), 10, 6, facecolor="#B86A0818", edgecolor=AMBER, linewidth=2.5, linestyle="--", label="Predicție deplasată cu 1 m"))
ax.set(xlim=(-1, 16), ylim=(-1, 8), aspect="equal", xlabel="x [m]", ylabel="y [m]")
ax.text(12, 4.8, "Intersecție: 54 m²\nReuniune: 66 m²\nIoU = 54/66 ≈ 0,818", fontsize=12, color=NAVY, linespacing=1.8)
ax.set_title("Exemplu didactic / suprapunere mare, margini deplasate", loc="left", color=NAVY, fontsize=15, pad=18)
ax.legend(loc="upper left", frameon=False, fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "iou_example")

manifest = {"purpose": "README evidence and illustrative figures; no product execution",
            "source_files": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
            "measured": {"windows": 144, "valid_windows": 67, "empty_windows": 77,
                         "valid_area_m2": scan["valid_core_area_m2"], "revised_routes": routes},
            "illustrative": {"reference_rectangle_m": [10, 6], "shift_m": 1, "iou": 54/66},
            "figures": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(OUT.glob("*")) if p.suffix in (".svg", ".png")}}
(ROOT / "workspace/readme_publication_20261018/figure_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("Created six figure assets; verified window and routing totals against source reports.")
