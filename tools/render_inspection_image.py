import os
import sys
from qgis.core import (
    QgsApplication, QgsProject, QgsMapSettings, QgsMapRendererParallelJob,
    QgsCoordinateReferenceSystem, QgsRectangle
)
from PyQt5.QtCore import QSize

qgs = QgsApplication([], False)
qgs.initQgis()

project = QgsProject.instance()
project.read('StratumRO_Inspectie_Vizuala.qgz')

settings = QgsMapSettings()
# Order of layers: top to bottom -> Ground Truth, AI Pred, Ortofoto
l_gt = [l for l in project.mapLayers().values() if l.name().startswith("4.")][0]
l_pred = [l for l in project.mapLayers().values() if l.name().startswith("3.")][0]
l_ortho = [l for l in project.mapLayers().values() if l.name().startswith("1.")][0]

settings.setLayers([l_gt, l_pred, l_ortho])
settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# Zoom extent covering the central USAMV buildings
bbox = QgsRectangle(390620.0, 585350.0, 391180.0, 585780.0)
settings.setExtent(bbox)
settings.setOutputSize(QSize(2400, 1840))

job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()

img = job.renderedImage()
out_png = os.path.abspath("workspace/output/inspectie_orto_cadastru_ai.png")
img.save(out_png, "PNG")
print("[+] Rendered high-res inspection map to:", out_png)

qgs.exitQgis()
