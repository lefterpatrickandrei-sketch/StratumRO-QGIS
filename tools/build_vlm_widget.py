# -*- coding: utf-8 -*-
"""
Builds the standalone & inline Generative UI HTML widget for VLM inspection.
"""

import base64
import os

art_dir = r"C:\Users\lefpa\.gemini\antigravity\brain\6ce10287-e105-4cfc-a2b5-535c17417cbb"
gallery_path = os.path.join(art_dir, "vlm_chips_gallery.jpg")
map_path = os.path.join(art_dir, "vlm_map_classified.jpg")

with open(gallery_path, "rb") as f:
    b64_gallery = base64.b64encode(f.read()).decode("utf-8")

with open(map_path, "rb") as f:
    b64_map = base64.b64encode(f.read()).decode("utf-8")

html_content = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    .active-tab {{ background: #0284c7; color: #ffffff; }}
  </style>
</head>
<body class="bg-transparent text-slate-100 antialiased p-2">
  <div class="bg-slate-900 border border-slate-700 rounded-xl p-4 shadow-2xl text-slate-100 max-w-full">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
      <div class="flex items-center space-x-2">
        <span class="h-3 w-3 rounded-full bg-emerald-500 animate-pulse"></span>
        <h2 class="font-bold text-sm sm:text-base text-sky-400 tracking-wide">STRATUM-RO — AUDIT VLM & MĂȘTI SAM</h2>
      </div>
      <div class="flex space-x-1">
        <button id="btn-gallery" onclick="showView('gallery')" class="active-tab px-3 py-1 rounded text-xs font-semibold transition">Carduri Inspecție VLM</button>
        <button id="btn-map" onclick="showView('map')" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded text-xs font-semibold transition">Hartă Generală (416 clădiri)</button>
      </div>
    </div>

    <!-- Quick Stat Badges -->
    <div class="grid grid-cols-4 gap-2 mb-3 text-center text-xs">
      <div class="bg-slate-800/80 border border-emerald-500/30 rounded p-1.5">
        <div class="text-emerald-400 font-bold text-sm">406</div>
        <div class="text-slate-400 text-[10px]">1CC (Principale)</div>
      </div>
      <div class="bg-slate-800/80 border border-sky-500/30 rounded p-1.5">
        <div class="text-sky-400 font-bold text-sm">10</div>
        <div class="text-slate-400 text-[10px]">2CC (Anexe / Garaje)</div>
      </div>
      <div class="bg-slate-800/80 border border-purple-500/30 rounded p-1.5">
        <div class="text-purple-400 font-bold text-sm">95%</div>
        <div class="text-slate-400 text-[10px]">Încredere Medie</div>
      </div>
      <div class="bg-slate-800/80 border border-pink-500/30 rounded p-1.5">
        <div class="text-pink-400 font-bold text-sm">SAM 2/3 + VLM</div>
        <div class="text-slate-400 text-[10px]">Pipeline Hibrid</div>
      </div>
    </div>

    <!-- Main Visual Canvas -->
    <div class="relative rounded-lg overflow-hidden border border-slate-800 bg-black flex items-center justify-center" style="height: 330px;">
      <!-- Gallery View -->
      <div id="view-gallery" class="w-full h-full flex flex-col items-center justify-center p-1">
        <img src="data:image/jpeg;base64,{b64_gallery}" alt="Carduri VLM" class="max-h-full max-w-full object-contain rounded shadow-lg" />
      </div>

      <!-- Map View -->
      <div id="view-map" class="w-full h-full hidden flex-col items-center justify-center p-1">
        <img src="data:image/jpeg;base64,{b64_map}" alt="Hartă VLM" class="max-h-full max-w-full object-contain rounded shadow-lg" />
      </div>
    </div>

    <!-- Footer Description -->
    <div class="mt-2 flex items-center justify-between text-[11px] text-slate-400">
      <span>🎯 <strong>Mască Roz:</strong> Contur SAM | 🟢 <strong>1CC:</strong> Locuință/Universitate | 🔵 <strong>2CC:</strong> Anexă</span>
      <span class="text-emerald-400 font-mono">Stereo 70 (EPSG:3844)</span>
    </div>
  </div>

  <script>
    function showView(view) {{
      const vGallery = document.getElementById('view-gallery');
      const vMap = document.getElementById('view-map');
      const btnGallery = document.getElementById('btn-gallery');
      const btnMap = document.getElementById('btn-map');

      if (view === 'gallery') {{
        vGallery.classList.remove('hidden');
        vGallery.classList.add('flex');
        vMap.classList.remove('flex');
        vMap.classList.add('hidden');
        btnGallery.className = 'active-tab px-3 py-1 rounded text-xs font-semibold transition';
        btnMap.className = 'bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded text-xs font-semibold transition';
      }} else {{
        vMap.classList.remove('hidden');
        vMap.classList.add('flex');
        vGallery.classList.remove('flex');
        vGallery.classList.add('hidden');
        btnMap.className = 'active-tab px-3 py-1 rounded text-xs font-semibold transition';
        btnGallery.className = 'bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded text-xs font-semibold transition';
      }}
    }}
  </script>
</body>
</html>
"""

out_html = os.path.join(art_dir, "vlm_viewer.html")
with open(out_html, "w", encoding="utf-8") as f:
    f.write(html_content)

print("[+] Created self-contained generative UI widget:", out_html)
