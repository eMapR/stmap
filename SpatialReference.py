import os
if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
from osgeo import osr

"""
@type should be one of:

WKT: Well Known Text 
PROJ4: proj4 
EPSG: EPSG GCS or PCS code, either as "EPSG:####" or "####"
ESRI or PRJ: ESRI .prj format
GML: Geography Markup Language CRS 
MAPINFO: MapInfo style CoordSys definition
OZI: OziExplorer .MAP file
URN: OGC URN prefixed with "urn:ogc:def:crs"  (not yet supported?)
WMSAUTO: Projections from the WMS AUTO:##### namespace
"""

def parse(input, type):

    if not isinstance(input, osr.SpatialReference):
        
        type = str(type).lower()
        srs = osr.SpatialReference()
        
        if type == 'wkt':
            srs.ImportFromWkt(input)
        if type == 'proj4':
            srs.ImportFromProj4(input)
        if type == 'epsg':
            srs.ImportFromEPSG(int(input.split(':')[-1]))   
        if type == 'esri' or type=='pjr':
            srs.ImportFromESRI(input)
        if type == 'gml' or type=='xml':
            srs.ImportFromXML(input)
        if type == 'mapinfo':
            srs.ImportFromMICoordSys(input)
        if type == 'ozi':
            srs.ImportFromOzi(input)
        #if type == 'urn':
        #    srs.ImportFromURN(input)
        if type == 'wmsauto':
            srs.ImportFromWMSAUTO(input)
        if type == 'unknown' or type == '':
            srs.SetFromUserinput(input)
        
    return srs
