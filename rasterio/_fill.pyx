# distutils: language = c++
"""Raster fill."""

include "gdal.pxi"

import uuid

import numpy as np

from rasterio import dtypes

cimport numpy as np

from rasterio._err cimport exc_wrap_int, exc_wrap_pointer
from rasterio._io cimport DatasetReaderBase, InMemoryRaster, io_auto


def _fillnodata(image, mask, double max_search_distance=100.0,
                int smoothing_iterations=0):
    cdef GDALDriverH driver = NULL
    cdef GDALDatasetH image_dataset = NULL
    cdef GDALRasterBandH image_band = NULL
    cdef GDALDatasetH mask_dataset = NULL
    cdef GDALRasterBandH mask_band = NULL
    cdef char **alg_options = NULL

    driver = GDALGetDriverByName("MEM")

    # copy numpy ndarray into an in-memory dataset.
    datasetname = str(uuid.uuid4()).encode('utf-8')
    image_dataset = GDALCreate(
        driver, <const char *>datasetname, image.shape[1], image.shape[0],
        1, <GDALDataType>dtypes.dtype_rev[image.dtype.name], NULL)
    image_band = GDALGetRasterBand(image_dataset, 1)
    io_auto(image, image_band, True)

    if mask is not None:
        mask_cast = mask.astype('uint8')
        datasetname = str(uuid.uuid4()).encode('utf-8')
        mask_dataset = GDALCreate(
            driver, <const char *>datasetname, mask.shape[1], mask.shape[0], 1,
            <GDALDataType>dtypes.dtype_rev['uint8'], NULL)
        mask_band = GDALGetRasterBand(mask_dataset, 1)
        io_auto(mask_cast, mask_band, True)

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
