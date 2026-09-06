import os
import sys
import json
import geopandas as gpd

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

gpkg_path = os.path.abspath(r"workspace\output\cladiri_stereo70.gpkg")

# Read layers
print("Citesc layerele din GeoPackage...")
gdf_hybrid = gpd.read_file(gpkg_path, layer="CLADIRI_HIBRID")
gdf_anexe = gpd.read_file(gpkg_path, layer="ANEXE_GOSPODARESTI")
gdf_arbori = gpd.read_file(gpkg_path, layer="ARBORI")
gdf_stalpi = gpd.read_file(gpkg_path, layer="STALPI_TURNURI")

# Format for web viewer (downsample arbori slightly for ultra smooth 60fps rendering in browser)
sample_arbori = gdf_arbori.sample(n=min(2500, len(gdf_arbori)), random_state=42)

def poly_to_coords(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [[list(p) for p in geom.exterior.coords]]
    elif geom.geom_type == 'MultiPolygon':
        res = []
        for p in geom.geoms:
            res.append([list(c) for c in p.exterior.coords])
        return res
    return []

main_items = []
for _, row in gdf_hybrid.iterrows():
    coords = poly_to_coords(row.geometry)
    if not coords: continue
    main_items.append({
        "id": int(row.get("id", 0)),
        "validare": str(row.get("validare", "CONFIRMAT_HIBRID")),
        "sam2_score": float(row.get("sam2_score", 0.0)),
        "inaltime_med_m": float(row.get("inaltime_med_m", 0.0)),
        "inaltime_max_m": float(row.get("inaltime_max_m", 0.0)),
        "area_m2": float(row.get("area_m2", 0.0)),
        "vertices": int(row.get("vertices", 4)),
        "coords": coords
    })

anexe_items = []
for _, row in gdf_anexe.iterrows():
    coords = poly_to_coords(row.geometry)
    if not coords: continue
    anexe_items.append({
        "id": int(row.get("id", 0)),
        "area_m2": float(row.get("area_m2", 0.0)),
        "coords": coords
    })

tree_items = []
for _, row in sample_arbori.iterrows():
    tree_items.append({
        "x": float(row.geometry.x),
        "y": float(row.geometry.y),
        "h": float(row.get("height_m", 0.0))
    })

pole_items = []
for _, row in gdf_stalpi.iterrows():
    pole_items.append({
        "x": float(row.geometry.x),
        "y": float(row.geometry.y),
        "h": float(row.get("height_m", 0.0)),
        "type": str(row.get("type", "Stalp"))
    })

bounds = {
    "xmin": float(gdf_hybrid.total_bounds[0]),
    "ymin": float(gdf_hybrid.total_bounds[1]),
    "xmax": float(gdf_hybrid.total_bounds[2]),
    "ymax": float(gdf_hybrid.total_bounds[3])
}

map_data = {
    "bounds": bounds,
    "main_buildings": main_items,
    "anexe": anexe_items,
    "trees": tree_items,
    "total_trees_count": len(gdf_arbori),
    "poles": pole_items,
    "stats": {
        "total_main": len(gdf_hybrid),
        "confirmed_sam2": sum(1 for b in main_items if b["validare"] == "CONFIRMAT_HIBRID"),
        "lidar_direct": sum(1 for b in main_items if b["validare"] == "LIDAR_DIRECT"),
        "total_anexe": len(gdf_anexe),
        "total_poles": len(gdf_stalpi)
    }
}

json_str = json.dumps(map_data)

html_content = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StratumRO — Fuziune Hibrida Meta SAM 2 + LiDAR</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      overflow: hidden;
      background: #090d16;
      color: #f8fafc;
    }}
    #map-canvas {{
      display: block;
      width: 100vw;
      height: 100vh;
      cursor: grab;
      background: radial-gradient(circle at center, #111827 0%, #030712 100%);
    }}
    #map-canvas:active {{
      cursor: grabbing;
    }}
    .glass {{
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }}
    .badge-hybrid {{
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.25) 0%, rgba(249, 115, 22, 0.25) 100%);
      border: 1px solid rgba(249, 115, 22, 0.5);
    }}
  </style>
