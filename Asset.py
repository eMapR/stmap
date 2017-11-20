import os, sys
import datetime
from glob import glob
import numpy as np

if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'/usr/lib/anaconda/share/gdal'
from osgeo import gdal, ogr, osr, gdalconst
import json, yaml

RESAMPLE_METHODS = {'average': gdalconst.GRIORA_Average,
                    'bilinear': gdalconst.GRIORA_Bilinear,
                    'cubic': gdalconst.GRIORA_Cubic,
                    'cubicspline': gdalconst.GRIORA_CubicSpline,
                    'gauss': gdalconst.GRIORA_Gauss,
                    'lanczos': gdalconst.GRIORA_Lanczos,
                    'mode': gdalconst.GRIORA_Mode,
                    'nearest': gdalconst.GRIORA_NearestNeighbour
                }

        
DATA_PATH = '/data/maps/'
    
def ListAssets():
    
    def getList(dirname):
        L = []
        dirlist = os.listdir(dirname)
        if 'default.vrt' in dirlist:
            L.append('')
            
        for fn in dirlist:
            full_path = os.path.join(dirname, fn)
            if os.path.isdir(full_path):
                L += [fn+x  for x in getList(full_path)]
            elif (fn[-4:] == '.vrt') and (fn != 'default.vrt'):
                L.append('.'+fn[:-4])
        return L
        
    return getList(DATA_PATH)

    
    
    
