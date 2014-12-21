# distutils: language = c++
# cython: profile=True
#

import numpy as np
cimport numpy as np

from rasterio._io cimport InMemoryRaster
from rasterio cimport _gdal, _io

def _fillnodata(image, mask, double max_search_distance=100.0, int smoothing_iterations=0):
    cdef void *hband
    cdef void *hmaskband
    cdef char **options = NULL
    cdef _io.RasterReader rdr
    cdef _io.RasterReader mrdr
    cdef InMemoryRaster mem_ds = None
    cdef InMemoryRaster mask_ds = None
    
    if isinstance(image, np.ndarray):
        mem_ds = InMemoryRaster(image)
        hband = mem_ds.band
    elif isinstance(image, tuple):
        rdr = image.ds
        hband = rdr.band(image.bidx)
    else:
        raise ValueError("Invalid source image")
    
    if isinstance(mask, np.ndarray):
        # A boolean mask must be converted to uint8 for GDAL
        mask_ds = InMemoryRaster(mask.astype('uint8'))
        hmaskband = mask_ds.band
    elif isinstance(mask, tuple):
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")
        mrdr = mask.ds
        hmaskband = mrdr.band(mask.bidx)
    else:
        hmaskband = NULL
    
    result = _gdal.GDALFillNodata(hband, hmaskband, max_search_distance, 0, smoothing_iterations, options, NULL, NULL)
    
    if isinstance(image, np.ndarray):
        _io.io_auto(image, hband, False)
    
    if mem_ds is not None:
        mem_ds.close()
    if mask_ds is not None:
        mask_ds.close()
    
    return result
