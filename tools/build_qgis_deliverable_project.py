# -*- coding: utf-8 -*-
"""
Build a QGIS project from the CURRENT deliverable state and render evidence PNGs.

Run with the QGIS python (not the venv python):
    cmd /c '"C:\\Program Files\\QGIS 3.40.0\\bin\\o4w_env.bat" && ^
           "C:\\Program Files\\QGIS 3.40.0\\bin\\python-qgis.bat" ^
           tools\\build_qgis_deliverable_project.py'

Produces:
  workspace/output/qgis_deliverable_2026-10-08.qgz   project with live layers
  workspace/evidence/01_qgis_deliverable_layers.png   ortho + 147 CLEAN + SOL_ANCPI
  workspace/evidence/02_qgis_safe_margin.png          margin + kept vs eliminated
  workspace/evidence/03_qgis_vlm_audit.png            VLM verdicts over ortho
  workspace/evidence/04_qgis_layers_report.txt        layer inventory + counts
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from qgis.core import (
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsFillSymbol,
    QgsMapSettings, QgsMapRendererParallelJob, QgsProject, QgsRasterLayer,
    QgsRectangle, QgsSingleSymbolRenderer, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

QgsApplication.setPrefixPath(r"C:\PROGRA~1\QGIS34~1.0\apps\qgis-ltr", True)
app = QgsApplication([], False)
app.initQgis()

GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
ORTHO = os.path.join(ROOT, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
NDSM = os.path.join(ROOT, "workspace", "output", "ndsm_stereo70.tif")
EVID = os.path.join(ROOT, "workspace", "evidence")
os.makedirs(EVID, exist_ok=True)

CRS = QgsCoordinateReferenceSystem("EPSG:3844")

report_lines = []


def log(msg):
    print(msg, flush=True)
    report_lines.append(str(msg))


def vec(name, style_color, width=0.6, outline="#000000", ow=0.16, opacity=1.0):
    lyr = QgsVectorLayer("%s|layername=%s" % (GPKG, name), name, "ogr")
    if not lyr.isValid():
        log("  [FAIL] %s" % name)
        return None
    sym = QgsFillSymbol.createSimple({
        "color": style_color,
        "outline_color": outline,
        "outline_width": str(ow),
        "outline_width_unit": "MM",
    })
    sym.setOpacity(opacity)
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    n = lyr.featureCount()
    area = 0.0
    for f in lyr.getFeatures():
        area += f.geometry().area()
    log("  OK  %-34s %4d feat  %7.2f ha" % (name, n, area / 10000.0))
    return lyr


log("=== QGIS DELIVERABLE BUILD %s ===" % Qgis.QGIS_VERSION)
log("gpkg: %s (%.1f MB)" % (os.path.basename(GPKG), os.path.getsize(GPKG) / 1e6))

proj = QgsProject.instance()
proj.clear()
proj.setCrs(CRS)

# ---------------- raster ----------------
log("\n--- rasters ---")
ortho = QgsRasterLayer(ORTHO, "ORTOFOTO_RGB", "gdal")
if ortho.isValid():
    proj.addMapLayer(ortho)
    log("  OK  ORTOFOTO_RGB")
else:
    log("  [FAIL] ORTOFOTO_RGB -> %s" % ORTHO)
ndsm = QgsRasterLayer(NDSM, "NDSM_LIDAR", "gdal")
if ndsm.isValid():
    proj.addMapLayer(ndsm)
    log("  OK  NDSM_LIDAR")

# ---------------- deliverable vectors ----------------
log("\n--- deliverable vectors ---")
layers = {}
layers["CLEAN"] = vec("CLADIRI_CADASTRU_CLEAN", "255,60,60,150", 0.6, "#7a0000", 0.30)
layers["SOL"] = vec("CLADIRI_SOL_ANCPI", "60,160,255,130", 0.4, "#003a7a", 0.25)
layers["ELIM"] = vec("CLADIRI_ELIMINATE_MARGINE_UNSAFE", "255,160,0,170", 0.5, "#7a4a00", 0.28)
layers["MARGIN"] = vec("MARGINE_SIGURANTA_ORTOFOTO", "0,0,0,0", 0.3, "#00e5ff", 0.9)
layers["VLM"] = vec("VLM_REAL_AUDIT", "160,0,220,190", 0.4, "#ffffff", 0.22)
layers["HYBRID"] = vec("CLADIRI_HIBRID", "0,200,120,110", 0.3, "#00543a", 0.18)
layers["UNC"] = vec("UNCLASSIFIED", "150,150,150,70", 0.2, "#555555", 0.12)

for k in ("CLEAN", "SOL", "ELIM", "VLM", "HYBRID"):
    if layers.get(k):
        proj.addMapLayer(layers[k])

root = proj.layerTreeRoot()
ortho_node = root.findLayer(ortho.id())
if ortho_node:
    root.insertChildNode(0, ortho_node.clone())
    ortho_node.setItemVisibilityChecked(True)

# ---------------- extent ----------------
ext = QgsRectangle()
for k in ("CLEAN", "ELIM"):
    if layers.get(k):
        e = layers[k].extent()
        if ext.isEmpty():
            ext = QgsRectangle(e)
        else:
            ext.combineExtentWith(e)
log("\nextent: %.1f %.1f %.1f %.1f" % (ext.xMinimum(), ext.yMinimum(),
                                        ext.xMaximum(), ext.yMaximum()))

QGZ = os.path.join(ROOT, "workspace", "output", "qgis_deliverable_2026-10-08.qgz")
proj.write(QGZ)
log("project written: %s" % QGZ)


def do_render(layers_on, path, extent, size=(2400, 1600)):
    for lyr_id in list(proj.mapLayers().keys()):
        node = root.findLayer(lyr_id)
        if node:
            node.setItemVisibilityChecked(lyr_id in layers_on)
    ms = QgsMapSettings()
    ms.setLayers([proj.mapLayer(l) for l in layers_on if proj.mapLayer(l)])
    ms.setBackgroundColor(QColor(255, 255, 255))
    ms.setOutputSize(QSize(*size))
    ms.setDestinationCrs(CRS)
    ms.setExtent(extent)
    job = QgsMapRendererParallelJob(ms)
    job.start()
    job.waitForFinished()
    img = job.renderedImage()
    img.save(path, "PNG")
    log("  rendered -> %s (%dx%d, %d layers)"
        % (os.path.basename(path), size[0], size[1], len(layers_on)))
    return path


ids = {k: (v.id() if v else None) for k, v in layers.items()}
raster_ids = [l.id() for l in (ortho, ndsm) if l and l.isValid()]

# 1) deliverable over ortho
if layers["CLEAN"]:
    do_render([ids["SOL"], ids["CLEAN"]] + raster_ids[:1],
              os.path.join(EVID, "01_qgis_deliverable_layers.png"), ext)

# 2) safe margin decision
if layers["ELIM"]:
    do_render([ids["ELIM"], ids["CLEAN"], ids["MARGIN"]] + raster_ids[:1],
              os.path.join(EVID, "02_qgis_safe_margin.png"), ext)

# 3) VLM audit
if layers["VLM"]:
    do_render([ids["VLM"], ids["CLEAN"]] + raster_ids[:1],
              os.path.join(EVID, "03_qgis_vlm_audit.png"), ext)

# 4) zoom on the DENSEST spatial cluster so shapes are actually readable.
#    Picking the 12 largest buildings does NOT zoom: they are spread across the
#    whole campus, so the combined extent collapses back to the full AOI.
if layers["CLEAN"]:
    feats = [(f.id(), f.geometry()) for f in layers["CLEAN"].getFeatures()]
    pts = [g.centroid().asPoint() for _, g in feats]
    best = None
    for i, _ in enumerate(feats):
        near = [(p.x() ** 2 + p.y() ** 2) ** 0.5
                for p in pts]
        d = sorted(near)
        # count how many centroids fall inside a 90 m radius of centroid i
        cx, cy = pts[i].x(), pts[i].y()
        cnt = sum(1 for p in pts
                  if (p.x() - cx) ** 2 + (p.y() - cy) ** 2 <= 90.0 ** 2)
        if best is None or cnt > best[0]:
            best = (cnt, cx, cy)
    cnt, cx, cy = best
    z = QgsRectangle(cx - 95, cy - 95, cx + 95, cy + 95)
    do_render([ids["CLEAN"], ids["SOL"]] + raster_ids[:1],
              os.path.join(EVID, "04_qgis_zoom_cluster.png"), z)
    log("  zoom cluster: %d buildings within 90 m of (%.0f, %.0f)" % (cnt, cx, cy))

    # same cluster with the eliminated set, to show what P2 removed
    do_render([ids["ELIM"], ids["CLEAN"], ids["MARGIN"]] + raster_ids[:1],
              os.path.join(EVID, "06_qgis_zoom_cluster_margin.png"), z)

# 5) nDSM hillshade + footprints
if ndsm.isValid() and layers["CLEAN"]:
    do_render([ids["CLEAN"]] + raster_ids,
              os.path.join(EVID, "05_qgis_ndsm_footprints.png"), ext)

# ---------------- attribute report ----------------
log("\n=== ATTRIBUTE EVIDENCE (CLADIRI_CADASTRU_CLEAN) ===")
if layers["CLEAN"]:
    lyr = layers["CLEAN"]
    cols = [f.name() for f in lyr.fields()]
    log("columns (%d): %s" % (len(cols), ", ".join(cols)))
    h = [f["inaltime_med_m"] for f in lyr.getFeatures() if f["inaltime_med_m"] is not None]
    hx = [f["inaltime_max_m"] for f in lyr.getFeatures() if f["inaltime_max_m"] is not None]
    a = [f["area_m2"] for f in lyr.getFeatures() if f["area_m2"] is not None]
    log("inaltime_med_m : n=%d min=%.2f max=%.2f unique=%d"
        % (len(h), min(h), max(h), len(set(round(x, 4) for x in h))))
    log("inaltime_max_m : n=%d min=%.2f max=%.2f unique=%d"
        % (len(hx), min(hx), max(hx), len(set(round(x, 4) for x in hx))))
    log("area_m2        : n=%d min=%.1f max=%.1f sum=%.1f m2"
        % (len(a), min(a), max(a), sum(a)))
    log("above 7.8 m    : %d / %d buildings (old hard-coded max was 7.8)"
        % (sum(1 for x in hx if x > 7.8), len(hx)))
    nc = [f.geometry().area() for f in lyr.getFeatures()]
    log("geometry area sum: %.1f m2  (attribute sum %.1f m2)"
        % (sum(nc), sum(a)))
    bad = max(abs(g - at) for g, f in zip(nc, lyr.getFeatures())
              if f["area_m2"] is not None for at in [f["area_m2"]])
    log("max |attr area - geom area| = %.6f m2" % bad)

log("\n=== ALL LAYERS IN PROJECT ===")
for lid, lyr in proj.mapLayers().items():
    cnt = ""
    if hasattr(lyr, "featureCount") and lyr.isValid():
        try:
            cnt = "%d feat" % lyr.featureCount()
        except Exception:
            cnt = ""
    log("  %-34s %-14s %s" % (lyr.name(), lyr.type(), cnt))

out = os.path.join(EVID, "04_qgis_layers_report.txt")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(report_lines))
log("\nreport -> %s" % out)

app.exitQgis()
print("DONE")