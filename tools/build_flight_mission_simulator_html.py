# -*- coding: utf-8 -*-
"""
Build Interactive Drone Flight Mission & Strip Player HTML
==========================================================
Generates a world-class, cyber-geomatics flight mission simulator and strip player
with live telemetry HUD, 2D flight canvas animation, real-time aerial frame display,
boustrophedon trajectory, and 60/40 photogrammetric overlap inspection.
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "workspace" / "reviews" / "drone_flight_strips" / "flight_mission_manifest.json"
OUT_HTML = ROOT / "workspace" / "reviews" / "drone_flight_strips" / "flight_mission_simulator.html"
OUT_INDEX = ROOT / "workspace" / "reviews" / "drone_flight_strips" / "index.html"
OUT_SIM_ROOT = ROOT / "workspace" / "reviews" / "simulare_drona_60_40.html"

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
stations = manifest["stations"]
specs = manifest["flight_specs"]
bounds = manifest["aoi_bounds"]

# Load simplified building centroids for rendering on map
GPKG_PATH = ROOT / "workspace" / "option_b_validation_20261019" / "b_proposals_cleaned.gpkg"
import geopandas as gpd
gdf_b = gpd.read_file(GPKG_PATH, layer="B_ROOF_PROPOSALS")
bldgs_simple = []
for idx, row in gdf_b.iterrows():
    c = row.geometry.centroid
    bldgs_simple.append({
        "id": row["candidate_id"],
        "x": round(c.x, 1),
        "y": round(c.y, 1),
        "area": round(float(row.get("area_m2", row.geometry.area)), 1)
    })

print(f"[*] Compilare Simulator Zbor Dronă: {len(stations)} stații, {len(bldgs_simple)} clădiri...")

html_content = f"""<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>StratumRO — Simulator Misiune Zbor Fotogrammetric Dronă (11 Benzi, 60/40 Overlap)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #06090e;
            --bg-surface: #0c111d;
            --bg-card: #131a29;
            --border-dim: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(56, 189, 248, 0.35);
            --cyan: #00f0ff;
            --emerald: #10b981;
            --amber: #f59e0b;
            --rose: #f43f5e;
            --purple: #a855f7;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --text-muted: #64748b;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }}

        body {{
            background: var(--bg-base);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }}

        /* Header Mission HUD */
        header {{
            background: rgba(12, 17, 29, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-glow);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            position: sticky;
            top: 0;
            z-index: 50;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .brand-icon {{
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--cyan), #3b82f6);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            box-shadow: 0 0 12px rgba(0, 240, 255, 0.4);
        }}

        .brand-text h1 {{
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            background: linear-gradient(90deg, #fff, var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .brand-text p {{
            font-size: 0.7rem;
            color: var(--text-sub);
            font-family: 'JetBrains Mono', monospace;
        }}

        .hud-ribbon {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }}

        .hud-badge {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-dim);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .hud-badge b {{
            color: var(--cyan);
        }}

        .hud-badge.emerald b {{
            color: var(--emerald);
        }}

        .hud-badge.amber b {{
            color: var(--amber);
        }}

        /* Main Cockpit Layout */
        .cockpit-grid {{
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 14px;
            padding: 14px;
            flex: 1;
            max-width: 1720px;
            margin: 0 auto;
            width: 100%;
        }}

        @media (max-width: 1024px) {{
            .cockpit-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        /* Left Canvas Map Box */
        .map-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-dim);
            border-radius: 14px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            position: relative;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text-sub);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .canvas-wrap {{
            position: relative;
            flex: 1;
            min-height: 440px;
            background: #03060a;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        canvas#flightCanvas {{
            display: block;
            width: 100%;
            height: 100%;
            cursor: crosshair;
        }}

        /* Map Legend Overlay */
        .map-legend {{
            position: absolute;
            bottom: 12px;
            left: 12px;
            background: rgba(6, 9, 14, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-dim);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.65rem;
            color: var(--text-sub);
            display: flex;
            flex-direction: column;
            gap: 4px;
            pointer-events: none;
        }}

        .legend-row {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }}

        /* Right Camera Feed Box */
        .camera-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-dim);
            border-radius: 14px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}

        .viewport-container {{
            position: relative;
            flex: 1;
            min-height: 380px;
            background: #000;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.08);
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .ortho-frame-img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: opacity 0.15s ease-in-out;
        }}

        /* Tactical HUD Overlay on Camera */
        .gimbal-hud {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 14px;
        }}

        .hud-corner-tl {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: #00f0ff;
            text-shadow: 0 0 4px rgba(0,0,0,0.9);
        }}

        .hud-crosshair {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 80px;
            height: 80px;
            pointer-events: none;
        }}

        .hud-crosshair::before, .hud-crosshair::after {{
            content: "";
            position: absolute;
            background: rgba(0, 240, 255, 0.45);
        }}

        .hud-crosshair::before {{
            top: 50%; left: 0; right: 0; height: 1px;
        }}

        .hud-crosshair::after {{
            left: 50%; top: 0; bottom: 0; width: 1px;
        }}

        .hud-center-box {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 32px;
            height: 32px;
            border: 1px dashed rgba(0, 240, 255, 0.6);
            border-radius: 4px;
        }}

        .hud-bottom-bar {{
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(6px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 6px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            color: #e2e8f0;
        }}

        /* Buildings list under camera */
        .in-view-box {{
            margin-top: 10px;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border-dim);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 0.75rem;
        }}

        .bldg-pill {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid rgba(56, 189, 248, 0.4);
            color: var(--cyan);
            padding: 2px 8px;
            border-radius: 4px;
            margin: 2px 4px 2px 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            text-decoration: none;
        }}

        .bldg-pill:hover {{
            background: rgba(56, 189, 248, 0.35);
        }}

        /* Bottom Control Deck */
        .control-deck {{
            background: var(--bg-surface);
            border-top: 1px solid var(--border-dim);
            padding: 14px 20px;
            position: sticky;
            bottom: 0;
            z-index: 50;
        }}

        .timeline-bar {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 12px;
        }}

        .scrubber-slider {{
            flex: 1;
            height: 8px;
            -webkit-appearance: none;
            background: #1e293b;
            border-radius: 4px;
            outline: none;
            cursor: pointer;
        }}

        .scrubber-slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: var(--cyan);
            box-shadow: 0 0 10px var(--cyan);
            cursor: pointer;
        }}

        .controls-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .btn-group {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}

        .ctrl-btn {{
            background: var(--bg-card);
            border: 1px solid var(--border-dim);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .ctrl-btn:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--border-glow);
        }}

        .ctrl-btn.active {{
            background: rgba(0, 240, 255, 0.18);
            border-color: var(--cyan);
            color: var(--cyan);
        }}

        .ctrl-btn-primary {{
            background: var(--cyan);
            color: #000;
            font-weight: 700;
            border: none;
            box-shadow: 0 0 14px rgba(0, 240, 255, 0.35);
        }}

        .ctrl-btn-primary:hover {{
            background: #38bdf8;
            color: #000;
        }}

        /* Strip Jump Pills */
        .strip-pills-row {{
            display: flex;
            gap: 6px;
            overflow-x: auto;
            padding-bottom: 4px;
            margin-top: 10px;
        }}

        .strip-pill {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-dim);
            color: var(--text-sub);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s;
        }}

        .strip-pill:hover {{
            color: var(--text-main);
            border-color: var(--border-glow);
        }}

        .strip-pill.active {{
            background: rgba(56, 189, 248, 0.18);
            border-color: var(--cyan);
            color: var(--cyan);
            font-weight: 700;
        }}

        .nav-links {{
            display: flex;
            justify-content: center;
            gap: 14px;
            padding: 10px;
            font-size: 0.75rem;
            background: #04070c;
            border-top: 1px solid var(--border-dim);
        }}

        .nav-link {{
            color: var(--cyan);
            text-decoration: none;
            font-weight: 600;
        }}

        .nav-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <!-- Top Mission Telemetry Bar -->
    <header>
        <div class="brand">
            <div class="brand-icon">🚁</div>
            <div class="brand-text">
                <h1>StratumRO — Simulator Misiune Zbor Fotogrammetric</h1>
                <p>Acoperire 60% Longitudinal / 40% Transversal • Stereo 70 (EPSG:3844)</p>
            </div>
        </div>

        <div class="hud-ribbon">
            <div class="hud-badge emerald">
                <span>STARE ZBOR:</span>
                <b id="hudStatus">STANDBY</b>
            </div>
            <div class="hud-badge">
                <span>CADRU:</span>
                <b id="hudFrameId">STRIP_01_FRAME_01</b>
            </div>
            <div class="hud-badge amber">
                <span>BANDA:</span>
                <b id="hudStrip">01 / 11</b>
            </div>
            <div class="hud-badge">
                <span>COORDONATE S70:</span>
                <b id="hudCoords">390530.0 E, 585886.0 N</b>
            </div>
            <div class="hud-badge">
                <span>CAP COMPAS:</span>
                <b id="hudHeading">180° (SUD)</b>
            </div>
            <div class="hud-badge">
                <span>ALTITUDINE:</span>
                <b>120.0 m AGL</b>
            </div>
        </div>
    </header>

    <!-- Cockpit View -->
    <div class="cockpit-grid">
        <!-- Left: 2D Flight Canvas Map -->
        <div class="map-card">
            <div class="card-header">
                <span>🗺️ Traseu Zbor Boustrophedon (1.05 km x 1.05 km)</span>
                <div style="display:flex; gap:8px;">
                    <button class="ctrl-btn" style="padding:3px 8px; font-size:0.7rem;" id="btnToggleFootprints">Amprente Cadre</button>
                    <button class="ctrl-btn" style="padding:3px 8px; font-size:0.7rem;" id="btnToggleBldgs">Clădiri 1CC</button>
                </div>
            </div>

            <div class="canvas-wrap">
                <canvas id="flightCanvas"></canvas>
                <div class="map-legend">
                    <div class="legend-row"><span class="legend-dot" style="background:#00f0ff;"></span> Linie Zbor Curentă</div>
                    <div class="legend-row"><span class="legend-dot" style="background:rgba(56,189,248,0.25);"></span> Amprentă Foto 180x120m</div>
                    <div class="legend-row"><span class="legend-dot" style="background:#10b981;"></span> Clădiri Detectate</div>
                    <div class="legend-row"><span class="legend-dot" style="background:#f59e0b;"></span> Punct Declansare Curent</div>
                </div>
            </div>
        </div>

        <!-- Right: Live Aerial Camera Viewport -->
        <div class="camera-card">
            <div class="card-header">
                <span>📸 Vizualizare Cameră Gimbal (Cadru Ortofoto Real 15 cm)</span>
                <span id="cardFrameIndex" style="font-family:'JetBrains Mono'; color:var(--cyan);">001 / {len(stations)}</span>
            </div>

            <div class="viewport-container" id="cameraViewport">
                <img id="orthoFrameImg" class="ortho-frame-img" src="{stations[0]['image']}" alt="Cadru Zbor Dronă">
                
                <!-- HUD Overlays -->
                <div class="gimbal-hud">
                    <div class="hud-corner-tl">
                        <div>FOV: 74°x53° | FOCAL: 35mm</div>
                        <div>EXPOSURE: 1/1600s f/4.0 ISO 100</div>
                        <div>GSD LA SOL: 1.5 cm/px</div>
                    </div>

                    <div class="hud-crosshair">
                        <div class="hud-center-box"></div>
                    </div>

                    <div class="hud-bottom-bar">
                        <span id="hudCameraId">{stations[0]['id']}</span>
                        <span id="hudCameraCoords">N: {stations[0]['y']} | E: {stations[0]['x']}</span>
                        <span id="hudCameraAlt">120m AGL</span>
                    </div>
                </div>
            </div>

            <!-- In-View Cadastral Buildings -->
            <div class="in-view-box">
                <div style="font-size:0.7rem; color:var(--text-sub); margin-bottom:4px; display:flex; justify-content:space-between;">
                    <span>🏢 Clădiri Cadastrale în Cadrul Curent: <b style="color:var(--emerald);" id="inViewCount">{stations[0]['bldg_count']}</b></span>
                    <span>Retragere streașină: 0.40m</span>
                </div>
                <div id="inViewPills">
                    <!-- Populated by JS -->
                </div>
            </div>
        </div>
    </div>

    <!-- Bottom Control Deck -->
    <div class="control-deck">
        <div class="timeline-bar">
            <span style="font-family:'JetBrains Mono'; font-size:0.75rem; color:var(--text-muted);" id="timelineCurrent">001</span>
            <input type="range" class="scrubber-slider" id="flightScrubber" min="0" max="{len(stations)-1}" value="0">
            <span style="font-family:'JetBrains Mono'; font-size:0.75rem; color:var(--text-muted);">{len(stations):03d}</span>
        </div>

        <div class="controls-row">
            <div class="btn-group">
                <button class="ctrl-btn ctrl-btn-primary" id="btnPlayPause">▶️ Zbor Automat</button>
                <button class="ctrl-btn" id="btnPrevFrame">⏮️ Înapoi</button>
                <button class="ctrl-btn" id="btnNextFrame">⏭️ Înainte</button>
                <button class="ctrl-btn" id="btnResetFlight">↺ Reset AOI</button>
            </div>

            <div class="btn-group">
                <span style="font-size:0.75rem; color:var(--text-muted);">Viteză Zbor:</span>
                <button class="ctrl-btn active" data-speed="1">1x</button>
                <button class="ctrl-btn" data-speed="2">2x</button>
                <button class="ctrl-btn" data-speed="5">5x</button>
                <button class="ctrl-btn" data-speed="10">10x</button>
            </div>
        </div>

        <!-- 11 Strips Jump Bar -->
        <div class="strip-pills-row" id="stripPillsRow">
            <!-- Populated by JS for all 11 strips -->
        </div>
    </div>

    <div class="nav-links">
        <a href="../catalog_cladiri_ortofoto.html" class="nav-link">📂 Înapoi la Catalogul Clădiri Ortofoto</a>
        <a href="../simulare_drona_60_40.html" class="nav-link">✈️ Raport Stereorestituție 60/40</a>
        <a href="../scara_150_ultra_detaliu/index.html" class="nav-link">🔍 Galerie Ultra-Detaliu 1:150</a>
    </div>

    <!-- Flight Mission Data Injection -->
    <script>
        const STATIONS = {json.dumps(stations)};
        const BUILDINGS = {json.dumps(bldgs_simple)};
        const AOI_BOUNDS = {json.dumps(bounds)};
        const FRAME_W = {specs['frame_width_m']};
        const FRAME_H = {specs['frame_height_m']};
    </script>

    <script>
        let currentIndex = 0;
        let isPlaying = false;
        let playSpeed = 1;
        let playInterval = null;
        let showFootprints = true;
        let showBldgs = true;

        const canvas = document.getElementById("flightCanvas");
        const ctx = canvas.getContext("2d");

        const X_MIN = AOI_BOUNDS[0];
        const Y_MIN = AOI_BOUNDS[1];
        const X_MAX = AOI_BOUNDS[2];
        const Y_MAX = AOI_BOUNDS[3];

        function resizeCanvas() {{
            const wrap = canvas.parentElement;
            canvas.width = wrap.clientWidth;
            canvas.height = wrap.clientHeight;
            drawMap();
        }}
        window.addEventListener("resize", resizeCanvas);

        function mapX(x) {{
            const pad = 36;
            const w = canvas.width - pad * 2;
            return pad + ((x - X_MIN) / (X_MAX - X_MIN)) * w;
        }}

        function mapY(y) {{
            const pad = 36;
            const h = canvas.height - pad * 2;
            return pad + (1 - (y - Y_MIN) / (Y_MAX - Y_MIN)) * h;
        }}

        function initStripPills() {{
            const row = document.getElementById("stripPillsRow");
            const strips = [...new Set(STATIONS.map(s => s.strip))].sort((a,b)=>a-b);
            
            row.innerHTML = strips.map(s => {{
                const dir = (s % 2 !== 0) ? "N→S" : "S→N";
                return `<button class="strip-pill ${{s===1?'active':''}}" data-strip="${{s}}" onclick="jumpToStrip(${{s}})">Banda ${{s<10?'0'+s:s}} (${{dir}})</button>`;
            }}).join("");
        }}

        function jumpToStrip(stripNum) {{
            const firstStation = STATIONS.findIndex(s => s.strip === stripNum);
            if (firstStation !== -1) {{
                setStation(firstStation);
            }}
        }}

        function setStation(idx) {{
            if (idx < 0) idx = 0;
            if (idx >= STATIONS.length) idx = STATIONS.length - 1;
            currentIndex = idx;

            const st = STATIONS[currentIndex];

            // Update HUD
            document.getElementById("hudFrameId").innerText = st.id;
            document.getElementById("hudStrip").innerText = `${{st.strip < 10 ? '0' + st.strip : st.strip}} / 11`;
            document.getElementById("hudCoords").innerText = `${{st.x}} E, ${{st.y}} N`;
            document.getElementById("hudHeading").innerText = `${{st.heading}}° (${{st.heading === 180 ? 'SUD' : 'NORD'}})`;
            document.getElementById("cardFrameIndex").innerText = `${{String(currentIndex + 1).padStart(3, '0')}} / ${{STATIONS.length}}`;

            // Update Camera Image
            const imgEl = document.getElementById("orthoFrameImg");
            imgEl.src = st.image;
            document.getElementById("hudCameraId").innerText = st.id;
            document.getElementById("hudCameraCoords").innerText = `N: ${{st.y}} | E: ${{st.x}}`;

            // Update in-view buildings
            document.getElementById("inViewCount").innerText = st.bldg_count;
            const pillsDiv = document.getElementById("inViewPills");
            if (st.buildings && st.buildings.length > 0) {{
                pillsDiv.innerHTML = st.buildings.map(b => `<a href="../catalog_cladiri_ortofoto.html?search=${{b}}" target="_blank" class="bldg-pill">🔍 ${{b}}</a>`).join("");
            }} else {{
                pillsDiv.innerHTML = `<span style="color:var(--text-muted); font-size:0.7rem;">Zonă verde / drum fără clădiri înregistrate</span>`;
            }}

            // Update Scrubber
            document.getElementById("flightScrubber").value = currentIndex;
            document.getElementById("timelineCurrent").innerText = String(currentIndex + 1).padStart(3, '0');

            // Update Strip Pills Active
            document.querySelectorAll(".strip-pill").forEach(p => {{
                p.classList.toggle("active", parseInt(p.dataset.strip) === st.strip);
            }});

            drawMap();
        }}

        function drawMap() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 1. Grid
            ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
            ctx.lineWidth = 1;
            for (let i = 0; i <= 10; i++) {{
                const gx = mapX(X_MIN + i * ((X_MAX - X_MIN) / 10));
                ctx.beginPath();
                ctx.moveTo(gx, mapY(Y_MIN));
                ctx.lineTo(gx, mapY(Y_MAX));
                ctx.stroke();

                const gy = mapY(Y_MIN + i * ((Y_MAX - Y_MIN) / 10));
                ctx.beginPath();
                ctx.moveTo(mapX(X_MIN), gy);
                ctx.lineTo(mapX(X_MAX), gy);
                ctx.stroke();
            }}

            // 2. AOI Boundary
            ctx.strokeStyle = "rgba(56, 189, 248, 0.35)";
            ctx.lineWidth = 2;
            ctx.strokeRect(mapX(X_MIN), mapY(Y_MAX), mapX(X_MAX) - mapX(X_MIN), mapY(Y_MIN) - mapY(Y_MAX));

            // 3. Cadastral Buildings
            if (showBldgs) {{
                ctx.fillStyle = "rgba(16, 185, 129, 0.4)";
                BUILDINGS.forEach(b => {{
                    const px = mapX(b.x);
                    const py = mapY(b.y);
                    ctx.beginPath();
                    ctx.arc(px, py, 2.5, 0, Math.PI * 2);
                    ctx.fill();
                }});
            }}

            // 4. All 11 Flight Lines
            ctx.strokeStyle = "rgba(0, 240, 255, 0.3)";
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);

            // Group stations by strip
            const stripGroups = {{}};
            STATIONS.forEach(s => {{
                if (!stripGroups[s.strip]) stripGroups[s.strip] = [];
                stripGroups[s.strip].push(s);
            }});

            Object.values(stripGroups).forEach(group => {{
                ctx.beginPath();
                group.forEach((st, idx) => {{
                    const px = mapX(st.x);
                    const py = mapY(st.y);
                    if (idx === 0) ctx.moveTo(px, py);
                    else ctx.lineTo(px, py);
                }});
                ctx.stroke();
            }});
            ctx.setLineDash([]);

            // 5. Visited Exposure Footprints (60/40 Overlap heat)
            if (showFootprints) {{
                // Draw footprints for previous 5 stations
                const startTrail = Math.max(0, currentIndex - 4);
                for (let i = startTrail; i < currentIndex; i++) {{
                    const st = STATIONS[i];
                    const b = st.bounds;
                    const rx = mapX(b[0]);
                    const ry = mapY(b[3]);
                    const rw = mapX(b[2]) - rx;
                    const rh = mapY(b[1]) - ry;

                    ctx.fillStyle = "rgba(168, 85, 247, 0.08)";
                    ctx.fillRect(rx, ry, rw, rh);
                    ctx.strokeStyle = "rgba(168, 85, 247, 0.25)";
                    ctx.lineWidth = 1;
                    ctx.strokeRect(rx, ry, rw, rh);
                }}
            }}

            // 6. Current Station & Active Footprint
            const curSt = STATIONS[currentIndex];
            const cb = curSt.bounds;
            const crx = mapX(cb[0]);
            const cry = mapY(cb[3]);
            const crw = mapX(cb[2]) - crx;
            const crh = mapY(cb[1]) - cry;

            // Highlighted active footprint
            ctx.fillStyle = "rgba(0, 240, 255, 0.15)";
            ctx.fillRect(crx, cry, crw, crh);
            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 2;
            ctx.strokeRect(crx, cry, crw, crh);

            // 7. Animated Drone Icon
            const dx = mapX(curSt.x);
            const dy = mapY(curSt.y);

            // Pulsing circle
            ctx.beginPath();
            ctx.arc(dx, dy, 14, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(0, 240, 255, 0.2)";
            ctx.fill();

            // Drone Center Dot
            ctx.beginPath();
            ctx.arc(dx, dy, 5, 0, Math.PI * 2);
            ctx.fillStyle = "#fff";
            ctx.fill();

            // Heading Vector Arrow
            const headRad = (curSt.heading === 180) ? Math.PI / 2 : -Math.PI / 2;
            const arrLen = 22;
            const ax = dx + Math.cos(headRad) * arrLen;
            const ay = dy + Math.sin(headRad) * arrLen;

            ctx.strokeStyle = "#f59e0b";
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.moveTo(dx, dy);
            ctx.lineTo(ax, ay);
            ctx.stroke();
        }}

        // Click on map to jump to nearest station
        canvas.addEventListener("click", (e) => {{
            const rect = canvas.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;

            let bestDist = Infinity;
            let bestIdx = 0;

            STATIONS.forEach((st, idx) => {{
                const sx = mapX(st.x);
                const sy = mapY(st.y);
                const d = Math.hypot(clickX - sx, clickY - sy);
                if (d < bestDist) {{
                    bestDist = d;
                    bestIdx = idx;
                }}
            }});

            setStation(bestIdx);
        }});

        // Play / Pause Logic
        function togglePlay() {{
            isPlaying = !isPlaying;
            const btn = document.getElementById("btnPlayPause");
            const statusBadge = document.getElementById("hudStatus");

            if (isPlaying) {{
                btn.innerText = "⏸️ Pauză Zbor";
                btn.style.background = "var(--amber)";
                statusBadge.innerText = "MISIUNE ÎN CURS";
                statusBadge.parentElement.className = "hud-badge emerald";

                const intervalMs = Math.round(1000 / playSpeed);
                playInterval = setInterval(() => {{
                    if (currentIndex < STATIONS.length - 1) {{
                        setStation(currentIndex + 1);
                    }} else {{
                        togglePlay(); // Stop at end
                    }}
                }}, intervalMs);
            }} else {{
                btn.innerText = "▶️ Zbor Automat";
                btn.style.background = "var(--cyan)";
                statusBadge.innerText = "STANDBY";
                statusBadge.parentElement.className = "hud-badge";
                clearInterval(playInterval);
            }}
        }}

        // Setup Event Listeners
        document.getElementById("btnPlayPause").addEventListener("click", togglePlay);
        document.getElementById("btnNextFrame").addEventListener("click", () => setStation(currentIndex + 1));
        document.getElementById("btnPrevFrame").addEventListener("click", () => setStation(currentIndex - 1));
        document.getElementById("btnResetFlight").addEventListener("click", () => setStation(0));

        document.getElementById("flightScrubber").addEventListener("input", (e) => {{
            setStation(parseInt(e.target.value));
        }});

        // Speed Buttons
        document.querySelectorAll("[data-speed]").forEach(btn => {{
            btn.addEventListener("click", function() {{
                document.querySelectorAll("[data-speed]").forEach(b => b.classList.remove("active"));
                this.classList.add("active");
                playSpeed = parseInt(this.dataset.speed);
                if (isPlaying) {{
                    togglePlay();
                    togglePlay(); // Restart with new speed
                }}
            }});
        }});

        document.getElementById("btnToggleFootprints").addEventListener("click", function() {{
            showFootprints = !showFootprints;
            this.classList.toggle("active", showFootprints);
            drawMap();
        }});

        document.getElementById("btnToggleBldgs").addEventListener("click", function() {{
            showBldgs = !showBldgs;
            this.classList.toggle("active", showBldgs);
            drawMap();
        }});

        // Keyboard Shortcuts
        window.addEventListener("keydown", (e) => {{
            if (e.code === "Space") {{
                e.preventDefault();
                togglePlay();
            }} else if (e.code === "ArrowRight") {{
                setStation(currentIndex + 1);
            }} else if (e.code === "ArrowLeft") {{
                setStation(currentIndex - 1);
            }}
        }});

        // Init
        window.onload = () => {{
            resizeCanvas();
            initStripPills();
            setStation(0);
        }};
    </script>
</body>
</html>
"""

OUT_HTML.write_text(html_content, encoding="utf-8")
OUT_INDEX.write_text(html_content, encoding="utf-8") # Replace old 25-frame index with full 253-frame simulator
print(f"[SUCCESS] Simulatorul de zbor fotogrammetric a fost compilat cu succes la:")
print(f"  -> {OUT_HTML}")
print(f"  -> {OUT_INDEX}")
