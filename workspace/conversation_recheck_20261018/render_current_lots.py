"""Execute in existing QGIS; render actual Lot4/Lot5 data without changing UI.

PNG evidence remains local under reviews/, respecting the code/docs-only policy
found in the owner-authorized Antigravity conversation. No inference is run.
"""
import hashlib
import json
from pathlib import Path
from qgis.core import (QgsProject,QgsVectorLayer,QgsRasterLayer,QgsRectangle,
                       QgsMapSettings,QgsMapRendererParallelJob,QgsFillSymbol,
                       QgsCoordinateReferenceSystem,QgsPalLayerSettings,
                       QgsVectorLayerSimpleLabeling,QgsTextFormat)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

root=Path("C:/Users/lefpa/Downloads/QGIS-AI")
meta=root/"workspace/conversation_recheck_20261018"
out=root/"workspace/reviews/conversation_recheck_20261018"
out.mkdir(parents=True,exist_ok=True)
p=QgsProject.instance()
basemaps=[l for l in p.mapLayers().values() if l.name().startswith("Cluj-")]
state={"filename":p.fileName(),"dirty":p.isDirty(),"canvas_layers":[l.id() for l in iface.mapCanvas().layers()],"layers":[]}
for l in p.mapLayers().values():
    if isinstance(l,QgsVectorLayer) and any(s in l.name() for s in ("LOT3 -","LOT4 -","LOT5 -","OPT_B","REST -")):
        n=p.layerTreeRoot().findLayer(l.id())
        state["layers"].append({"id":l.id(),"name":l.name(),"source":l.source(),"count":l.featureCount(),"checked":n.itemVisibilityChecked() if n else False,"effective_visible":n.isVisible() if n else False,"in_canvas":l.id() in state["canvas_layers"]})
(meta/"live_sources.json").write_text(json.dumps(state,indent=2),encoding="utf-8")

entries=[]
for prefix,path,layer,ids in [
    ("lot4","workspace/reviews/lot4_20261017/selected_v4_orthogonal/lot4_orthogonal.gpkg","ROOF_HYPOTHESES_ORTHO90",range(21,31)),
    ("lot5","workspace/reviews/comparatie_a_vs_b_20261018/comparatie_a_vs_b.gpkg","LOT5_OPTIUNEA_A_ROOF",range(31,41))]:
    for number in ids:
        bid=f"T{number}:C1"
        v=QgsVectorLayer(str(root/path)+"|layername="+layer,bid,"ogr")
        assert v.setSubsetString('"body_id" = '+"'"+bid+"'") and v.featureCount()==1
        v.renderer().setSymbol(QgsFillSymbol.createSimple({"color":"0,0,0,0","outline_color":"0,240,255,255","outline_width":"0.65"}))
        pal=QgsPalLayerSettings();pal.fieldName="body_id"
        fmt=QgsTextFormat();fmt.setSize(12);fmt.setColor(QColor("white"))
        buf=fmt.buffer();buf.setEnabled(True);buf.setSize(1);buf.setColor(QColor("black"));fmt.setBuffer(buf)
        pal.setFormat(fmt);v.setLabeling(QgsVectorLayerSimpleLabeling(pal));v.setLabelsEnabled(True)
        v.updateExtents();extent=QgsRectangle(v.extent());extent.scale(1.3)
        rasters=list(basemaps)
        cover=root/f"workspace/reviews/lot4_20261017/covers/T{number}_5cm.tif"
        if prefix=="lot4" and cover.exists():
            detail=QgsRasterLayer(str(cover),"detail")
            if detail.isValid():rasters=[detail]+rasters
        settings=QgsMapSettings();settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
        settings.setLayers([v]+rasters);settings.setExtent(extent);settings.setOutputSize(QSize(1000,850))
        job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished()
        dest=out/f"{prefix}_T{number}.png";assert job.renderedImage().save(str(dest))
        entries.append({"body_id":bid,"path":dest.relative_to(root).as_posix(),"source":path,"layer":layer,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),"versioned":False})
assert state["dirty"]==p.isDirty()
assert state["canvas_layers"]==[l.id() for l in iface.mapCanvas().layers()]
(meta/"visual_manifest.json").write_text(json.dumps(entries,indent=2),encoding="utf-8")
print(json.dumps({"rendered":len(entries),"project_dirty_before_and_after":p.isDirty(),"canvas_unchanged":True,"images_versioned":False}))
