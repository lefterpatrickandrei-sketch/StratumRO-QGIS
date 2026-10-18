"""Execute inside the existing QGIS bridge; reads state and saves audit evidence."""
import json
from pathlib import Path
from qgis.core import QgsProject, QgsVectorLayer
from qgis.utils import iface

out=Path("C:/Users/lefpa/Downloads/QGIS-AI/workspace/project_verification_20261018")
p=QgsProject.instance()
rows=[]
for l in p.mapLayers().values():
    item={"id":l.id(),"name":l.name(),"source":l.source(),"valid":l.isValid(),"crs":l.crs().authid()}
    if isinstance(l,QgsVectorLayer):
        item.update(count=l.featureCount(),editable=l.isEditable(),modified=l.isModified())
    rows.append(item)
state={"path":p.fileName(),"dirty":p.isDirty(),"layer_count":len(rows),"layers":rows,
       "canvas_layers":[l.id() for l in iface.mapCanvas().layers()]}
(out/"live_qgis_snapshot.json").write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding="utf-8")
iface.mapCanvas().saveAsImage(str(out/"live_qgis_canvas.png"))
print(json.dumps({"path":state["path"],"dirty":state["dirty"],"layer_count":len(rows),
                  "invalid_layers":[l["name"] for l in rows if not l["valid"]],
                  "layers_without_crs":[l["name"] for l in rows if not l["crs"]],
                  "modified_layers":[l["name"] for l in rows if l.get("modified")]}))
