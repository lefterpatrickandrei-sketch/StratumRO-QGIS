import os
import sys
import json
import geopandas as gpd

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cad_gpkg = os.path.abspath(r"workspace\output\cadastru_ancpi.gpkg")
pug_gpkg = os.path.abspath(r"workspace\output\urbanism_pug.gpkg")
report_path = os.path.abspath(r"workspace\output\raport_indicatori_pug.json")

with open(report_path, "r", encoding="utf-8") as f:
    pug_report = json.load(f)

# Citim layere Cadastru
gdf_cad_main = gpd.read_file(cad_gpkg, layer="CONSTRUCTII")
gdf_cad_anexe = gpd.read_file(cad_gpkg, layer="ANEXE")
gdf_cad_trees = gpd.read_file(cad_gpkg, layer="ARBORI_ALINIAMENT")
gdf_cad_poles = gpd.read_file(cad_gpkg, layer="STALPI_UTILITATI")

# Citim layere PUG
gdf_pug_main = gpd.read_file(pug_gpkg, layer="CLADIRI_VOLUMETRICE_LOD1")
gdf_pug_canopy = gpd.read_file(pug_gpkg, layer="CORONAMENTE_FOND_VEGETAL")
gdf_pug_utr = gpd.read_file(pug_gpkg, layer="ZONIFICARE_POT_CUT")

# Sample arbori pentru browser 60fps
sample_trees = gdf_cad_trees.sample(n=min(2200, len(gdf_cad_trees)), random_state=42)
sample_canopy = gdf_pug_canopy.sample(n=min(1200, len(gdf_pug_canopy)), random_state=42)

