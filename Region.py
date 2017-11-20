import os, sys
import numpy as np

if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
from osgeo import gdal, ogr, osr, gdalconst



class Region:
    
    def __init__(self, region, region_type='json'):
        
        region = region.encode('utf-8');
        if region_type.lower() == 'gml':
            self.geom = ogr.CreateGeometryFromGML(region)
        elif region_type.lower() == 'wkt':
            self.geom = ogr.CreateGeomgeryFromWkt(region)
        else:
            self.geom = ogr.CreateGeometryFromJson(region.encode('utf-8'))
       

    def rasterize(self, projection, transform, burn_value=1):
        # Reproject vector geometry to same projection as raster
        rasterSR = osr.SpatialReference()
        rasterSR.ImportFromWkt(projection)
        G = reproject(self.geom, rasterSR)

        # Get raster georeference info
        xOrigin, pixelWidth, xSkew, yOrigin, ySkew, pixelHeight = transform

        # Get region boundary in raster-space
        xmin, ymin, xmax, ymax = getBounds(G)

        # Figure out where the Upper Left corner is
        ULx = xmin if pixelWidth>0 else xmax
        ULy = ymin if pixelHeight>0 else ymax

        xoff = int((ULx - xOrigin)/pixelWidth)
        yoff = int((ULy - yOrigin)/pixelHeight)
        xcount = int((xmax - xmin)/abs(pixelWidth))+1
        ycount = int((ymax - ymin)/abs(pixelHeight))+1

        # Build an in-memory vector layer in order to rasterize it
        region_ds = ogr.GetDriverByName('Memory').CreateDataSource('memdata')
        region_lyr = region_ds.CreateLayer('region', srs=rasterSR )
        feat = ogr.Feature( region_lyr.GetLayerDefn() )
        feat.SetGeometry(G)
        region_lyr.CreateFeature(feat)

        if burn_value.lower() == 'mask':
            xcount *= 16
            ycount *= 16
            pixelWidth/=16
            pixelHeight/=16
        
        # Create in-memory target raster to burn the layer into
        mask_ds = gdal.GetDriverByName('MEM').Create('', xcount, ycount, 1, gdal.GDT_Byte)
        mask_ds.SetGeoTransform( ( xmin, pixelWidth, 0, ymax, 0, pixelHeight ))
        mask_ds.SetProjection(rasterSR.ExportToWkt())

        # Rasterize zone polygon to raster
        
        if burn_value.lower() == 'mask':
            gdal.RasterizeLayer(mask_ds, [1], region_lyr, burn_values=[255])
            mask = mask_ds.ReadAsArray(0, 0, xcount, ycount, xcount/16, ycount/16, resample_alg=GRIORA_Average)
        else:
            gdal.RasterizeLayer(mask_ds, [1], region_lyr, burn_values=[burn_value])
            mask = mask_ds.ReadAsArray(0, 0, xcount, ycount)

        return mask, (xoff, yoff)
        
                

def reproject(geom, target):

    sourceSR = geom.GetSpatialReference()

    # Target may be a spatial reference, a geometry, or a raster
    if isinstance(target, osr.SpatialReference):
        targetSR = target
    elif hasattr(target, 'GetSpatialReference'):
        targetSR = target.GetSpatialReference()
    else:
        targetSR = osr.SpatialReference()
        targetSR.ImportFromWkt(target.GetProjectionRef())

    coordTrans = osr.CoordinateTransformation(sourceSR, targetSR)
    geom.Transform(coordTrans)

    return geom
    
    
def getBounds(geom):

    if geom.GetGeometryName() == 'LINESTRING':
        points = geom.GetPoints()
    else:
        # Collect vertices into a list
        points = []
        for g in geom:
            points += g.GetPoints()

    # Get min and max
    points = np.array(points)
    xmin, ymin = np.min(points, axis=0)
    xmax, ymax = np.max(points, axis=0)

    return ( xmin, ymin, xmax, ymax)
    
    