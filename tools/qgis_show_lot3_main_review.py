"""Show the current Lot3 review in the shared QGIS project and save evidence."""
from pathlib import Path
import json
from qgis.core import QgsProject, QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob
from qgis.PyQt.QtCore import QSize, QTimer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.utils import iface

ROOT = Path('C:/Users/lefpa/Downloads/QGIS-AI')
PROJECT = ROOT / 'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
OUT = ROOT / 'workspace/reviews/lot3_main_display_20261017'
pointer = json.loads((ROOT / 'workspace/reviews/lot3_repairs_20261017/CURRENT_SELECTION.json').read_text())
p = QgsProject.instance()
assert Path(p.fileName()).resolve() == PROJECT.resolve(), 'Wrong QGIS project'
assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l, 'isEditable'))
root = p.layerTreeRoot()
group = root.findGroup(pointer['shared_group'])
assert group is not None
layers = [n.layer() for n in group.findLayers() if n.layer().type() == 0]
assert len(layers) == 1
roofs = layers[0]
assert roofs.isValid() and roofs.featureCount() == pointer['feature_count']
expected = ROOT / 'workspace/reviews/lot3_repairs_20261017' / pointer['gpkg']
assert Path(roofs.source().split('|')[0]).resolve() == expected.resolve()
OUT.mkdir(exist_ok=False)
(OUT / '.gitattributes').write_text('* -text\n', encoding='utf-8')
before = {'project': p.fileName(), 'dirty': p.isDirty(), 'extent': iface.mapCanvas().extent().asWktPolygon()}
(OUT / 'before.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
for child in root.children():
    if child.name().startswith('LOT3'):
        child.setExpanded(child == group)
group.setItemVisibilityChecked(True)
group.setExpanded(True)
for node in group.findLayers():
    node.setItemVisibilityChecked(True)
for child in group.children():
    if hasattr(child, 'children'):
        child.setExpanded(False)
iface.setActiveLayer(roofs)
extent = QgsRectangle(roofs.extent())
extent.scale(1.13)
iface.mapCanvas().setExtent(extent)
iface.mapCanvas().refresh()
window = iface.mainWindow()
window.showMaximized()
window.raise_()
window.activateWindow()
for dock in window.findChildren(QDockWidget):
    if dock.objectName() in ['MessageLog', 'ProcessingToolbox', 'QmsServiceToolbox', 'Browser', 'LayerOrder']:
        dock.hide()
assert p.write(), 'Project save failed'
native = [n.layer() for n in group.findLayers() if n.layer().type() == 1]
orthos = [l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
settings = QgsMapSettings()
settings.setDestinationCrs(p.crs())
settings.setLayers([roofs] + native + orthos)
settings.setExtent(extent)
settings.setOutputSize(QSize(1600, 1250))
settings.setBackgroundColor(QColor('white'))
job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()
assert job.renderedImage().save(str(OUT / 'lot3_main_overview.png'))

def capture_main_review():
    assert iface.mapCanvas().grab().save(str(OUT / 'live_canvas.png'))
    assert iface.mainWindow().grab().save(str(OUT / 'live_main_window.png'))
    state = {'project': p.fileName(), 'saved': not p.isDirty(), 'layer_id': roofs.id(),
             'layer_name': roofs.name(), 'source': roofs.source(), 'feature_count': roofs.featureCount(),
             'visible': root.findLayer(roofs.id()).isVisible(), 'case_count': pointer['case_count'],
             'extent': iface.mapCanvas().extent().asWktPolygon(), 'owner_verdict_changed': False}
    (OUT / 'display_verification.json').write_text(json.dumps(state, indent=2), encoding='utf-8')

def focus_after_layout():
    iface.mapCanvas().setExtent(extent)
    iface.mapCanvas().refresh()
    assert p.write()
    QTimer.singleShot(1800, capture_main_review)

QTimer.singleShot(400, focus_after_layout)
print('Main QGIS project saved; overview displayed; capture scheduled.')
