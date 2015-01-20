# distutils: language = c++
# cython: profile=True
#

import numpy as np
cimport numpy as np

from rasterio import dtypes
from rasterio._err import cpl_errs
from rasterio cimport _gdal, _io

from rasterio._io cimport InMemoryRaster


def _fillnodata(image, mask, double max_search_distance=100.0, int smoothing_iterations=0):
    cdef void *memdriver = _gdal.GDALGetDriverByName("MEM")
    cdef void *image_dataset
    cdef void *image_band
    cdef void *mask_dataset
    cdef void *mask_band
    cdef char **alg_options = NULL

    if isinstance(image, np.ndarray):
        # copy numpy ndarray into an in-memory dataset
        image_dataset = _gdal.GDALCreate(
            memdriver,
            "image",
            image.shape[1],
            image.shape[0],
            1,
            <_gdal.GDALDataType>dtypes.dtype_rev[image.dtype.name],
            NULL)
        image_band = _gdal.GDALGetRasterBand(image_dataset, 1)
        _io.io_auto(image, image_band, True)
    elif isinstance(image, tuple):
        # TODO
        raise NotImplementedError()
    else:
        raise ValueError("Invalid source image")

    if isinstance(mask, np.ndarray):
        mask_cast = mask.astype('uint8')
        mask_dataset = _gdal.GDALCreate(
            memdriver,
            "mask",
            mask.shape[1],
            mask.shape[0],
            1,
            <_gdal.GDALDataType>dtypes.dtype_rev['uint8'],
            NULL)
        mask_band = _gdal.GDALGetRasterBand(mask_dataset, 1)
        _io.io_auto(mask_cast, mask_band, True)
    elif isinstance(mask, tuple):
        # TODO
        raise NotImplementedError()
    elif mask is None:
        mask_band = NULL
    else:
        raise ValueError("Invalid source image mask")

    with cpl_errs:
        alg_options = _gdal.CSLSetNameValue(
                alg_options, "TEMP_FILE_DRIVER", "MEM")
        _gdal.GDALFillNodata(
                image_band,
                mask_band,
                max_search_distance,
                0,
                smoothing_iterations,
                alg_options,
                NULL,
                NULL)

    # read the result into a numpy ndarray
    result = np.empty(image.shape, dtype=image.dtype)
    _io.io_auto(result, image_band, False)

    _gdal.GDALClose(image_dataset)
    _gdal.GDALClose(mask_dataset)
    _gdal.CSLDestroy(alg_options)

    return result
