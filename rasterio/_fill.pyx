# distutils: language = c++

"""Raster fill."""

include "gdal.pxi"

import numpy as np
from rasterio._err cimport exc_wrap_int
from rasterio._io cimport MemoryDataset


def _fillnodata(image, mask, double max_search_distance=100.0, int smoothing_iterations=0):
    """Fill missing data regions of a 2-D image array

    Returns a 2-D array.
    """
    cdef GDALRasterBandH image_band = NULL
    cdef GDALRasterBandH mask_band = NULL
    cdef char **alg_options = NULL
    cdef MemoryDataset image_dataset = None
    cdef MemoryDataset mask_dataset = None

    try:
        # copy numpy ndarray into an in-memory dataset.
        image_dataset = MemoryDataset(image)
        image_band = image_dataset.band(1)

        if mask is not None:
            mask_cast = mask.astype('uint8')
            mask_dataset = MemoryDataset(mask_cast)
            mask_band = mask_dataset.band(1)

        alg_options = CSLSetNameValue(alg_options, "TEMP_FILE_DRIVER", "MEM")
        exc_wrap_int(
            GDALFillNodata(image_band, mask_band, max_search_distance, 0,
                           smoothing_iterations, alg_options, NULL, NULL))

        # MemoryData is multi-band, but this function returns a single
        # band's data.
        return np.asarray(image_dataset)[0]

    finally:
        if image_dataset is not None:
            image_dataset.close()
        if mask_dataset is not None:
            mask_dataset.close()
        CSLDestroy(alg_options)
