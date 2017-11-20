import sys
sys.path.append('/var/www/html/mapping/stmap/')

import json, yaml
import imghdr
import webapp2
from operations import dispatch
from cache import cache_disk


# Some Contants
REQUEST_PATH = '/bridgeAPI';          # where this webapp is mounted / virtual hosted
CACHE_PATH = '/data/apicache/'

# WebApp2 servlet to handle requests for timeseries over the patch data
class DataHandler(webapp2.RequestHandler):
    def get(self, path=''):
        # params keep both GET and POST values
        GET = self.request.params
        R = parseRequest(GET)
        self.response.headers.update(R['headers'])
        self.response.write(R['data'])

    # Do same thing on GET and POST methods
    def post(self, path=''):
        self.get(path)

# Initialize the webapp handlers.
application = webapp2.WSGIApplication([
    (REQUEST_PATH, DataHandler),
], debug=True)


# Parse web request, pass it to operations.dispatch(),
# parse response, and return it the web app
#@cache_disk(CACHE_PATH)
def parseRequest(request):
    request = {k.lower():v  for k,v in request.iteritems()}
    if len(request) == 1:
        if 'json' in request:
            request.update(json.loads(request['json']))
        elif 'yaml' in request:
            request.update(yaml.safe_load(request['yaml']))
    
    # dispatch() should always return a binary string of data
    # Support detecting different kinds of data and responding
    # with appropriate headers back to the webapp.
    R = {'headers':{}, 'data':''}
    R['data'] = dispatch(request)
    
    # Detect if an image, and if so, add an image Content-Type
    #imghdr returns None if image isn't detected
    img = imghdr.what('', R['data'])
    if img: 
        R['headers'].update({'Content-Type': "image/"+img})
    
    return R
    






