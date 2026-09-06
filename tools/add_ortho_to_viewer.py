# -*- coding: utf-8 -*-
"""
Integrează ortofotoplanul real sub-decimetric (RGB Stereo 70) în ambele vizualizatoare web:
  - qgis_map_viewer.html
  - qgis_map_inline.html
Adaugă butonul de comutare pentru Ortofoto Aerian (On/Off) și randarea pe canvas sub poligoanele vectoriale.
"""

import os
import sys
import base64
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ortho_jpg = BASE_DIR / "workspace" / "output" / "ortho_basemap.jpg"

if not ortho_jpg.exists():
    print(f"[EROARE] Fișierul {ortho_jpg} nu există!")
    sys.exit(1)

with open(ortho_jpg, "rb") as f:
    b64_data = base64.b64encode(f.read()).decode("utf-8")

data_uri = f"data:image/jpeg;base64,{b64_data}"
print(f"Ortofoto codificat în Base64: {len(data_uri) / 1024:.1f} KB")

# Fișierele țintă
viewer_files = [
    Path(r"C:\Users\lefpa\.gemini\antigravity\brain\932496f8-cca4-49e2-99ec-b8b4c90db783\qgis_map_viewer.html"),
    Path(r"C:\Users\lefpa\.gemini\antigravity\brain\932496f8-cca4-49e2-99ec-b8b4c90db783\qgis_map_inline.html")
]

for html_path in viewer_files:
    if not html_path.exists():
        continue
    
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Adăugăm variabila ORTHO_DATA_URI
    if "const ORTHO_B64 =" not in content:
        content = content.replace('const DATA =', f'const ORTHO_B64 = "{data_uri}";\n    const DATA =')

    # 2. Adăugăm butonul de Ortofoto în Toolbar dacă nu există
    if 'id="btn-toggle-ortho"' not in content:
        toggle_html = '''
      <!-- Ortofoto Toggle Button -->
      <button id="btn-toggle-ortho" class="px-2.5 py-1.5 rounded-md transition text-xs font-semibold flex items-center gap-1.5 bg-emerald-900/80 border border-emerald-500/70 text-emerald-200 hover:bg-emerald-800">
        <span>📸 Ortofoto Aerian (ON)</span>
      </button>'''
        content = content.replace('<!-- Mode Switcher Tabs -->', f'{toggle_html}\n\n      <!-- Mode Switcher Tabs -->')

    # 3. Adăugăm logica Image() și renderOrtho() pe canvas
    if 'let showOrtho = true;' not in content:
        init_ortho_code = '''
    let showOrtho = true;
    const orthoImg = new Image();
    let orthoLoaded = false;
    orthoImg.onload = () => {
      orthoLoaded = true;
      render();
    };
    orthoImg.src = ORTHO_B64;

    const btnToggleOrtho = document.getElementById('btn-toggle-ortho');
    if (btnToggleOrtho) {
      btnToggleOrtho.addEventListener('click', () => {
        showOrtho = !showOrtho;
        if (showOrtho) {
          btnToggleOrtho.className = "px-2.5 py-1.5 rounded-md transition text-xs font-semibold flex items-center gap-1.5 bg-emerald-900/80 border border-emerald-500/70 text-emerald-200 hover:bg-emerald-800";
          btnToggleOrtho.innerHTML = "<span>📸 Ortofoto Aerian (ON)</span>";
        } else {
          btnToggleOrtho.className = "px-2.5 py-1.5 rounded-md transition text-xs font-semibold flex items-center gap-1.5 bg-slate-800 border border-slate-600 text-slate-400 hover:text-white";
          btnToggleOrtho.innerHTML = "<span>📸 Ortofoto Aerian (OFF)</span>";
        }
        render();
      });
    }
'''
        content = content.replace('let currentMode = \'cadastru\';', f'let currentMode = \'cadastru\';\n{init_ortho_code}')

    # 4. Inserăm apelul de randare ortofoto înainte de vectori
    if 'if (showOrtho && orthoLoaded)' not in content:
        draw_ortho_call = '''
      // Desenează Ortofotoplanul Real deasupra grilei, dedesubtul vectorilor
      if (showOrtho && orthoLoaded) {
        const [imgSx, imgSy] = toScreen(DATA.bounds.xmin, DATA.bounds.ymax);
        const [imgEx, imgEy] = toScreen(DATA.bounds.xmax, DATA.bounds.ymin);
        ctx.save();
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(orthoImg, imgSx, imgSy, imgEx - imgSx, imgEy - imgSy);
        ctx.restore();
      }
'''
        content = content.replace("if (currentMode === 'cadastru') {", f"{draw_ortho_call}\n      if (currentMode === 'cadastru') {{")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Actualizat vizualizator cu Ortofoto: {html_path.name}")

print("Toate vizualizatoarele au fost actualizate cu succes!")
