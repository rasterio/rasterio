# distutils: language = c++
"""Raster fill."""

import numpy as np
cimport numpy as np

from rasterio import dtypes
from rasterio._err import CPLErrors
from rasterio cimport _gdal, _io
from rasterio._io cimport InMemoryRaster

include "gdal.pxi"


def _fillnodata(image, mask, double max_search_distance=100.0,
                int smoothing_iterations=0):
    cdef GDALDriverH driver = NULL
    cdef GDALDatasetH image_dataset = NULL
    cdef GDALRasterBandH image_band = NULL
    cdef GDALDatasetH mask_dataset = NULL
    cdef GDALRasterBandH mask_band = NULL
    cdef char **alg_options = NULL

    driver = _gdal.GDALGetDriverByName("MEM")

    if dtypes.is_ndarray(image):
        # copy numpy ndarray into an in-memory dataset.
        image_dataset = _gdal.GDALCreate(
            driver,
            "image",
            image.shape[1],
            image.shape[0],
            1,
            <_gdal.GDALDataType>dtypes.dtype_rev[image.dtype.name],
            NULL)
        image_band = _gdal.GDALGetRasterBand(image_dataset, 1)
        _io.io_auto(image, image_band, True)
    elif isinstance(image, tuple):
        rdr = image.ds
        band = (<_io.DatasetReaderBase?>rdr).band(image.bidx)
    else:
        raise ValueError("Invalid source image")

    if dtypes.is_ndarray(mask):
        mask_cast = mask.astype('uint8')
        mask_dataset = _gdal.GDALCreate(
            driver,
            "mask",
            mask.shape[1],
            mask.shape[0],
            1,
            <_gdal.GDALDataType>dtypes.dtype_rev['uint8'],
            NULL)
        mask_band = _gdal.GDALGetRasterBand(mask_dataset, 1)
        _io.io_auto(mask_cast, mask_band, True)
    elif isinstance(mask, tuple):
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")
        elif isinstance(mask, tuple):
            mrdr = mask.ds
            maskband = (<_io.DatasetReaderBase?>mrdr).band(mask.bidx)
    elif mask is None:
        mask_band = NULL
    else:
        raise ValueError("Invalid source image mask")

    try:
        with CPLErrors() as cple:
            alg_options = _gdal.CSLSetNameValue(
                alg_options, "TEMP_FILE_DRIVER", "MEM")
            _gdal.GDALFillNodata(
                image_band, mask_band, max_search_distance, 0,
                smoothing_iterations, alg_options, NULL, NULL)
            cple.check()
        # read the result into a numpy ndarray
        result = np.empty(image.shape, dtype=image.dtype)
        _io.io_auto(result, image_band, False)
    finally:
        if image_dataset != NULL:
            _gdal.GDALClose(image_dataset)
        if mask_dataset != NULL:
            _gdal.GDALClose(mask_dataset)
        _gdal.CSLDestroy(alg_options)

    return result
