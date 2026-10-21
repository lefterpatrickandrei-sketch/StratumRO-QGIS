"""
overlay_fig1_additions.py - 1:1 Non-Destructive Architecture Diagram Overlay
Preserves 100% of the original Perplexity architecture diagram (all arrows, signs,
directions, texts, boxes, badges, colors, and canvas geometry) and ONLY adds:
1. System 1 Fast Triage (JEV / Laya <35ms) inside L4 box.
2. USAMV 195 GT, stratumro-brain Shared Memory, and Multi-Agent MCP inside Cadastral Knowledge Inputs.
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

    # Fonts
    font_path = "C:/Windows/Fonts/arial.ttf"
    font_l4 = ImageFont.truetype(font_path, 13)
    font_ki = ImageFont.truetype(font_path, 11)

    # Charcoal text color matching original bullets
    text_color = (35, 35, 35, 255)

    # 1. Non-destructive addition in L4 box
    # Fits exactly in the empty band below bullet 3 (y=719) and above bottom bar (y=782)
    l4_text = "• System 1 Fast Triage: JEV / Laya (<35ms on CPU / Edge; UNCERTAIN escalates to VLM)"
    draw.text((823, 744), l4_text, fill=text_color, font=font_l4)

    # 2. Non-destructive additions in Cadastral Knowledge Inputs box
    # Fits inside the empty region between y=560 and y=780, well within x=1560..1790 (KI box ends at 1806)
    ki_bullets = [
        (572, "• Tier 2 GT: 195 USAMV bldgs (30m buffer)"),
        (596, "• Shared Memory: stratumro-brain vault"),
        (620, "• Multi-Agent: Kilo + Antigravity MCP"),
    ]
    for y_pos, bullet in ki_bullets:
        draw.text((1560, y_pos), bullet, fill=text_color, font=font_ki)

    # Save output image
    img.save(out_img_path, format="PNG")
    print(f"Saved faithful 1:1 overlay to: {out_img_path}")

    # Copy to artifact directory for instant viewing
    if artifact_dir.exists():
        dest = artifact_dir / "fig1_architecture_v2_hybrid.png"
        shutil.copy2(out_img_path, dest)
        print(f"Copied to artifact directory: {dest}")


if __name__ == "__main__":
    main()