</head>
<body class="relative w-screen h-screen">

  <!-- Header & Toolbar -->
  <header class="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-xl">
    <div class="glass p-4 rounded-xl shadow-2xl flex items-center gap-3">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
        <span class="font-bold text-base tracking-wide text-white">StratumRO — Fuziune Hibridă Meta SAM 2 + LiDAR</span>
      </div>
      <span class="text-xs text-slate-400 border-l border-slate-700 pl-3">Stereo 70 (EPSG:3844)</span>
      <span class="text-xs badge-hybrid text-orange-300 font-semibold px-2 py-0.5 rounded">GPU RTX 4050</span>
    </div>

    <!-- Live Stats Bar -->
    <div class="glass px-4 py-2.5 rounded-xl shadow-xl flex items-center gap-4 text-xs">
      <div class="flex items-center gap-1.5">
        <span class="text-slate-400">Total Clădiri:</span>
        <span class="font-bold text-white">{map_data['stats']['total_main']}</span>
      </div>
      <div class="flex items-center gap-1.5 border-l border-slate-700 pl-3">
        <span class="w-2 h-2 rounded-full bg-red-500"></span>
        <span class="text-slate-400">Dublă Confirmare (SAM 2 + LiDAR):</span>
        <span class="font-bold text-red-400">{map_data['stats']['confirmed_sam2']}</span>
      </div>
      <div class="flex items-center gap-1.5 border-l border-slate-700 pl-3">
        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
        <span class="text-slate-400">LiDAR Direct:</span>
        <span class="font-bold text-amber-400">{map_data['stats']['lidar_direct']}</span>
      </div>
    </div>

    <!-- Layer Toggles -->
    <div class="glass p-3 rounded-xl shadow-xl flex flex-wrap gap-2 text-xs">
      <label class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/80 cursor-pointer border border-red-500/40 text-red-200 transition">
        <input type="checkbox" id="chk-hybrid-confirmed" checked class="accent-red-500">
        <span class="w-2.5 h-2.5 bg-red-500 rounded-sm inline-block"></span>
        <span>Confirmat SAM 2 ({map_data['stats']['confirmed_sam2']})</span>
      </label>

      <label class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/80 cursor-pointer border border-orange-500/40 text-orange-200 transition">
        <input type="checkbox" id="chk-lidar-direct" checked class="accent-orange-500">
        <span class="w-2.5 h-2.5 bg-orange-500 rounded-sm inline-block"></span>
        <span>LiDAR Direct ({map_data['stats']['lidar_direct']})</span>
      </label>

      <label class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/80 cursor-pointer border border-yellow-500/40 text-yellow-200 transition">
        <input type="checkbox" id="chk-anexe" checked class="accent-yellow-500">
        <span class="w-2.5 h-2.5 bg-yellow-400 rounded-sm inline-block"></span>
        <span>Anexe ({map_data['stats']['total_anexe']})</span>
      </label>

      <label class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/80 cursor-pointer border border-emerald-500/40 text-emerald-200 transition">
        <input type="checkbox" id="chk-trees" checked class="accent-emerald-500">
        <span class="w-2.5 h-2.5 bg-emerald-400 rounded-full inline-block"></span>
        <span>Arbori ({map_data['total_trees_count']})</span>
      </label>

      <label class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/80 cursor-pointer border border-cyan-500/40 text-cyan-200 transition">
        <input type="checkbox" id="chk-poles" checked class="accent-cyan-500">
        <span class="w-2.5 h-2.5 bg-cyan-400 rotate-45 inline-block"></span>
        <span>Stâlpi &amp; Turnuri ({map_data['stats']['total_poles']})</span>
      </label>
    </div>
  </header>

  <!-- Zoom & Navigation Controls -->
  <div class="absolute bottom-6 right-6 z-20 flex flex-col gap-2">
    <div class="glass p-1.5 rounded-xl shadow-xl flex flex-col gap-1">
      <button id="btn-zoom-in" class="w-9 h-9 flex items-center justify-center bg-slate-800 hover:bg-slate-700 rounded-lg text-lg font-bold transition">+</button>
      <button id="btn-zoom-out" class="w-9 h-9 flex items-center justify-center bg-slate-800 hover:bg-slate-700 rounded-lg text-lg font-bold transition">−</button>
      <button id="btn-reset" class="w-9 h-9 flex items-center justify-center bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-semibold transition" title="Resetare Zoom">⟲</button>
    </div>
  </div>

  <!-- Object Info Tooltip / Inspector -->
  <div id="info-card" class="absolute bottom-6 left-6 z-20 glass p-4 rounded-xl shadow-xl max-w-sm hidden transition-all">
    <div class="flex justify-between items-start mb-2">
      <h3 id="info-title" class="font-bold text-sm text-white flex items-center gap-2">Detalii Obiect</h3>
      <button id="btn-close-info" class="text-slate-400 hover:text-white text-xs">✕</button>
    </div>
    <div id="info-body" class="text-xs text-slate-300 space-y-1"></div>
  </div>

  <canvas id="map-canvas"></canvas>

  <script>
    const DATA = {json_str};

    const canvas = document.getElementById('map-canvas');
    const ctx = canvas.getContext('2d');

    let width, height;
    function resize() {{
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      render();
    }}
    window.addEventListener('resize', resize);

    // Initial bounding box
    const b = DATA.bounds;
    const geoWidth = b.xmax - b.xmin;
    const geoHeight = b.ymax - b.ymin;

    let zoom = 1.0;
    let panX = 0;
    let panY = 0;

    function resetView() {{
      const padding = 60;
      const scaleX = (width - padding * 2) / geoWidth;
      const scaleY = (height - padding * 2) / geoHeight;
      zoom = Math.min(scaleX, scaleY);
      
      const centerGeoX = (b.xmin + b.xmax) / 2;
      const centerGeoY = (b.ymin + b.ymax) / 2;
      
      panX = width / 2 - centerGeoX * zoom;
      panY = height / 2 + centerGeoY * zoom; // inverted Y for north-up
      render();
    }}

    function toScreen(gx, gy) {{
      return [
        gx * zoom + panX,
        panY - gy * zoom
      ];
    }}

    function toGeo(sx, sy) {{
      return [
        (sx - panX) / zoom,
        (panY - sy) / zoom
      ];
    }}

    function render() {{
      ctx.clearRect(0, 0, width, height);

      // 1. Draw Subtle Grid (Stereo 70, 100m lines)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.lineWidth = 1;
      const gridStep = 100;
      const startX = Math.floor(b.xmin / gridStep) * gridStep;
      const endX = Math.ceil(b.xmax / gridStep) * gridStep;
      const startY = Math.floor(b.ymin / gridStep) * gridStep;
      const endY = Math.ceil(b.ymax / gridStep) * gridStep;

      for (let gx = startX; gx <= endX; gx += gridStep) {{
        const [sx1, sy1] = toScreen(gx, startY);
        const [sx2, sy2] = toScreen(gx, endY);
        ctx.beginPath();
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
        ctx.stroke();
      }}
      for (let gy = startY; gy <= endY; gy += gridStep) {{
        const [sx1, sy1] = toScreen(startX, gy);
        const [sx2, sy2] = toScreen(endX, gy);
        ctx.beginPath();
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
        ctx.stroke();
      }}

      // 2. Draw Trees
      if (document.getElementById('chk-trees').checked) {{
        ctx.fillStyle = 'rgba(52, 211, 153, 0.45)';
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.85)';
        ctx.lineWidth = 1;
        const treeR = Math.max(1.8, 1.8 * zoom * 0.25);
        for (let t of DATA.trees) {{
          const [sx, sy] = toScreen(t.x, t.y);
          if (sx < -20 || sx > width + 20 || sy < -20 || sy > height + 20) continue;
          ctx.beginPath();
          ctx.arc(sx, sy, treeR, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }}
      }}

      // 3. Draw Secondary Buildings / Anexe
      if (document.getElementById('chk-anexe').checked) {{
        ctx.fillStyle = 'rgba(251, 191, 36, 0.55)';
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.95)';
        ctx.lineWidth = 1.2;
        for (let a of DATA.anexe) {{
          for (let poly of a.coords) {{
            ctx.beginPath();
            for (let i = 0; i < poly.length; i++) {{
              const [sx, sy] = toScreen(poly[i][0], poly[i][1]);
              if (i === 0) ctx.moveTo(sx, sy);
              else ctx.lineTo(sx, sy);
            }}
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
          }}
        }}
      }}

      // 4. Draw Main Hybrid Buildings
      const showConfirmed = document.getElementById('chk-hybrid-confirmed').checked;
      const showLidar = document.getElementById('chk-lidar-direct').checked;

      for (let bldg of DATA.main_buildings) {{
        const isConfirmed = (bldg.validare === "CONFIRMAT_HIBRID");
        if (isConfirmed && !showConfirmed) continue;
        if (!isConfirmed && !showLidar) continue;

        if (isConfirmed) {{
          ctx.fillStyle = 'rgba(239, 68, 68, 0.55)';
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
          ctx.lineWidth = 1.5;
        }} else {{
          ctx.fillStyle = 'rgba(249, 115, 22, 0.5)';
          ctx.strokeStyle = 'rgba(234, 88, 12, 0.9)';
          ctx.lineWidth = 1.2;
        }}

        for (let poly of bldg.coords) {{
          ctx.beginPath();
          for (let i = 0; i < poly.length; i++) {{
            const [sx, sy] = toScreen(poly[i][0], poly[i][1]);
            if (i === 0) ctx.moveTo(sx, sy);
            else ctx.lineTo(sx, sy);
          }}
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
        }}
      }}

      // 5. Draw Utility Poles & Towers
      if (document.getElementById('chk-poles').checked) {{
        ctx.fillStyle = '#22d3ee';
        ctx.strokeStyle = '#0891b2';
        ctx.lineWidth = 1.5;
        const poleSize = Math.max(4, 5 * zoom * 0.3);
        for (let p of DATA.poles) {{
          const [sx, sy] = toScreen(p.x, p.y);
          ctx.save();
          ctx.translate(sx, sy);
          ctx.rotate(Math.PI / 4);
          ctx.fillRect(-poleSize/2, -poleSize/2, poleSize, poleSize);
          ctx.strokeRect(-poleSize/2, -poleSize/2, poleSize, poleSize);
          ctx.restore();
        }}
      }}
    }}

    // Mouse Interaction: Pan & Zoom
    let isDragging = false;
    let startX, startY;

    canvas.addEventListener('mousedown', (e) => {{
      isDragging = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
    }});

    window.addEventListener('mouseup', () => isDragging = false);

    canvas.addEventListener('mousemove', (e) => {{
      if (isDragging) {{
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        render();
      }}
    }});

    canvas.addEventListener('wheel', (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      panX = mouseX - (mouseX - panX) * zoomFactor;
      panY = mouseY - (mouseY - panY) * zoomFactor;
      zoom *= zoomFactor;
      render();
    }});

    // Button controls
    document.getElementById('btn-zoom-in').addEventListener('click', () => {{
      zoom *= 1.25;
      panX = width / 2 - (width / 2 - panX) * 1.25;
      panY = height / 2 - (height / 2 - panY) * 1.25;
      render();
    }});

    document.getElementById('btn-zoom-out').addEventListener('click', () => {{
      zoom /= 1.25;
      panX = width / 2 - (width / 2 - panX) / 1.25;
      panY = height / 2 - (height / 2 - panY) / 1.25;
      render();
    }});

    document.getElementById('btn-reset').addEventListener('click', resetView);

    // Layer checkboxes
    ['chk-hybrid-confirmed', 'chk-lidar-direct', 'chk-anexe', 'chk-trees', 'chk-poles'].forEach(id => {{
      document.getElementById(id).addEventListener('change', render);
    }});

    // Click on object to inspect
    canvas.addEventListener('click', (e) => {{
      const [gx, gy] = toGeo(e.clientX, e.clientY);
      const infoCard = document.getElementById('info-card');
      const infoTitle = document.getElementById('info-title');
      const infoBody = document.getElementById('info-body');

      let found = null;
      for (let bldg of DATA.main_buildings) {{
        for (let poly of bldg.coords) {{
          if (pointInPolygon([gx, gy], poly)) {{
            found = bldg;
            break;
          }}
        }}
        if (found) break;
      }}

      if (found) {{
        infoCard.classList.remove('hidden');
        const isConf = (found.validare === "CONFIRMAT_HIBRID");
        infoTitle.innerHTML = `Clădire C${{found.id}} <span class="text-xs px-2 py-0.5 rounded ${{isConf ? 'bg-red-500/30 text-red-300' : 'bg-orange-500/30 text-orange-300'}}">${{found.validare}}</span>`;
        infoBody.innerHTML = `
          <div><b>Suprafață Cadastrală:</b> ${{found.area_m2}} m²</div>
          <div><b>Înălțime Medie nDSM:</b> ${{found.inaltime_med_m}} m</div>
          <div><b>Înălțime Maximă Coamă:</b> ${{found.inaltime_max_m}} m</div>
          <div><b>Scor Confidență SAM 2:</b> ${{found.sam2_score.toFixed(3)}}</div>
          <div><b>Noduri CAD (Regularizare 90°):</b> ${{found.vertices}} noduri</div>
        `;
      }} else {{
        infoCard.classList.add('hidden');
      }}
    }});

    document.getElementById('btn-close-info').addEventListener('click', () => {{
      document.getElementById('info-card').classList.add('hidden');
    }});

    function pointInPolygon(pt, vs) {{
      const x = pt[0], y = pt[1];
      let inside = false;
      for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {{
        const xi = vs[i][0], yi = vs[i][1];
        const xj = vs[j][0], yj = vs[j][1];
        const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
      }}
      return inside;
    }}

    // Initial setup
    resize();
    resetView();
  </script>
</body>
</html>
"""

# Write to both standalone and inline artifacts
standalone_path = os.path.abspath(r"C:\Users\lefpa\.gemini\antigravity\brain\932496f8-cca4-49e2-99ec-b8b4c90db783\qgis_map_viewer.html")
inline_path = os.path.abspath(r"C:\Users\lefpa\.gemini\antigravity\brain\932496f8-cca4-49e2-99ec-b8b4c90db783\qgis_map_inline.html")

with open(standalone_path, "w", encoding="utf-8") as f:
    f.write(html_content)

with open(inline_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"[OK] Vizualizator actualizat cu succes in:\n  - {standalone_path}\n  - {inline_path}")
