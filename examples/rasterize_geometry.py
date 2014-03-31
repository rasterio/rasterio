import logging
import numpy
import sys
import rasterio
from rasterio.features import rasterize


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterize_geometry')


rows = cols = 10
transform = [0, 1, 0, 0, 0, 1]
geometry = {'type':'Polygon','coordinates':[[(2,2),(2,4.25),(4.25,4.25),(4.25,2),(2,2)]]}
with rasterio.drivers():
    result = rasterize([geometry], out_shape=(rows, cols), transform=transform)
    with rasterio.open(
            "test.tif",
            'w',
            driver='GTiff',
            width=cols,
            height=rows,
            count=1,
            dtype=numpy.uint8,
            nodata=0,
            transform=transform,
            crs={'init': "EPSG:4326"}) as out:
        out.write_band(1, result.astype(numpy.uint8))
