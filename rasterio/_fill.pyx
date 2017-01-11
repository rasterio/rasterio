# distutils: language = c++
"""Raster fill."""

import uuid

import numpy as np

from rasterio import dtypes

cimport numpy as np

from rasterio._err cimport exc_wrap_int, exc_wrap_pointer
from rasterio._gdal cimport (
    CSLDestroy, CSLSetNameValue, GDALClose, GDALCreate, GDALFillNodata,
    GDALGetDriverByName, GDALGetRasterBand)
from rasterio._io cimport DatasetReaderBase, InMemoryRaster, io_auto

include "gdal.pxi"


def _fillnodata(image, mask, double max_search_distance=100.0,
                int smoothing_iterations=0):
    cdef GDALDriverH driver = NULL
    cdef GDALDatasetH image_dataset = NULL
    cdef GDALRasterBandH image_band = NULL
    cdef GDALDatasetH mask_dataset = NULL
    cdef GDALRasterBandH mask_band = NULL
    cdef char **alg_options = NULL

    driver = GDALGetDriverByName("MEM")

    if dtypes.is_ndarray(image):
        # copy numpy ndarray into an in-memory dataset.
        datasetname = str(uuid.uuid4()).encode('utf-8')
        image_dataset = GDALCreate(
            driver, <const char *>datasetname, image.shape[1], image.shape[0],
            1, <GDALDataType>dtypes.dtype_rev[image.dtype.name], NULL)
        image_band = GDALGetRasterBand(image_dataset, 1)
        io_auto(image, image_band, True)
    elif isinstance(image, tuple):
        rdr = image.ds
        band = (<DatasetReaderBase?>rdr).band(image.bidx)
    else:
        raise ValueError("Invalid source image")

    if dtypes.is_ndarray(mask):
        mask_cast = mask.astype('uint8')
        datasetname = str(uuid.uuid4()).encode('utf-8')
        mask_dataset = GDALCreate(
            driver, <const char *>datasetname, mask.shape[1], mask.shape[0], 1,
            <GDALDataType>dtypes.dtype_rev['uint8'], NULL)
        mask_band = GDALGetRasterBand(mask_dataset, 1)
        io_auto(mask_cast, mask_band, True)
    elif isinstance(mask, tuple):
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")
        elif isinstance(mask, tuple):
            mrdr = mask.ds
            maskband = (<DatasetReaderBase?>mrdr).band(mask.bidx)
    elif mask is None:
        mask_band = NULL
    else:
        raise ValueError("Invalid source image mask")

    try:
        alg_options = CSLSetNameValue(alg_options, "TEMP_FILE_DRIVER", "MEM")
        exc_wrap_int(
            GDALFillNodata(image_band, mask_band, max_search_distance, 0,
                           smoothing_iterations, alg_options, NULL, NULL))
        result = np.empty(image.shape, dtype=image.dtype)
        io_auto(result, image_band, False)
        return result
    finally:
        if image_dataset != NULL:
            GDALClose(image_dataset)
        if mask_dataset != NULL:
            GDALClose(mask_dataset)
        CSLDestroy(alg_options)