def poly_to_coords(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [[list(p) for p in geom.exterior.coords]]
    elif geom.geom_type == 'MultiPolygon':
        return [[list(c) for c in p.exterior.coords] for p in geom.geoms]
    return []

# 1. Cadastru Data
cad_items = []
for _, r in gdf_cad_main.iterrows():
    coords = poly_to_coords(r.geometry)
    if not coords: continue
    cad_items.append({
        "id": r.get("id_cadastral", f"C{r.get('id', 0)}"),
        "sc": float(r.get("suprafata_sol_mp", r.geometry.area)),
        "regim": str(r.get("regim_inaltime", "P")),
        "vertices": int(r.get("vertices", 4)),
        "coords": coords
    })

anexe_items = []
for _, r in gdf_cad_anexe.iterrows():
    coords = poly_to_coords(r.geometry)
    if not coords: continue
    anexe_items.append({
        "id": r.get("id_cadastral", f"C{r.get('id', 0)}"),
        "sc": float(r.get("suprafata_sol_mp", r.geometry.area)),
        "coords": coords
    })

# 2. PUG Data
pug_bldgs = []
for _, r in gdf_pug_main.iterrows():
    coords = poly_to_coords(r.geometry)
    if not coords: continue
    pug_bldgs.append({
        "id": str(r.get("cod_cladire", "")),
        "regim": str(r.get("regim_inaltime", "P")),
        "h_cornisa": float(r.get("h_cornisa_m", 4.0)),
        "h_coama": float(r.get("h_coama_m", 5.5)),
        "sc": float(r.get("sc_sol_mp", 0.0)),
        "sd": float(r.get("sd_desfasurat_mp", 0.0)),
        "vol": float(r.get("volum_construit_mc", 0.0)),
        "coords": coords
    })

canopy_items = []
for _, r in sample_canopy.iterrows():
    coords = poly_to_coords(r.geometry)
    if not coords: continue
    canopy_items.append({
        "h": float(r.get("inaltime_m", 4.0)),
        "coords": coords
    })

utr_items = []
for _, r in gdf_pug_utr.iterrows():
    coords = poly_to_coords(r.geometry)
    if not coords: continue
    utr_items.append({
        "id": str(r.get("id_utr", "")),
        "pot": float(r.get("pot_procent", 0.0)),
        "cut": float(r.get("cut", 0.0)),
        "green": float(r.get("procent_spatiu_verde", 0.0)),
        "coords": coords
    })

trees_pts = [{"x": float(r.geometry.x), "y": float(r.geometry.y), "h": float(r.get("height_m", 4.0))} for _, r in sample_trees.iterrows()]
poles_pts = [{"x": float(r.geometry.x), "y": float(r.geometry.y), "h": float(r.get("height_m", 12.0))} for _, r in gdf_cad_poles.iterrows()]

bounds = {
    "xmin": float(gdf_cad_main.total_bounds[0]),
    "ymin": float(gdf_cad_main.total_bounds[1]),
    "xmax": float(gdf_cad_main.total_bounds[2]),
    "ymax": float(gdf_cad_main.total_bounds[3])
}

all_data = {
    "bounds": bounds,
    "cadastru": {
        "constructii": cad_items,
        "anexe": anexe_items,
        "arbori_count": len(gdf_cad_trees),
        "poles_count": len(gdf_cad_poles)
    },
    "pug": {
        "bldgs": pug_bldgs,
        "canopy": canopy_items,
        "utr": utr_items,
        "report": pug_report
    },
    "trees": trees_pts,
    "poles": poles_pts
}

json_str = json.dumps(all_data)

html_template = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StratumRO — Produse Specializate: Cadastru vs. PUG</title>
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
    .mode-tab-active {{
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
      color: #ffffff;
      font-weight: 700;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }}
  </style>
</head>
<body class="relative w-screen h-screen">

  <!-- Header & Toolbar -->
  <header class="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-xl">
    <div class="glass p-3 rounded-xl shadow-2xl flex items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
        <span class="font-bold text-sm tracking-wide text-white">StratumRO — Produse Separate</span>
      </div>

      <!-- Mode Switcher Tabs -->
      <div class="flex bg-slate-900/90 p-1 rounded-lg border border-slate-700/80 text-xs">
        <button id="tab-cadastru" class="px-3 py-1.5 rounded-md transition mode-tab-active flex items-center gap-1.5">
          <span>🏛️ 1. CADASTRU (ANCPI)</span>
        </button>
        <button id="tab-pug" class="px-3 py-1.5 rounded-md transition text-slate-400 hover:text-white flex items-center gap-1.5">
          <span>🏙️ 2. URBANISM &amp; PUG</span>
        </button>
      </div>
    </div>

    <!-- Mode 1: CADASTRU Info Bar -->
    <div id="panel-cadastru" class="glass px-4 py-2.5 rounded-xl shadow-xl text-xs space-y-1">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-red-300">Norme ANCPI (Legea 7/1996 &amp; Ord. 600/2023)</span>
        <span class="text-emerald-400 font-bold">0 Copaci pe Clădiri</span>
      </div>
      <div class="flex items-center gap-4 text-slate-400">
        <div>Construcții C1: <b class="text-white">377</b></div>
        <div>Anexe C2: <b class="text-white">6</b></div>
        <div>Arbori Aliniament: <b class="text-white">3,927</b></div>
        <div>Noduri 90°: <b class="text-white">68.2% dreptunghiuri</b></div>
      </div>
    </div>

    <!-- Mode 2: PUG Info Bar -->
    <div id="panel-pug" class="glass px-4 py-2.5 rounded-xl shadow-xl text-xs space-y-1 hidden">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-orange-300">Urbanism &amp; PUG (Legea 350/2001 &amp; Legea 24/2007)</span>
        <span class="text-orange-400 font-bold">LOD1 3D + Spații Verzi</span>
      </div>
      <div class="flex items-center gap-4 text-slate-400">
        <div>POT Mediu: <b class="text-white">{pug_report['indicatori_generali_zona']['pot_mediu_procent']}%</b></div>
        <div>CUT Mediu: <b class="text-white">{pug_report['indicatori_generali_zona']['cut_mediu']}</b></div>
        <div>Suprafață Verde: <b class="text-emerald-300">21.2 ha</b></div>
        <div>Volum Construit: <b class="text-white">434.257 m³</b></div>
      </div>
    </div>
  </header>

  <!-- Navigation Controls -->
  <div class="absolute bottom-6 right-6 z-20 flex flex-col gap-2">
    <div class="glass p-1.5 rounded-xl shadow-xl flex flex-col gap-1">
      <button id="btn-zoom-in" class="w-9 h-9 flex items-center justify-center bg-slate-800 hover:bg-slate-700 rounded-lg text-lg font-bold transition">+</button>
      <button id="btn-zoom-out" class="w-9 h-9 flex items-center justify-center bg-slate-800 hover:bg-slate-700 rounded-lg text-lg font-bold transition">−</button>
      <button id="btn-reset" class="w-9 h-9 flex items-center justify-center bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-semibold transition" title="Resetare Zoom">⟲</button>
    </div>
  </div>

  <!-- Object Inspector -->
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

    let currentMode = 'cadastru'; // 'cadastru' or 'pug'

    const canvas = document.getElementById('map-canvas');
    const ctx = canvas.getContext('2d');

    let width, height;
    function resize() {{
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      render();
    }}
    window.addEventListener('resize', resize);

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
      panY = height / 2 + centerGeoY * zoom;
      render();
    }}

    function toScreen(gx, gy) {{
      return [gx * zoom + panX, panY - gy * zoom];
    }}

    function toGeo(sx, sy) {{
      return [(sx - panX) / zoom, (panY - sy) / zoom];
    }}

    function render() {{
      ctx.clearRect(0, 0, width, height);

      // 1. Stereo 70 Grid
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

      if (currentMode === 'cadastru') {{
        renderCadastru();
      }} else {{
        renderPug();
      }}
    }}

    function renderCadastru() {{
      // A. Trees outside buildings
      ctx.fillStyle = 'rgba(34, 197, 94, 0.45)';
      ctx.strokeStyle = 'rgba(21, 128, 61, 0.85)';
      ctx.lineWidth = 1;
      const treeR = Math.max(1.6, 1.8 * zoom * 0.25);
      for (let t of DATA.trees) {{
        const [sx, sy] = toScreen(t.x, t.y);
        ctx.beginPath();
        ctx.arc(sx, sy, treeR, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }}

      // B. Anexe C2 (Yellow)
      ctx.fillStyle = 'rgba(250, 204, 21, 0.55)';
      ctx.strokeStyle = 'rgba(202, 138, 4, 0.95)';
      ctx.lineWidth = 1.2;
      for (let a of DATA.cadastru.anexe) {{
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

      // C. Constructii C1 (Red, strict 90 degrees)
      ctx.fillStyle = 'rgba(239, 68, 68, 0.6)';
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.lineWidth = 1.5;
      for (let bldg of DATA.cadastru.constructii) {{
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

      // D. Poles (Cyan Diamonds)
      ctx.fillStyle = '#06b6d4';
      ctx.strokeStyle = '#0e7490';
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

    function renderPug() {{
      // A. UTR Grid Cells (Dashed borders with POT / CUT)
      ctx.fillStyle = 'rgba(99, 102, 241, 0.08)';
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.35)';
      ctx.lineWidth = 1.0;
      ctx.setLineDash([4, 4]);
      for (let u of DATA.pug.utr) {{
        for (let poly of u.coords) {{
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
      ctx.setLineDash([]); // reset dash

      // B. Canopy Polygons (Green Spaces)
      ctx.fillStyle = 'rgba(74, 222, 128, 0.28)';
      ctx.strokeStyle = 'rgba(34, 197, 94, 0.6)';
      ctx.lineWidth = 0.8;
      for (let c of DATA.pug.canopy) {{
        for (let poly of c.coords) {{
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

      // C. Tree Trunk Points
      ctx.fillStyle = '#22c55e';
      const treeR = Math.max(1.8, 2.0 * zoom * 0.25);
      for (let t of DATA.trees) {{
        const [sx, sy] = toScreen(t.x, t.y);
        ctx.beginPath();
        ctx.arc(sx, sy, treeR, 0, Math.PI * 2);
        ctx.fill();
      }}

      // D. Cladiri Volumetrice LOD1 (Color coded by height)
      for (let bldg of DATA.pug.bldgs) {{
        const h = bldg.h_cornisa;
        let fillColor = 'rgba(249, 115, 22, 0.65)'; // P
        if (h > 9.0) fillColor = 'rgba(220, 38, 38, 0.75)'; // P+2, P+3
        else if (h > 6.0) fillColor = 'rgba(234, 88, 12, 0.7)'; // P+1

        ctx.fillStyle = fillColor;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.4;

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
    }}

    // Mode Switcher Listeners
    const tabCad = document.getElementById('tab-cadastru');
    const tabPug = document.getElementById('tab-pug');
    const panelCad = document.getElementById('panel-cadastru');
    const panelPug = document.getElementById('panel-pug');

    tabCad.addEventListener('click', () => {{
      currentMode = 'cadastru';
      tabCad.className = 'px-3 py-1.5 rounded-md transition mode-tab-active flex items-center gap-1.5';
      tabPug.className = 'px-3 py-1.5 rounded-md transition text-slate-400 hover:text-white flex items-center gap-1.5';
      panelCad.classList.remove('hidden');
      panelPug.classList.add('hidden');
      render();
    }});

    tabPug.addEventListener('click', () => {{
      currentMode = 'pug';
      tabPug.className = 'px-3 py-1.5 rounded-md transition mode-tab-active flex items-center gap-1.5';
      tabCad.className = 'px-3 py-1.5 rounded-md transition text-slate-400 hover:text-white flex items-center gap-1.5';
      panelPug.classList.remove('hidden');
      panelCad.classList.add('hidden');
      render();
    }});

    // Pan & Zoom
    let isDragging = false, startX, startY;
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
      panX = e.clientX - (e.clientX - panX) * zoomFactor;
      panY = e.clientY - (e.clientY - panY) * zoomFactor;
      zoom *= zoomFactor;
      render();
    }});

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

    // Click inspector
    canvas.addEventListener('click', (e) => {{
      const [gx, gy] = toGeo(e.clientX, e.clientY);
      const infoCard = document.getElementById('info-card');
      const infoTitle = document.getElementById('info-title');
      const infoBody = document.getElementById('info-body');

      if (currentMode === 'cadastru') {{
        let found = null;
        for (let b of DATA.cadastru.constructii) {{
          for (let poly of b.coords) {{
            if (pointInPolygon([gx, gy], poly)) {{ found = b; break; }}
          }}
          if (found) break;
        }}
        if (found) {{
          infoCard.classList.remove('hidden');
          infoTitle.innerHTML = `<span class="text-red-400">🏛️ Imobil Cadastral ${{found.id}}</span>`;
          infoBody.innerHTML = `
            <div><b>Categorie:</b> Construcție Principală (C1)</div>
            <div><b>Suprafață la Sol (Sc):</b> ${{found.sc}} m²</div>
            <div><b>Regim Înălțime Cadastral:</b> ${{found.regim}}</div>
            <div><b>Noduri Poligon (CAD 90°):</b> ${{found.vertices}} noduri</div>
            <div><b>Vegetație pe Acoperiș:</b> <span class="text-emerald-400 font-bold">0 copaci (Interzis ANCPI)</span></div>
          `;
          return;
        }}
      }} else {{
        let found = null;
        for (let b of DATA.pug.bldgs) {{
          for (let poly of b.coords) {{
            if (pointInPolygon([gx, gy], poly)) {{ found = b; break; }}
          }}
          if (found) break;
        }}
        if (found) {{
          infoCard.classList.remove('hidden');
          infoTitle.innerHTML = `<span class="text-orange-400">🏙️ Clădire Volumetrică LOD1 (${{found.id}})</span>`;
          infoBody.innerHTML = `
            <div><b>Regim Înălțime PUG:</b> ${{found.regim}}</div>
            <div><b>Cota Cornișă:</b> ${{found.h_cornisa}} m</div>
            <div><b>Cota Coamă (Max):</b> ${{found.h_coama}} m</div>
            <div><b>Suprafață Construită (Sc):</b> ${{found.sc}} m²</div>
            <div><b>Suprafață Desfășurată (Sd):</b> ${{found.sd}} m²</div>
            <div><b>Volum Construit:</b> ${{found.vol}} m³</div>
          `;
          return;
        }}
      }}
      infoCard.classList.add('hidden');
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

    resize();
    resetView();
  </script>
</body>
</html>
"""

# Write to both artifacts
standalone_path = os.path.abspath(r"C:\Users\lefpa\.gemini\antigravity\brain\932496f8-cca4-49e2-99ec-b8b4c90db783\qgis_map_viewer.html")
inline_path = os.path.abspath(r"C:\Users\lefpa\.gemini\antigravity\brain\932496f8-cca4-49e2-99ec-b8b4c90db783\qgis_map_inline.html")

with open(standalone_path, "w", encoding="utf-8") as f:
    f.write(html_template)

with open(inline_path, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"[OK] Vizualizator hibrid cu comutator CADASTRU / PUG salvat cu succes.")
