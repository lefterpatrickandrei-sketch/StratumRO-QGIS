# -*- coding: utf-8 -*-
import traceback

try:
    from qgis.core import (
        QgsProject, QgsVectorLayer, QgsFillSymbol, QgsMarkerSymbol,
        QgsSingleSymbolRenderer, QgsRectangle, QgsPalLayerSettings,
        QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
    )
    from qgis.utils import iface
    from qgis.PyQt.QtGui import QColor, QFont

    p = QgsProject.instance()
    root = p.layerTreeRoot()
    expected_project = 'C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
    if p.fileName().replace('\\', '/').lower() != expected_project.lower():
        raise RuntimeError(f'Wrong shared project: {p.fileName()}; expected {expected_project}')
    if p.isDirty() or any(getattr(l, 'isEditable', lambda: False)() for l in p.mapLayers().values()):
        raise RuntimeError('Unsaved project or editable layers; reconcile user changes first')

    # 1. Manage legacy Lot 3 group: set to unchecked historical
    old_grp = root.findGroup('LOT3_T11_T20_IN_VERIFICARE')
    if old_grp:
        old_grp.setName('LOT3_ISTORIC_INITIAL_NEACCEPTAT')
        old_grp.setItemVisibilityChecked(False)
        for ch in old_grp.children():
            ch.setItemVisibilityChecked(False)
        print('Historical Lot 3 group disabled')

    # Remove existing revision group if rerunning
    rev_grp_name = 'LOT3_REVIZIE_T11_T20'
    existing_rev = root.findGroup(rev_grp_name)
    if existing_rev:
        for child in list(existing_rev.children()):
            if hasattr(child, 'layerId'):
                p.removeMapLayer(child.layerId())
        root.removeChildNode(existing_rev)

    for l in list(p.mapLayers().values()):
        if l.name().startswith('LOT3_REV_'):
            p.removeMapLayer(l.id())

    # Create new revision group at top
    rev_grp = root.insertGroup(0, rev_grp_name)
    rev_grp.setExpanded(True)
    rev_grp.setItemVisibilityChecked(True)

    gpkg_base = 'C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_revision_20261013/results/lot3_revision_results.gpkg'

    def make_label_settings(field_name, text_color, buffer_color, size_pt=9):
        settings = QgsPalLayerSettings()
        settings.fieldName = field_name
        settings.isExpression = False
        settings.enabled = True
        
        tformat = QgsTextFormat()
        font = QFont('Segoe UI', size_pt, QFont.Bold)
        tformat.setFont(font)
        tformat.setSize(size_pt)
        tformat.setColor(QColor(text_color))
        
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(1.0)
        buf.setColor(QColor(buffer_color))
        tformat.setBuffer(buf)
        settings.setFormat(tformat)
        return settings

    # Layer 1: LOT3_REV_CORPURI_EXTRASE
    ds_corp = f"{gpkg_base}|layername=CORPURI_EXTRASE_LOT3"
    lyr_corp = QgsVectorLayer(ds_corp, 'LOT3_REV_CORPURI_EXTRASE', 'ogr')
    if lyr_corp.isValid():
        sym_corp = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',
            'outline_color': '#00e5ff',
            'outline_width': '0.7',
            'outline_style': 'solid'
        })
        lyr_corp.setRenderer(QgsSingleSymbolRenderer(sym_corp))
        lbl_corp = make_label_settings('id', '#00b0ff', '#ffffff', 9)
        lyr_corp.setLabeling(QgsVectorLayerSimpleLabeling(lbl_corp))
        lyr_corp.setLabelsEnabled(True)
        p.addMapLayer(lyr_corp, False)
        node_corp = rev_grp.addLayer(lyr_corp)
        node_corp.setItemVisibilityChecked(True)
        print(f"Added LOT3_REV_CORPURI_EXTRASE: {lyr_corp.featureCount()} features")
    else:
        raise RuntimeError('Failed to load CORPURI_EXTRASE_LOT3')

    # Layer 2: LOT3_REV_CAZURI_NERECUPERATE
    ds_nerec = f"{gpkg_base}|layername=CAZURI_NERECUPERATE_LOT3"
    lyr_nerec = QgsVectorLayer(ds_nerec, 'LOT3_REV_CAZURI_NERECUPERATE', 'ogr')
    if lyr_nerec.isValid():
        sym_nerec = QgsMarkerSymbol.createSimple({
            'name': 'cross',
            'size': '4.0',
            'color': '#ff1744',
            'outline_color': '#ff1744',
            'outline_width': '0.8'
        })
        lyr_nerec.setRenderer(QgsSingleSymbolRenderer(sym_nerec))
        lbl_nerec = make_label_settings('test_id', '#d50000', '#ffffff', 9)
        lyr_nerec.setLabeling(QgsVectorLayerSimpleLabeling(lbl_nerec))
        lyr_nerec.setLabelsEnabled(True)
        p.addMapLayer(lyr_nerec, False)
        node_nerec = rev_grp.addLayer(lyr_nerec)
        node_nerec.setItemVisibilityChecked(True)
        print(f"Added LOT3_REV_CAZURI_NERECUPERATE: {lyr_nerec.featureCount()} features")
    else:
        raise RuntimeError('Failed to load CAZURI_NERECUPERATE_LOT3')

    # Layer 3: LOT3_REV_FERESTRE_SELECTIE
    ds_sel = f"{gpkg_base}|layername=FERESTRE_SELECTIE_LOT3"
    lyr_sel = QgsVectorLayer(ds_sel, 'LOT3_REV_FERESTRE_SELECTIE', 'ogr')
    if lyr_sel.isValid():
        sym_sel = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',
            'outline_color': '#ffd700',
            'outline_width': '0.4',
            'outline_style': 'dash'
        })
        lyr_sel.setRenderer(QgsSingleSymbolRenderer(sym_sel))
        lbl_sel = make_label_settings('test_id', '#e65100', '#ffffff', 8)
        lyr_sel.setLabeling(QgsVectorLayerSimpleLabeling(lbl_sel))
        lyr_sel.setLabelsEnabled(True)
        p.addMapLayer(lyr_sel, False)
        node_sel = rev_grp.addLayer(lyr_sel)
        node_sel.setItemVisibilityChecked(True)
        print(f"Added LOT3_REV_FERESTRE_SELECTIE: {lyr_sel.featureCount()} features")
    else:
        raise RuntimeError('Failed to load FERESTRE_SELECTIE_LOT3')

    # Layer 4: LOT3_REV_MASCA_BRUTA (unchecked)
    ds_raw = f"{gpkg_base}|layername=MASCA_BRUTA_SAM2"
    lyr_raw = QgsVectorLayer(ds_raw, 'LOT3_REV_MASCA_BRUTA', 'ogr')
    if lyr_raw.isValid():
        sym_raw = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',
            'outline_color': '#9c27b0',
            'outline_width': '0.3',
            'outline_style': 'dot'
        })
        lyr_raw.setRenderer(QgsSingleSymbolRenderer(sym_raw))
        p.addMapLayer(lyr_raw, False)
        node_raw = rev_grp.addLayer(lyr_raw)
        node_raw.setItemVisibilityChecked(False)
        print(f"Added LOT3_REV_MASCA_BRUTA (unchecked): {lyr_raw.featureCount()} features")

    # Set canvas extent to encompass all Lot 3 revision cases
    if iface and iface.mapCanvas():
        ext = QgsRectangle(390550.0, 585050.0, 391380.0, 585680.0)
        iface.mapCanvas().setExtent(ext)
        iface.mapCanvas().refresh()

    if not lyr_corp.isValid() or lyr_corp.featureCount() != 6:
        raise RuntimeError(f'Unexpected extracted bodies count: {lyr_corp.featureCount()}; expected 6')
    if not lyr_nerec.isValid() or lyr_nerec.featureCount() != 6:
        raise RuntimeError(f'Unexpected unrecovered count: {lyr_nerec.featureCount()}; expected 6')
    if not lyr_sel.isValid() or lyr_sel.featureCount() != 10:
        raise RuntimeError(f'Unexpected selection window count: {lyr_sel.featureCount()}; expected 10')

    if not p.write():
        raise RuntimeError('Project save failed')
    print('PYQGIS_SUCCESS')
except Exception as e:
    print('PYQGIS_EXCEPTION:', traceback.format_exc())
