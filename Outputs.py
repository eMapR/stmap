import os, sys
import datetime
import numpy as np
import png as PNG

if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
from osgeo import gdal, ogr, osr, gdalconst
import json, yaml,msgpack

## Output drivers
def toJSON(data, **kwargs):
    return json.dumps(data)
def toYAML(data, **kwargs):
    return yaml.dump(data)
def toMsgPack(data, **kwargs):
    return msgpack.packb(data)
def identity(*args, **kwargs):
    return (args, kwargs)

def toPNG(data, ds, **kwargs):
    image = data
    if data.ndim == 3:
        image = np.squeeze(image[0,:,:])

    if 'legend' in ds.metadata:
        pal = np.zeros(256, dtype=np.uint32)
        for k,v in ds.metadata['legend'].iteritems():
            pal[k] = v[1]
        png = PNG.Build(image.filled(0), pal)
    else:
        image = rescaleTo8Bit(image, **ds.metadata['map-scaling'])
        png = PNG.Build(image.filled(0))
    
    return png
    
    
def rescaleTo8Bit(data, min=0, max=1):
    data = data.astype(np.float)
    min = float(min)
    max = float(max)
    
    out = np.ceil(255*(data-min)/(max-data))
    out[out<1] = 1
    out[out>255] = 255
    
    return out.astype(np.uint8)
    
    
# Safely map input strings to output drivers
OUTPUT_DRIVERS = {
    'json': toJSON,
    'yaml': toYAML,
    'msgpack': toMsgPack,
    'png': toPNG,
    'py': identity
    }
def getDriver(name):
    DEFAULT='json'
    try:
        driver = OUTPUT_DRIVERS[name.lower()]
    except KeyError:
        driver = OUTPUT_DRIVERS[DEFAULT]
    return driver
    