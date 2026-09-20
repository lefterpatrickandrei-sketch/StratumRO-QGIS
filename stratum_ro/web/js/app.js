/**
 * StratumRO GeoAI Studio — Frontend Application Logic
 * Integrates Leaflet Web Map, Live QGIS Mirror, Workflow Runner,
 * Geodetic Telemetry, and Kilo Adversarial Reviewer.
 */

let map = null;
let candidatesLayer = null;
let groundTruthLayer = null;
let activeModeId = "assisted_cadastre";

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadHealthTelemetry();
  loadWorkflowModes();
  loadGeoJSONLayers();
  setupEventListeners();
});

// ---------------------------------------------------------------------------
// 1. Map Initialization (Cluj Benchmark Coordinates)
// ---------------------------------------------------------------------------
function initMap() {
  // Center of Cluj-Napoca AOI benchmark (Stereo 70 Easting: 392250, Northing: 585200)
  const clujCenter = [46.7695, 23.5898];

  map = L.map("map", {
    center: clujCenter,
    zoom: 17,
    zoomControl: false,
  });

  L.control.zoom({ position: "bottomright" }).addTo(map);

  // CartoDB Dark Matter Basemap
  const darkMatter = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> | ANCPI Stereo 70',
      maxZoom: 20,
      subdomains: "abcd",
    }
  ).addTo(map);

  // Satellite Imagery Option (ESRI World Imagery)
  const esriSat = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
      maxZoom: 19,
    }
  );

  L.control.layers(
    { "CartoDB Dark": darkMatter, "Ortofoto Satelit": esriSat },
    null,
    { position: "topright" }
  ).addTo(map);
}

// ---------------------------------------------------------------------------
// 2. Health & System Telemetry
// ---------------------------------------------------------------------------
async function loadHealthTelemetry() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();

    // QGIS Engine Status
    const qgisDot = document.getElementById("qgis-dot");
    const qgisText = document.getElementById("qgis-status-text");
    if (data.qgis_engine.connected) {
      qgisDot.style.background = "var(--color-emerald)";
      qgisText.textContent = "QGIS Desktop: CONECTAT";
    } else {
      qgisDot.style.background = "var(--color-crimson)";
      qgisText.textContent = "QGIS Desktop: OFFLINE";
    }

    // NIM Status
    const nimText = document.getElementById("nim-status-text");
    if (nimText) {
      nimText.textContent = data.providers.nvidia_nim.available
        ? "NIM Vision: ACTIV"
        : "NIM: INACTIV";
    }

    // Kilo Status
    const kiloText = document.getElementById("kilo-status-text");
    if (kiloText) {
      kiloText.textContent = data.providers.kilo_openrouter.available
        ? "Kilo 70B: READY"
        : "Kilo: INACTIV";
    }
  } catch (err) {
    console.warn("Could not fetch health telemetry:", err);
  }
}

