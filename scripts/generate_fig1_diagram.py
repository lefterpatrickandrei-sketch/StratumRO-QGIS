# -*- coding: utf-8 -*-
"""
Generates upgraded 1:1 architectural diagram reflecting:
- Unified repository (single git repo)
- System 1 fast local triage (JEV / Laya / heuristic <35ms)
- System 2 VLM Describe-First verification
- Deterministic Geodetic core (Stereo 70 EPSG:3844)
Matches exact resolution (1931 x 1343) and visual design style.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_diagram(output_path="perplexity AI/png/fig1_architecture_v2_hybrid.png"):
    # Create high-res figure matching 1931 x 1343 at 100 dpi
    fig = plt.figure(figsize=(19.31, 13.43), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1931)
    ax.set_ylim(0, 1343)
    ax.axis("off")

    # Background
    ax.add_patch(patches.Rectangle((0, 0), 1931, 1343, facecolor="#ffffff"))

    # Title & Subtitle
    ax.text(965, 1290, "StratumRO-QGIS: Multimodal Architecture v2 (Hybrid Local System 1 + Cloud VLM)",
            ha="center", va="center", fontsize=24, fontweight="bold", color="#111827", fontfamily="sans-serif")
    ax.text(965, 1255, "System 1 proposes & fast-triages (<35ms), deterministic geometry validates in Stereo 70, geodesist approves",
            ha="center", va="center", fontsize=15, color="#4b5563", fontfamily="sans-serif")

    def draw_box(x, y, w, h, title, lines, bg_color, border_color="#374151", badge=None, badge_color="#15803d"):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=12",
                                     facecolor=bg_color, edgecolor=border_color, linewidth=1.8)
        ax.add_patch(box)
        ax.text(x + 20, y + h - 35, title, fontsize=15, fontweight="bold", color="#111827", va="top")
        
        curr_y = y + h - 75
        for line in lines:
            ax.text(x + 20, curr_y, line, fontsize=12, color="#1f2937", va="top")
            curr_y -= 26

        if badge:
            badge_w = len(badge) * 8.5 + 20
            b_box = patches.FancyBboxPatch((x + w - badge_w - 15, y + 15), badge_w, 28,
                                           boxstyle="round,pad=0,rounding_size=6",
                                           facecolor=badge_color, edgecolor="none")
            ax.add_patch(b_box)
            ax.text(x + w - badge_w/2 - 15, y + 29, badge, fontsize=10, fontweight="bold", color="#ffffff", ha="center", va="center")

    def draw_arrow(x1, y1, x2, y2, label=None):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#374151", lw=2, mutation_scale=18))
        if label:
            mx, my = (x1 + x2)/2, (y1 + y2)/2
            ax.text(mx, my + 10, label, fontsize=11, fontweight="bold", color="#374151", ha="center")

    # Inputs Row (Top)
    draw_box(40, 1020, 480, 190, "Orthophoto RGB",
             ["0.15 - 0.20 m GSD tiles", "EPSG:3844 (Stereo 70)", "USAMV Cluj area (242 buildings cataloged)"],
             "#f3f4f6")
    
    draw_box(560, 1020, 520, 190, "LiDAR (LAKI, LAZ)",
             ["ASPRS class 6 / 2 / 3-5", "DTM, nDSM, EPSG:5781 Black Sea Heights", "Height gate: p95 >= 1.8m"],
             "#f3f4f6")

    draw_box(1120, 1020, 420, 190, "Survey + Cadastral Refs",
             ["Tier 1: Legal parcels (ANCPI)", "Tier 2: Validated roofs (195 USAMV)", "Spatial Block Split (30m buffer)"],
             "#f3f4f6")

    draw_box(1570, 450, 320, 760, "Knowledge & Memory",
             ["Docs + Romanian Legal Corpus", "ANCPI Ordinul 600/2023", "Legea 169/2026 (Cod Urbanism)", "Ordinul 904/2023 (PUG GeoPackage)",
              "---------------------------", "Shared Memory Vault:", "stratumro-brain (Git-backed)", "6 Code-map pages (3312 files)",
              "inbox/ -> canon/ governance", "14 Active Agent Skills"],
             "#e0f2fe", border_color="#0284c7")

    # Mid Row: Pipeline Stages
    draw_box(40, 780, 480, 190, "L1 Deterministic Geo Core",
             ["CRS check, tiling, nDSM extraction", "ExG vegetation filter (NDVI/ExG < 0.35)", "Candidate generator, RGB+nDSM tiles"],
             "#dcfce7", badge="WS + LAPTOP", badge_color="#166534")

    draw_box(560, 780, 520, 190, "L2a Trained Roof Segmenter",
             ["RGB + nDSM 4-channel U-Net++ / DeepLab", "Trained on Tier 2 USAMV ground truth", "Targets >85% IoU (eliminates 6.15% flaw)"],
             "#fef3c7", badge="WS train | LAPTOP run", badge_color="#b45309")

    draw_box(1120, 780, 420, 190, "L2b SAM 2.1 Refinement",
             ["SAM 2.0 / 2.1 Tiny (<1.35 GB VRAM)", "Box prompts from nDSM / L2a candidates", "Boundary refinement + sub-pixel mask"],
             "#fef3c7", badge="WS + LAPTOP", badge_color="#b45309")

    # Next Row: System 1 Triage + Fusion & Geometry
    draw_box(40, 520, 720, 210, "L3 Fusion + Deterministic Regularization",
             ["Mask fusion, polygonize, DP simplify 0.25m", "Orientation regularization 90° (vectorizer.py)",
              "Procrustes / SVD auto-snap on tier1_teren", "Area sanity & valid GEOS geometry"],
             "#f3e8ff", badge="WS + LAPTOP", badge_color="#6b21a8")

    draw_box(800, 520, 740, 210, "L4 System 1 Local Triage (<35ms)",
             ["JEV / Laya (322M/421M ONNX) & LightGBM", "Evaluates: Area, 90° rect, LiDAR var, SAM2 conf",
              "p >= 0.85 -> APPROVED | p <= 0.15 -> REJECTED", "Escalates only 10-15% ambiguous cases to System 2"],
             "#fee2e2", badge="LOCAL JEV/LAYA <35ms", badge_color="#991b1b")

    # Lower Row: System 2 VLM Escalation & LLM Orchestration
    draw_box(40, 260, 1500, 220, "L5 System 2 Verification (Fail-Closed) & LLM Orchestration",
             ["VLM Describe-First: Qwen-VL Local (Workstation 24GB) or Gemini Flash Cloud API (Laptop)",
              "Fail-Closed: Timeout 60s / JSON errors -> UNCERTAIN (never silently APPROVED)",
              "32 MCP tools in mcp/stratumro_server.py | Router strictly forbids LLM from CRS & coordinates",
              "Task Cards (tasks/): 4 focused roles (Planner, Builder, Reviewer, Researcher)"],
             "#e0e7ff", border_color="#3730a3", badge="CLOUD + WS FALLBACK", badge_color="#3730a3")

    # Bottom Row: Human Gate & Feedback Loop
    draw_box(40, 40, 720, 180, "L6 Human Gate (QGIS Desktop)",
             ["QGIS Desktop 3.40 (Phase 1 Operational Hub)", "Authorized surveyor inspects & stamps deliverable",
              "'ADMIS' is only an internal test state", "Native DXF (TopoLT/ANCPI) + .CP coordinate export"],
             "#fef9c3", border_color="#ca8a04")

    draw_box(800, 40, 740, 180, "Feedback Loop -> Retraining Store",
             ["Spatial Split Store: Train (126) / Val (22) / Test (31)", "30m buffer zones strictly prevent spatial data leakage",
              "Continuous metrics tracking on frozen USAMV benchmark", "Retrains L2a 4-channel roof segmenter & L4 triage gates"],
             "#fef9c3", border_color="#ca8a04")

    # Connections / Arrows
    draw_arrow(280, 1020, 280, 970)
    draw_arrow(820, 1020, 820, 970)
    draw_arrow(1330, 1020, 1330, 970)
    draw_arrow(280, 780, 280, 730)
    draw_arrow(820, 780, 820, 730)
    draw_arrow(1330, 780, 1170, 730)
    draw_arrow(400, 520, 400, 480, "EVIDENCE PACKET")
    draw_arrow(1170, 520, 1170, 480, "AMBIGUOUS ONLY")
    draw_arrow(400, 260, 400, 220, "VALID CANDIDATES")
    draw_arrow(1170, 260, 1170, 220, "VERIFIED METRICS")

    plt.savefig(output_path, dpi=100, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    print(f"[OK] Generated updated architecture diagram at {output_path}")


if __name__ == "__main__":
    generate_diagram()