class Asset:    
    def __init__(self, name):
        self.name = name
        self.ds = ''
        self.path = ''
        self.metadata = {}
        
        # Identify the underlying (virtual) file
        tree = name.split('.')
        if len(tree) == 1:
            tree.append('default')
        fn = os.path.join(DATA_PATH, *tree) + '.vrt'
         
        # If found, get metadata, if any, from along path
        if os.path.exists(fn):
            self.path = fn
            self.ds = gdal.Open(fn)
            t = self.ds.GetGeoTransform()
            self.metadata['native-resolution'] = [t[1] , t[5]]
            self.metadata['native-UL'] = [t[0], t[3]]
            self.metadata['native-size'] = [self.ds.RasterCount, self.ds.RasterXSize, self.ds.RasterYSize]
            self.metadata['native-projection'] = self.ds.GetProjection()
            if 'nodata' not in self.metadata:
                self.metadata['nodata'] = None
            
            for i in range(len(tree)):
                for f in  ['.yaml', '/default.yaml', '/'+tree[i]+'.yaml']:
                    fn = os.path.join(DATA_PATH, *tree[:i+1]) + f
                    if os.path.exists(fn):
                        with open(fn, 'r') as m:
                            self.metadata.update(yaml.safe_load(m))

            self.bandDates = self.metadata['band-dates']

        
    def getResampleMethod(self, name):
        try:
            method = RESAMPLE_METHODS[name]
        except KeyError:
            try:
                method = RESAMPLE_METHODS[self.metadata['resample-method']]
            except KeyError:   
                method = gdalconst.GRIORA_NearestNeighbour
        return method
    
    def getIconFilename(self):
        for x in ['jpg', 'png', 'gif', 'bmp']:
            fn = self.path.replace('.vrt', '_icon.'+x)
            if os.path.exists(fn):
                return fn
        return ''
        
    
    def warpTo(self, srs, resampleMethod):
        resampleMethod = self.getResampleMethod(resampleMethod)
        
        ## Get the auto-generated warped VRT. It'll need some work.
        tmp_ds = gdal.AutoCreateWarpedVRT(self.ds, None, srs.ExportToWkt(), resampleMethod)
        
        ## Read the XML text of the warped VRT
        memfilename = '/vsimem/tmp_'+str(id(self))+'_'+str(id(srs))+'.vrt'
        driver = gdal.GetDriverByName('VRT')
        driver.CreateCopy(memfilename, tmp_ds)
        filehandle = gdal.VSIFOpenL(memfilename, 'r')
        stat = gdal.VSIStatL(memfilename)
        XML = gdal.VSIFReadL(1, stat.size, filehandle)
        gdal.VSIFCloseL(filehandle)
        gdal.Unlink(memfilename)
        
        ## Set the INIT_DEST option to pay attention to NoData values
        XML = XML.replace('<Option name="INIT_DEST">0</Option>', '<Option name="INIT_DEST">NO_DATA</Option>')
        
        ## Set NoData values for each source band in the bandlist.
        # Define the XML templates
        VRT_BAND_WARPED = '<BandMapping src="{src}" dst="{dst}" />'
        VRT_BAND_NODATA_TEMPLATE = """
            <BandMapping src="{src}" dst="{dst}">
                <SrcNoDataReal>{nd}</SrcNoDataReal>
                <SrcNoDataImag>0</SrcNoDataImag>
                <DstNoDataReal>{nd}</DstNoDataReal>
                <DstNoDataImag>0</DstNoDataImag>
            </BandMapping>
        """
        # Loop over each band and set it's nodata value.
        for b in range(1,self.ds.RasterCount+1):
            nd = self.ds.GetRasterBand(b).GetNoDataValue()
            XML = XML.replace(VRT_BAND_WARPED.format(src=b, dst=b), VRT_BAND_NODATA_TEMPLATE.format(src=b, dst=b,nd=nd))
       
        ## Set the new VRT XML as the current dataset
        self.ds = gdal.Open(XML);
            
        return self
            
            
    def parseBands(self, date):
        #Get the band either from the request string or by choosing a nearest date
        if date[0] == 'b':
            bands = int(date[1:])
        else:
            bands = self.bandsByDate(date)
        
        return bands
        
    
    def datesToBands(self, dates=None):
    # Select bands corresponding to the specified dates
        if dates is None:
            return self.bandDates.keys().sort()

        dates = [yaml.safe_load(dates)]
        bands = []
        if len(dates) == 1:
            distance = datetime.date.max - datetime.date.min
            for b in self.bandDates:
                d = np.abs(self.bandDates[b] - dates[0])
                if d < distance:
                    bands = [b]
                    distance = d
        else:
            for b in self.bandDates:
                if self.bandDates[b] >= dates[0] and self.bandDates[b] <= dates[1]:
                    bands.append(b)
        
        return bands
    
    
    
    def getWindow(self, bounds, dates, size, resampleMethod=None):
        resampleMethod = self.getResampleMethod(resampleMethod)
        bands = self.datesToBands(dates)
        
        xOrigin, pixelWidth, xSkew, yOrigin, ySkew, pixelHeight = self.ds.GetGeoTransform()
        
        # Figure out where the Upper Left corner is
        xmin, ymin, xmax, ymax = bounds
        ULx = xmin if pixelWidth>0 else xmax
        ULy = ymin if pixelHeight>0 else ymax
        
        # Get the region to read
        xoff = ((ULx - xOrigin)/pixelWidth)
        yoff = ((ULy - yOrigin)/pixelHeight)
        xcount = ((xmax - xmin)/abs(pixelWidth))
        ycount = ((ymax - ymin)/abs(pixelHeight))
        
        data = np.zeros((len(bands), size[0], size[1]))
        mask = np.zeros((len(bands), size[0], size[1]), np.bool)
        nd = self.metadata['nodata']
        for i, b in enumerate(bands):
            band = self.ds.GetRasterBand(b)
            d = band.ReadAsArray(xoff, yoff, xcount, ycount, size[0], size[1], resample_alg=resampleMethod)
            mask[i,:,:] = np.equal(d, band.GetNoDataValue()) #+ np.equal(d,nd)
            data[i,:,:] = d
        data = np.ma.MaskedArray(data, mask)
        
        return data
        

    def getRegion(self, region, dates=None, resampleMethod=None):
    
        resampleMethod = self.getResampleMethod(resampleMethod)
        bands = self.datesToBands(dates)
        
        # Determine if need to grab just a single pixel or a region
        isPoint = (region.geom.GetGeometryName() == 'POINT')

        if isPoint:
            # Grab just the single pixel covering the Point
            xoff, yoff = self.getRasterOffset(region)
            xcount, ycount = (1,1)
        else:
            # Get mask of region in raster-space
            proj = self.ds.GetProjectionRef()
            transform =  self.ds.GetGeoTransform()
            weights, offsets = region.rasterize(proj, transform, 1)
            xoff, yoff = offsets
            ycount, xcount = mask.shape
            
        # if bands isn't specified, read data in all of them
        if not bands:
            bands = range(1,self.ds.RasterCount+1)

        # Read raster data
        data = np.zeros((len(bands), xcount, ycount))
        mask = np.zeros((len(bands), xcount, ycount), np.bool)
        nd = self.metadata['nodata']
        for b in bands:
            band = self.ds.GetRasterBand(b)
            d = band.ReadAsArray(xoff, yoff, xcount, ycount).astype(np.float)
            mask[b-1,:,:] = np.equal(d,band.GetNoDataValue()) + np.equal(d,nd)
            data[b-1,:,:] = d
            
        data = np.ma.MaskedArray(data, mask)    
        return data, weights
        
        
    def getRasterOffset(self, point):
        # Get the raster pixel coordinate of a point (possibly in a different projection)
        point = point.reproject(self.ds)
        x, y = point.GetPoints()[0]
        transform = self.ds.GetGeoTransform()
        xOrigin, pixelWidth, xSkew, yOrigin, ySkew, pixelHeight = transform
        xoff = int((x - xOrigin)/pixelWidth)
        yoff = int((y - yOrigin)/pixelHeight)

        return xoff, yoff

        
#### END DATASET CLASS ####