// ---------------------------------------------------------------------------
// 3. Workflow Modes Loader
// ---------------------------------------------------------------------------
async function loadWorkflowModes() {
  const container = document.getElementById("mode-cards-container");
  if (!container) return;

  try {
    const res = await fetch("/api/workflow/modes");
    if (!res.ok) return;
    const modes = await res.json();

    container.innerHTML = "";
    modes.forEach((mode, idx) => {
      const card = document.createElement("div");
      card.className = `mode-card ${idx === 0 ? "active" : ""}`;
      card.dataset.modeId = mode.id;

      card.innerHTML = `
        <div class="mode-card-header">
          <span class="mode-card-title">${mode.name}</span>
          <span class="mode-badge">${mode.badge}</span>
        </div>
        <p class="mode-desc">${mode.description}</p>
      `;

      card.addEventListener("click", () => {
        document.querySelectorAll(".mode-card").forEach((c) => c.classList.remove("active"));
        card.classList.add("active");
        activeModeId = mode.id;
      });

      container.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading workflow modes:", err);
  }
}

// ---------------------------------------------------------------------------
// 4. Load & Render GeoJSON Layers
// ---------------------------------------------------------------------------
async function loadGeoJSONLayers() {
  // Load AI Footprint Candidates (Cyan Polygons)
  try {
    const res = await fetch("/api/layers/geojson/candidates");
    if (res.ok) {
      const fc = await res.json();
      if (fc.features && fc.features.length > 0) {
        if (candidatesLayer) map.removeLayer(candidatesLayer);

        candidatesLayer = L.geoJSON(fc, {
          style: {
            color: "#00f0ff",
            weight: 2,
            opacity: 0.9,
            fillColor: "#00f0ff",
            fillOpacity: 0.25,
          },
          onEachFeature: (feature, layer) => {
            const props = feature.properties || {};
            const area = props.stereo70_area_m2 || "N/A";
            const perim = props.stereo70_length_m || "N/A";
            layer.bindPopup(`
              <div style="font-family: var(--font-mono); font-size: 0.8rem; color: #1e293b;">
                <b style="color: #0284c7;">Amprentă Clădire (StratumRO AI)</b><br/>
                <b>Sistem Ref:</b> Stereo 70 (EPSG:3844)<br/>
                <b>Suprafață (Sc):</b> ${area} mp<br/>
                <b>Perimetru:</b> ${perim} m<br/>
                <b>Destinație TopoLT:</b> 1CC (Construcție)<br/>
                <span style="font-size: 0.7rem; color: #64748b;">90° Regularizat ortogonal</span>
              </div>
            `);
          },
        }).addTo(map);

        map.fitBounds(candidatesLayer.getBounds(), { padding: [40, 40] });
      }
    }
  } catch (err) {
    console.warn("Could not load candidates layer:", err);
  }

  // Load Official Ground Truth (Emerald Polygons)
  try {
    const res = await fetch("/api/layers/geojson/ground_truth");
    if (res.ok) {
      const fc = await res.json();
      if (fc.features && fc.features.length > 0) {
        if (groundTruthLayer) map.removeLayer(groundTruthLayer);

        groundTruthLayer = L.geoJSON(fc, {
          style: {
            color: "#10b981",
            weight: 1.5,
            dashArray: "4, 4",
            opacity: 0.85,
            fillColor: "#10b981",
            fillOpacity: 0.12,
          },
          onEachFeature: (feature, layer) => {
            const props = feature.properties || {};
            layer.bindPopup(`
              <div style="font-family: var(--font-mono); font-size: 0.8rem; color: #1e293b;">
                <b style="color: #059669;">Referință Teren (Ground Truth)</b><br/>
                <b>Identificator:</b> ${props.id || "Cadastru Oficial"}<br/>
                <b>Suprafață:</b> ${props.stereo70_area_m2 || "N/A"} mp
              </div>
            `);
          },
        }).addTo(map);
      }
    }
  } catch (err) {
    console.warn("Could not load ground truth layer:", err);
  }
}

// ---------------------------------------------------------------------------
// 5. Event Listeners & Actions
// ---------------------------------------------------------------------------
function setupEventListeners() {
  // Tab Switch: Map vs QGIS Mirror
  const tabMap = document.getElementById("tab-map");
  const tabQgis = document.getElementById("tab-qgis");
  const mapView = document.getElementById("map");
  const qgisView = document.getElementById("qgis-mirror-view");

  if (tabMap && tabQgis) {
    tabMap.addEventListener("click", () => {
      tabMap.classList.add("active");
      tabQgis.classList.remove("active");
      mapView.style.display = "block";
      qgisView.style.display = "none";
      map.invalidateSize();
    });

    tabQgis.addEventListener("click", () => {
      tabQgis.classList.add("active");
      tabMap.classList.remove("active");
      mapView.style.display = "none";
      qgisView.style.display = "block";
      refreshQGISCanvas();
    });
  }

  // Refresh QGIS Canvas Button
  const btnRefreshCanvas = document.getElementById("btn-refresh-canvas");
  if (btnRefreshCanvas) {
    btnRefreshCanvas.addEventListener("click", refreshQGISCanvas);
  }

  // Run Workflow Button
  const btnRunWorkflow = document.getElementById("btn-run-workflow");
  if (btnRunWorkflow) {
    btnRunWorkflow.addEventListener("click", handleRunWorkflow);
  }

  // Run Kilo Audit Button
  const btnKiloAudit = document.getElementById("btn-kilo-audit");
  if (btnKiloAudit) {
    btnKiloAudit.addEventListener("click", handleKiloAudit);
  }
}

// ---------------------------------------------------------------------------
// 6. QGIS Canvas Refresh
// ---------------------------------------------------------------------------
function refreshQGISCanvas() {
  const img = document.getElementById("qgis-canvas-img");
  const timeTag = document.getElementById("canvas-time");
  if (!img) return;

  img.src = `/api/qgis/canvas?t=${Date.now()}`;
  if (timeTag) {
    timeTag.textContent = new Date().toLocaleTimeString();
  }
}

// ---------------------------------------------------------------------------
// 7. Workflow Execution Handler
// ---------------------------------------------------------------------------
async function handleRunWorkflow() {
  const btn = document.getElementById("btn-run-workflow");
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="pill-dot pulse"></span> Se procesează...`;

  try {
    const res = await fetch("/api/workflow/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: activeModeId, regularize_90: true }),
    });

    const data = await res.json();
    if (res.ok) {
      // Reload layers
      await loadGeoJSONLayers();
      refreshQGISCanvas();
      alert(`Fluxul "${activeModeId}" s-a finalizat cu succes în ${data.duration_sec}s!`);
    } else {
      alert(`Eroare la execuție: ${data.detail || "Eroare necunoscută"}`);
    }
  } catch (err) {
    alert("Eroare de conexiune la serverul StratumRO.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// ---------------------------------------------------------------------------
// 8. Kilo Adversarial Review Handler
// ---------------------------------------------------------------------------
async function handleKiloAudit() {
  const btn = document.getElementById("btn-kilo-audit");
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `Audit în derulare...`;

  const verdictEl = document.getElementById("kilo-verdict");
  const findingsEl = document.getElementById("kilo-findings");
  verdictEl.textContent = "AUDITING...";
  verdictEl.style.borderColor = "var(--color-amber)";
  verdictEl.style.color = "var(--color-amber)";

  try {
    const res = await fetch("/api/kilo/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        milestone_name: "Web Cockpit Live Session Verification",
      }),
    });

    const data = await res.json();
    if (res.ok) {
      verdictEl.textContent = data.verdict || "APPROVED";
      if (data.verdict === "APPROVED") {
        verdictEl.style.borderColor = "var(--color-emerald)";
        verdictEl.style.color = "var(--color-emerald)";
      } else if (data.verdict === "APPROVED_WITH_CONDITIONS") {
        verdictEl.style.borderColor = "var(--color-amber)";
        verdictEl.style.color = "var(--color-amber)";
      } else {
        verdictEl.style.borderColor = "var(--color-crimson)";
        verdictEl.style.color = "var(--color-crimson)";
      }

      if (data.findings && data.findings.length > 0) {
        findingsEl.innerHTML = data.findings.map((f) => `<div>${f}</div>`).join("");
      } else {
        findingsEl.textContent = data.full_review
          ? data.full_review.slice(0, 300) + "..."
          : "Nicio neregulă identificată. Arhitectura respectă regulile AGENTS.md.";
      }
    } else {
      verdictEl.textContent = "EROARE";
      findingsEl.textContent = data.detail || "Nu s-a putut contacta Kilo.";
    }
  } catch (err) {
    verdictEl.textContent = "TIMEOUT";
    findingsEl.textContent = "Conexiunea la OpenRouter / Kilo a eșuat.";
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}
