"""
overlay_fig1_additions.py - 1:1 Non-Destructive Architecture Diagram Overlay
Preserves 100% of the original Perplexity architecture diagram (all arrows, signs,
directions, texts, boxes, badges, colors, and canvas geometry) and ONLY adds:
1. System 1 Fast Triage (JEV / Laya <35ms) inside L4 box, with a wide margin
   strictly before the red badge [WS: VLM | LAPTOP: probe] (no overlap).
2. USAMV 195 GT, stratumro-brain Shared Memory, and Multi-Agent MCP inside
   Cadastral Knowledge Inputs box, strictly within margins.
"""

from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont


def main():
    repo_root = Path(__file__).resolve().parent.parent
    src_img_path = repo_root / "perplexity AI" / "png" / "fig1_architecture.png"
    out_img_path = repo_root / "perplexity AI" / "png" / "fig1_architecture_v2_hybrid.png"
    artifact_dir = Path(r"C:\Users\lefpa\.gemini\antigravity\brain\3664d195-fd57-4ad2-a160-377d4b659f41")

    if not src_img_path.exists():
        raise FileNotFoundError(f"Source image not found: {src_img_path}")

    # Load original image pixel-for-pixel
    img = Image.open(src_img_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Fonts: Segoe UI 13 matches the clean UI typography
    font_path = "C:/Windows/Fonts/segoeui.ttf"
    font_l4 = ImageFont.truetype(font_path, 13)
    font_ki = ImageFont.truetype(font_path, 13)

    # Charcoal text color matching original lines
    text_color = (35, 35, 35, 255)

    # 1. Non-destructive addition in L4 box
    # Starts at x=823 (aligned with lines 1-3), ends at x=1183.
    # The red badge starts at x=1277, providing a generous 94px safety margin with ZERO overlap!
    l4_text = "System 1: JEV / Laya (<35ms CPU triage; UNCERTAIN -> VLM)"
    draw.text((823, 744), l4_text, fill=text_color, font=font_l4)

    # 2. Non-destructive additions in Cadastral Knowledge Inputs box
    # Starts at x=1564, ends at x=1814. Box border is at x=1890 (76px margin).
    ki_bullets = [
        (570, "• Tier 2 GT: 195 USAMV bldgs (30m buffer)"),
        (595, "• Shared Memory: stratumro-brain vault"),
        (620, "• Multi-Agent: Kilo + Antigravity MCP"),
    ]
    for y_pos, bullet in ki_bullets:
        draw.text((1564, y_pos), bullet, fill=text_color, font=font_ki)

    # Save output image
    img.save(str(out_img_path), format="PNG")
    print(f"Saved faithful 1:1 overlay to: {out_img_path}")

    # Copy to artifact directory for instant viewing
    if artifact_dir.exists():
        dest = artifact_dir / "fig1_architecture_v2_hybrid.png"
        shutil.copy2(str(out_img_path), str(dest))
        print(f"Copied to artifact directory: {dest}")


if __name__ == "__main__":
    main()
