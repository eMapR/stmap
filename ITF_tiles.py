import sys
sys.path.append('/var/www/html/mapping/stmap/')

import webapp2
from operations import dispatch
from cache import cache_disk
from timeout_decorator import timeout

REQUEST_PATH = '/TMS/';
CACHE_PATH = '/data/apicache/'

# WebApp2 servlet to handle requests for WMS tiles
class TileHandler(webapp2.RequestHandler):
    def get(self, *path):
        # params keep both GET and POST values
        query_data = self.request.params
        R = parseTileRequest(*path)
        self.response.headers['Content-Type'] = "image/png"
        self.response.write(R)

    # Do same thing on GET and POST methods
    def post(self, path=''):
        self.get(path)
        
# Initialize the webapp handlers.
application = webapp2.WSGIApplication([
    (REQUEST_PATH+'(.+?)/(.+?)/(\d+)/(\d+)/(\d+).png', TileHandler),
], debug=True)


#@cache_disk(CACHE_PATH)

@timeout(5)
def parseTileRequest(asset, date, zoom, x, y):
    # Parses a request for an image tile. Request paths are in the form:
    # http://ltweb.ceoas.oregonstate.edu/mapping/tiles/asset/band_or_date/zoom/y/x.png

    # Well known text for Web Mercator projection used by Web Mapping libaries
    # Equivillent to EPSG:3857, but without the need to look it up on disk
    TMS_WKT = 'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]'
    
    
    # Determine the boundaries for the given tile
    bounds = tileBounds(x, y, zoom)
    
    # Build an API call to get the tile as a PNG
    command = {'operation': 'window',
               'asset': asset,
               'window': bounds,
               'date': date,
               'srs': TMS_WKT,
               'srs_type': 'WKT',
               'window_size': [256,256],
               'output': 'PNG'
               }
    
    # Dispatch the API call and return the result
    return dispatch(command)
    
def tileBounds(tx, ty, zoom):
    '''Returns bounds of the given tile in EPSG:900913 coordinates'''
    
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
    
def googleTile(tx, ty, zoom):
    '''Converts TMS tile coordinates to Google Tile coordinates'''
    return (tx, 2**zoom - 1 - ty)

    
    