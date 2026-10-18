"""Keep orthophoto detail patches below vector evidence in a shared project."""


def vectors_above_rasters(project):
    """Preserve relative orders/visibility, changing only rendering priority.

    Nested raster groups otherwise hide parts of roof outlines from older lots.
    This changes no feature, verdict, source, tree group or raster pixel.
    """
    from qgis.core import QgsMapLayerType
    root=project.layerTreeRoot()
    current=list(root.layerOrder())
    vectors=[l for l in current if l.type()==QgsMapLayerType.VectorLayer]
    others=[l for l in current if l.type() not in (QgsMapLayerType.VectorLayer,QgsMapLayerType.RasterLayer)]
    rasters=[l for l in current if l.type()==QgsMapLayerType.RasterLayer]
    order=vectors+others+rasters
    root.setCustomLayerOrder(order)
    root.setHasCustomLayerOrder(True)
    return [l.id() for l in order]
