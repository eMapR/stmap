import sys, os
import time, datetime
import numpy as np
import json, yaml, msgpack 
if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
import gdal, ogr, osr

from operations import dispatch
import SpatialReference
from Region import Region
from Asset import Asset, ListAssets
import Reducers
import Outputs
import re


def parseTileRequest(asset, date, zoom, x, y):
    # Parses a request for an image tile. Request paths are in the form:
    # http://ltweb.ceoas.oregonstate.edu/mapping/tiles/asset/band_or_date/zoom/y/x.png

    # Well known text for Web Mercator projection used by Web Mapping libaries
    # Equivillent to EPSG:3857, but without the need to look it up on disk
    TMS_WKT = 'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]'
    
    
    # Determine the boundaries for the given tile
    bounds = tileBounds(x, y, zoom)
    
    # Build an API call to get the tile as a PNG
    C={'operation': 'window',
       'asset': asset,
       'window': bounds,
       'date': date,
       'srs': TMS_WKT,
       'srs_type': 'WKT',
       'window_size': [256,256],
       'output': 'py'
       }
       
    
    a = op_window(**C)
       
       
    #a = dispatch(C)


    print [a[0][0][0,0,(0, 128, 255)].data], [a[0][0][0,0,(0, 128, 255)].mask]
               
def op_window(asset, window, window_size, date,  srs=None, output='png', srs_type='unknown', resample=None, reducers=None, **kwargs):
    
    outputDriver = Outputs.getDriver(output)
    
    DS = Asset(asset)
    if srs:
        SR = SpatialReference.parse(srs, srs_type)
        DS = DS.warpTo(SR, resample)
    
    
    
    driver = gdal.GetDriverByName('VRT')
    driver.CreateCopy('/data/apicache/'+asset + '_warped.vrt', DS.ds)
    
    
    data = DS.getWindow(window, date, window_size, resample)
    if reducers:
        data = Reducers.apply(reducers, data)
    
    return outputDriver(data, ds=DS)
    
               
               
    '''Returns bounds of the given tile in EPSG:900913 coordinates'''
def tileBounds(tx, ty, zoom):
    
    tx= float(tx); ty = float(ty); zoom=float(zoom)
    
    #basis = 2 * math.pi * 6378137 
    basis = 40075016.68557849

    z = 2**zoom;
    ty = z-1-ty
    minx = basis * (tx/z - 0.5)
    miny = basis * (ty/z - 0.5)
    maxx = basis * ((tx+1)/z - 0.5)
    maxy = basis * ((ty+1)/z - 0.5)   
    
    return (minx, miny, maxx, maxy)
    
if __name__ == '__main__':
    parseTileRequest('WAORCA_biomass.default', '1990-06-01', 7,19, 47)
    #parseTileRequest('WAORCA_biomass.default_warp', '1990-06-01', 7,19, 47)
    #parseTileRequest('WAORCA_biomass.default_vrt', '1990-06-01', 7,19, 47)
    #parseTileRequest('WAORCA_biomass.default_warp2', '1990-06-01', 7,19, 47)
