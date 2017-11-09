"""Rasterio shim for GDAL 1.x"""

include "directives.pxi"

# The baseline GDAL API.
include "gdal.pxi"

# Implementation specific to GDAL<2.0
from rasterio import dtypes
from rasterio.enums import Resampling

cimport numpy as np
from rasterio._err cimport exc_wrap_pointer


cdef GDALDatasetH open_dataset(
        object filename, int flags, object allowed_drivers, object open_options,
        object siblings) except NULL:
    """Wrapper for GDALOpen and GDALOpenShared"""
    cdef const char *fname = NULL
    cdef const char **drivers = NULL
    cdef const char **options = NULL
    cdef const char *key = NULL
    cdef const char *val = NULL
    cdef const char *driver = NULL
    cdef GDALDatasetH hds = NULL

    filename = filename.encode('utf-8')
    fname = filename

    # Note well: driver choice, open options, and sibling files
    # are not supported by GDAL versions < 2.0.
    if flags & 0x20:
        with nogil:
            GDALOpenShared(fname, <int>(flags & 0x01))
    else:
        with nogil:
            hds = GDALOpen(fname, <int>(flags & 0x01))

    return exc_wrap_pointer(hds)


cdef int delete_nodata_value(GDALRasterBandH hBand) except 3:
    raise NotImplementedError(
        "GDAL versions < 2.1 do not support nodata deletion")


cdef int io_band(GDALRasterBandH band, int mode, float x0, float y0,
                 float width, float height, object data, int resampling=0):
    """Read or write a region of data for the band.

    Implicit are

    1) data type conversion if the dtype of `data` and `band` differ.
    2) decimation if `data` and `band` shapes differ.

    The striding of `data` is passed to GDAL so that it can navigate
    the layout of ndarray views.
    """
    # GDAL handles all the buffering indexing, so a typed memoryview,
    # as in previous versions, isn't needed.
    cdef void *buf = <void *>np.PyArray_DATA(data)
    cdef int bufxsize = data.shape[1]
    cdef int bufysize = data.shape[0]
    cdef int buftype = dtypes.dtype_rev[data.dtype.name]
    cdef int bufpixelspace = data.strides[1]
    cdef int buflinespace = data.strides[0]

    cdef int xoff = <int>x0
    cdef int yoff = <int>y0
    cdef int xsize = <int>width
    cdef int ysize = <int>height
    cdef int retval = 3

    with nogil:
        retval = GDALRasterIO(
            band, mode, xoff, yoff, xsize, ysize, buf, bufxsize, bufysize,
            buftype, bufpixelspace, buflinespace)

    return retval


cdef int io_multi_band(GDALDatasetH hds, int mode, float x0, float y0,
                       float width, float height, object data,
                       long[:] indexes, int resampling=0):
    """Read or write a region of data for multiple bands.

    Implicit are

    1) data type conversion if the dtype of `data` and bands differ.
    2) decimation if `data` and band shapes differ.

    The striding of `data` is passed to GDAL so that it can navigate
    the layout of ndarray views.
    """
    cdef int i = 0
    cdef int retval = 3
    cdef int *bandmap = NULL
    cdef void *buf = <void *>np.PyArray_DATA(data)
    cdef int bufxsize = data.shape[2]
    cdef int bufysize = data.shape[1]
    cdef int buftype = dtypes.dtype_rev[data.dtype.name]
    cdef int bufpixelspace = data.strides[2]
    cdef int buflinespace = data.strides[1]
    cdef int bufbandspace = data.strides[0]
    cdef int count = len(indexes)

    cdef int xoff = <int>x0
    cdef int yoff = <int>y0
    cdef int xsize = <int>width
    cdef int ysize = <int>height

    with nogil:
        bandmap = <int *>CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = GDALDatasetRasterIO(
            hds, mode, xoff, yoff, xsize, ysize, buf,
            bufxsize, bufysize, buftype, count, bandmap,
            bufpixelspace, buflinespace, bufbandspace)
        CPLFree(bandmap)

    return retval


cdef int io_multi_mask(GDALDatasetH hds, int mode, float x0, float y0,
                       float width, float height, object data,
                       long[:] indexes, int resampling=0):
    """Read or write a region of data for multiple band masks.

    Implicit are

    1) data type conversion if the dtype of `data` and bands differ.
    2) decimation if `data` and band shapes differ.

    The striding of `data` is passed to GDAL so that it can navigate
    the layout of ndarray views.
    """
    cdef int i = 0
    cdef int j = 0
    cdef int retval = 3
    cdef GDALRasterBandH band = NULL
    cdef GDALRasterBandH hmask = NULL
    cdef void *buf = NULL
    cdef int bufxsize = data.shape[2]
    cdef int bufysize = data.shape[1]
    cdef int buftype = dtypes.dtype_rev[data.dtype.name]
    cdef int bufpixelspace = data.strides[2]
    cdef int buflinespace = data.strides[1]
    cdef int count = len(indexes)

    cdef int xoff = <int>x0
    cdef int yoff = <int>y0
    cdef int xsize = <int>width
    cdef int ysize = <int>height

    for i in range(count):
        j = indexes[i]
        band = GDALGetRasterBand(hds, j)
        if band == NULL:
            raise ValueError("Null band")
        hmask = GDALGetMaskBand(band)
        if hmask == NULL:
            raise ValueError("Null mask band")
        buf = <void *>np.PyArray_DATA(data[i])
        if buf == NULL:
            raise ValueError("NULL data")
        with nogil:
            retval = GDALRasterIO(
                hmask, mode, xoff, yoff, xsize, ysize, buf, bufxsize,
                bufysize, 1, bufpixelspace, buflinespace)
            if retval:
                break

    return retval
