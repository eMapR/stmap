import sys, os
import time, datetime
import numpy as np
import json, yaml, msgpack 
if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
import gdal, ogr, osr

import SpatialReference
from Region import Region
from Asset import Asset, ListAssets
import Reducers
import Outputs

gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()


# Some Constants
URL_BASE = 'http://ltweb.ceoas.oregonstate.edu/mapping/'


    

# Get list of available Assets
def op_list(output='yaml', **kwargs):
    outputDriver = Outputs.getDriver(output)
    return outputDriver(ListAssets())
    
    
# Get metadata about asset
def op_info(asset, output='yaml', **kwargs):
    outputDriver = Outputs.getDriver(output)
    info = Asset(asset).metadata

    # Only yaml natively serializes datetime objects
    if output.lower() != 'yaml':
        if 'band-dates' in info:
            info['band-dates'] = {k:v.isoformat() for k,v in info['band-dates'].iteritems()}
    return outputDriver(info)

def op_icon(asset, **kwargs):
    with open(Asset(asset).getIconFilename(), 'rb') as infile:
        icon = infile.read()
    return icon


def op_window(asset, window, window_size, date,  srs=None, output='png', srs_type='unknown', resample=None, reducers=None, **kwargs):
    
    outputDriver = Outputs.getDriver(output)
    
    DS = Asset(asset)
    if srs:
        SR = SpatialReference.parse(srs, srs_type)
        DS = DS.warpTo(SR, resample)
    data = DS.getWindow(window, date, window_size, resample)
    if reducers:
        data = Reducers.apply(reducers, data)
    
    return outputDriver(data, ds=DS)
    

def op_regions(asset, region, output='json', date=None,  srs=None, srs_type='unknown', resample=None, region_srs=None, region_srs_type='unknown', reducers=None, region_type='json', **kwargs):
    
    outputDriver = Outputs.getDriver(output)
    
    ## Parse the region 
    R = Region(region)
    if region_srs:
        region_SR = SpatialReference.parse(region_srs, region_srs_type)
        R.geom.AssignSpatialReference(region_SR)
    
    DS = Asset(asset)
    if srs:
        SR = SpatialReference.parse(srs, srs_type)
        DS = DS.warpTo(SR, resample)
    
    data,weights = DS.getRegion(R, date, resample)

    if reducers:
        data = Reducers.apply(reducers, data, weights)
    data = data.tolist()
    return outputDriver(data, ds=DS)
    
    
    
OPERATIONS = {
        'window': op_window,
        'regions': op_regions,
        'list': op_list,
        'info': op_info,
        'icon': op_icon
    }
def dispatch(call):

    return OPERATIONS[call['operation']](**call)


    ## Use the following pattern when live,
    ## but let it error out during debugging.
    
    #try:
    #    return OPERATIONS[call['operation']](**call)
    #except TypeError:
    #    return 'Wrong parameters for operation'
    #    
    #except KeyError:
    #    return "No such operation"
        

        
    