# rasterio

import os

from six import string_types

from rasterio._io import RasterReader, RasterUpdater
import rasterio.dtypes
from rasterio.dtypes import (
    ubyte, uint8, uint16, int16, uint32, int32, float32, float64)

def open(
        path, mode='r', 
        driver=None,
        width=None, height=None,
        count=None,
        dtype=None,
        crs=None, transform=None):
    """Open file at ``path`` in ``mode`` "r" (read), "r+" (read/write),
    or "w" (write) and return a ``Reader`` or ``Updater`` object.
    
    In write mode, a driver name such as "GTiff" or "JPEG" (see GDAL
    docs or ``gdan_translate --help`` on the command line), ``width``
    (number of pixels per line) and ``height`` (number of lines), the
    ``count`` number of bands in the new file must be specified.
    Additionally, the data type for bands such as ``rasterio.ubyte`` for
    8-bit bands or ``rasterio.uint16`` for 16-bit bands must be
    specified using the ``dtype`` argument.

    A coordinate reference system for raster datasets in write mode can
    be defined by the ``crs`` argument. It takes Proj4 style mappings
    like
    
      {'proj': 'longlat', 'ellps': 'WGS84', 'datum': 'WGS84',
       'no_defs': True}
    
    A geo-transform matrix that maps pixel coordinates to coordinates in
    the specified crs should be specified using the ``transform``
    argument. This matrix is represented by a six-element sequence.
    
    Item 0: the top left x value 
    Item 1: W-E pixel resolution 
    Item 2: rotation, 0 if the image is "north up" 
    Item 3: top left y value 
    Item 4: rotation, 0 if the image is "north up"
    Item 5: N-S pixel resolution (usually a negative number)
    """
    if not isinstance(path, string_types):
        raise TypeError("invalid path: %r" % path)
    if mode and not isinstance(mode, string_types):
        raise TypeError("invalid mode: %r" % mode)
    if driver and not isinstance(driver, string_types):
        raise TypeError("invalid driver: %r" % driver)
    if mode in ('r', 'r+'):
        if not os.path.exists(path):
            raise IOError("no such file or directory: %r" % path)
    
    if mode == 'r':
        s = RasterReader(path)
    elif mode == 'r+':
        raise NotImplemented("r+ mode not implemented")
        # s = RasterUpdater(path, mode, driver=None)
    elif mode == 'w':
        s = RasterUpdater(
                path, mode, driver,
                width, height, count, 
                crs, transform, dtype)
    else:
        raise ValueError(
            "mode string must be one of 'r', 'r+', or 'w', not %s" % mode)
    
    s.start()
    return s

def check_dtype(dt):
    tp = getattr(dt, 'type', dt)
    return tp in rasterio.dtypes.dtype_rev

