"""Run in existing QGIS: render selected audit cases without changing the project."""
import json
from pathlib import Path
from qgis.core import (QgsProject, QgsVectorLayer, QgsRectangle, QgsMapSettings,
                       QgsMapRendererParallelJob, QgsFillSymbol, QgsCoordinateReferenceSystem,
                       QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

root=Path("C:/Users/lefpa/Downloads/QGIS-AI")
out=root/"workspace/project_verification_20261018"
audit=json.loads((out/"output_audit.json").read_text(encoding="utf-8"))
basemaps=[l for l in QgsProject.instance().mapLayers().values() if l.name().startswith("Cluj-")]
cases=[("rest_complex", "rest", ["REST_260:C1"]), ("option_a_complex", "option_a", ["T39:C1"])]
b=audit["datasets"]["option_b"]
pair=max(b["positive_overlap_pairs"],key=lambda x:x["area_m2"])
cases.append(("option_b_overlap","option_b",[b["features"][pair[k]]["body_id"] for k in ("a","b")]))
manifest=[]
for name,key,ids in cases:
    d=audit["datasets"][key]
    layer=QgsVectorLayer(str(root/d["path"])+"|layername="+d["layer"],name,"ogr")
    expr='"body_id" IN ('+','.join("'"+s.replace("'","''")+"'" for s in ids)+')'
    assert layer.setSubsetString(expr) and layer.featureCount()==len(ids)
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({"color":"0,0,0,0","outline_color":"255,110,0,255","outline_width":"0.65"}))
    pal=QgsPalLayerSettings();pal.fieldName="body_id"
    fmt=QgsTextFormat();fmt.setSize(11);fmt.setColor(QColor("white"))
    buffer=fmt.buffer();buffer.setEnabled(True);buffer.setSize(1);buffer.setColor(QColor("black"));fmt.setBuffer(buffer)
    pal.setFormat(fmt);layer.setLabeling(QgsVectorLayerSimpleLabeling(pal));layer.setLabelsEnabled(True)
    layer.updateExtents();extent=QgsRectangle(layer.extent());extent.scale(1.35)
    settings=QgsMapSettings();settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
    settings.setLayers([layer]+basemaps);settings.setExtent(extent);settings.setOutputSize(QSize(1000,850))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished()
    path=out/(name+".png");assert job.renderedImage().save(str(path))
    manifest.append({"image":path.name,"body_ids":ids,"dataset":d["path"],"layer":d["layer"],"source_sha256":d["sha256"],"extent":[extent.xMinimum(),extent.yMinimum(),extent.xMaximum(),extent.yMaximum()]})
(out/"visual_cases.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest))
