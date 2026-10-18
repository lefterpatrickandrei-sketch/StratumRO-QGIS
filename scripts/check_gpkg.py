from osgeo import ogr
ds = ogr.Open(r'C:\Users\lefpa\Downloads\QGIS-AI\workspace\UAT_Giurgiu\data\output\UAT_Giurgiu.gpkg')
for i in range(ds.GetLayerCount()):
    l = ds.GetLayerByIndex(i)
    print(l.GetName(), l.GetFeatureCount(), l.GetGeomType())
ds = None