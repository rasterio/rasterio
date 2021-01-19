# Declarations and implementations shared between the GDAL 2.0 and 2.1
# shim APIs in _shim20.pyx and _shim21.pyx.

from rasterio import dtypes
from rasterio.enums import Resampling
from rasterio.env import GDALVersion
from rasterio.errors import ResamplingAlgorithmError

cimport numpy as np

from rasterio._err cimport exc_wrap_int


cdef extern from "cpl_progress.h":

    ctypedef int (*GDALProgressFunc)(double dfComplete, const char *pszMessage, void *pProgressArg)


cdef extern from "gdal.h" nogil:

    ctypedef struct GDALRasterIOExtraArg:
        int nVersion
        GDALRIOResampleAlg eResampleAlg
        GDALProgressFunc pfnProgress
        void *pProgressData
        int bFloatingPointWindowValidity
        double dfXOff
        double dfYOff
        double dfXSize
        double dfYSize

    cdef CPLErr GDALRasterIOEx(GDALRasterBandH hRBand, GDALRWFlag eRWFlag, int nDSXOff, int nDSYOff, int nDSXSize, int nDSYSize, void *pBuffer, int nBXSize, int nBYSize, GDALDataType eBDataType, GSpacing nPixelSpace, GSpacing nLineSpace, GDALRasterIOExtraArg *psExtraArg)

    cdef CPLErr GDALDatasetRasterIOEx(GDALDatasetH hDS, GDALRWFlag eRWFlag, int nDSXOff, int nDSYOff, int nDSXSize, int nDSYSize, void *pBuffer, int nBXSize, int nBYSize, GDALDataType eBDataType, int nBandCount, int *panBandCount, GSpacing nPixelSpace, GSpacing nLineSpace, GSpacing nBandSpace, GDALRasterIOExtraArg *psExtraArg)


gdal31_version_checked = False
gdal31_version_met = False
gdal33_version_checked = False
gdal33_version_met = False

def validate_resampling(resampling):
    """Validate that the resampling method is compatible of reads/writes"""

    if resampling == Resampling.sum:
        global gdal31_version_checked
        global gdal31_version_met
        if not gdal31_version_checked:
            gdal31_version_checked = True
            gdal31_version_met = GDALVersion.runtime().at_least('3.1')
        if not gdal31_version_met:
            raise ResamplingAlgorithmError("{!r} requires GDAL 3.1".format(Resampling(resampling)))
    elif resampling == Resampling.rms:
        global gdal33_version_checked
        global gdal33_version_met
        if not gdal33_version_checked:
            gdal33_version_checked = True
            gdal33_version_met = GDALVersion.runtime().at_least('3.3')
        if not gdal33_version_met:
            raise ResamplingAlgorithmError("{!r} requires GDAL 3.3".format(Resampling(resampling)))
    elif resampling > 7:
        raise ResamplingAlgorithmError("{!r} can be used for warp operations but not for reads and writes".format(Resampling(resampling)))


cdef int io_band(GDALRasterBandH band, int mode, double x0, double y0,
                 double width, double height, object data, int resampling=0) except -1:
    """Read or write a region of data for the band.

    Implicit are

    1) data type conversion if the dtype of `data` and `band` differ.
    2) decimation if `data` and `band` shapes differ.

    The striding of `data` is passed to GDAL so that it can navigate
    the layout of ndarray views.

    """
    validate_resampling(resampling)

    # GDAL handles all the buffering indexing, so a typed memoryview,
    # as in previous versions, isn't needed.
    cdef void *buf = <void *>np.PyArray_DATA(data)
    cdef int bufxsize = data.shape[1]
    cdef int bufysize = data.shape[0]
    cdef GDALDataType buftype = dtypes.dtype_rev[data.dtype.name]
    cdef GSpacing bufpixelspace = data.strides[1]
    cdef GSpacing buflinespace = data.strides[0]

    cdef int xoff = <int>x0
    cdef int yoff = <int>y0
    cdef int xsize = <int>width
    cdef int ysize = <int>height
    cdef int retval = 3

    cdef GDALRasterIOExtraArg extras
    extras.nVersion = 1
    extras.eResampleAlg = <GDALRIOResampleAlg>resampling
    extras.bFloatingPointWindowValidity = 1
    extras.dfXOff = x0
    extras.dfYOff = y0
    extras.dfXSize = width
    extras.dfYSize = height
    extras.pfnProgress = NULL
    extras.pProgressData = NULL

    with nogil:
        retval = GDALRasterIOEx(
            band, <GDALRWFlag>mode, xoff, yoff, xsize, ysize, buf, bufxsize, bufysize,
            buftype, bufpixelspace, buflinespace, &extras)

    return exc_wrap_int(retval)


cdef int io_multi_band(GDALDatasetH hds, int mode, double x0, double y0,
                       double width, double height, object data,
                       Py_ssize_t[:] indexes, int resampling=0) except -1:
    """Read or write a region of data for multiple bands.

    Implicit are

    1) data type conversion if the dtype of `data` and bands differ.
    2) decimation if `data` and band shapes differ.

    The striding of `data` is passed to GDAL so that it can navigate
    the layout of ndarray views.

    """
    validate_resampling(resampling)

    cdef int i = 0
    cdef int retval = 3
    cdef int *bandmap = NULL
    cdef void *buf = <void *>np.PyArray_DATA(data)
    cdef int bufxsize = data.shape[2]
    cdef int bufysize = data.shape[1]
    cdef GDALDataType buftype = dtypes.dtype_rev[data.dtype.name]
    cdef GSpacing bufpixelspace = data.strides[2]
    cdef GSpacing buflinespace = data.strides[1]
    cdef GSpacing bufbandspace = data.strides[0]
    cdef int count = len(indexes)

    cdef int xoff = <int>x0
    cdef int yoff = <int>y0
    cdef int xsize = <int>width
    cdef int ysize = <int>height

    cdef GDALRasterIOExtraArg extras
    extras.nVersion = 1
    extras.eResampleAlg = <GDALRIOResampleAlg>resampling
    extras.bFloatingPointWindowValidity = 1
    extras.dfXOff = x0
    extras.dfYOff = y0
    extras.dfXSize = width
    extras.dfYSize = height
    extras.pfnProgress = NULL
    extras.pProgressData = NULL

    bandmap = <int *>CPLMalloc(count*sizeof(int))
    for i in range(count):
        bandmap[i] = <int>indexes[i]

    try:
        with nogil:
            retval = GDALDatasetRasterIOEx(
                hds, <GDALRWFlag>mode, xoff, yoff, xsize, ysize, buf,
                bufxsize, bufysize, buftype, count, bandmap,
                bufpixelspace, buflinespace, bufbandspace, &extras)

        return exc_wrap_int(retval)

    finally:
        CPLFree(bandmap)


cdef int io_multi_mask(GDALDatasetH hds, int mode, double x0, double y0,
                       double width, double height, object data,
                       Py_ssize_t[:] indexes, int resampling=0) except -1:
    """Read or write a region of data for multiple band masks.

    Implicit are

    1) data type conversion if the dtype of `data` and bands differ.
    2) decimation if `data` and band shapes differ.

    The striding of `data` is passed to GDAL so that it can navigate
    the layout of ndarray views.

    """
    validate_resampling(resampling)

    cdef int i = 0
    cdef int j = 0
    cdef int retval = 3
    cdef GDALRasterBandH band = NULL
    cdef GDALRasterBandH hmask = NULL
    cdef void *buf = NULL
    cdef int bufxsize = data.shape[2]
    cdef int bufysize = data.shape[1]
    cdef GDALDataType buftype = dtypes.dtype_rev[data.dtype.name]
    cdef GSpacing bufpixelspace = data.strides[2]
    cdef GSpacing buflinespace = data.strides[1]
    cdef int count = len(indexes)

    cdef int xoff = <int>x0
    cdef int yoff = <int>y0
    cdef int xsize = <int>width
    cdef int ysize = <int>height

    cdef GDALRasterIOExtraArg extras
    extras.nVersion = 1
    extras.eResampleAlg = <GDALRIOResampleAlg>resampling
    extras.bFloatingPointWindowValidity = 1
    extras.dfXOff = x0
    extras.dfYOff = y0
    extras.dfXSize = width
    extras.dfYSize = height
    extras.pfnProgress = NULL
    extras.pProgressData = NULL

    for i in range(count):
        j = <int>indexes[i]
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
            retval = GDALRasterIOEx(
                hmask, <GDALRWFlag>mode, xoff, yoff, xsize, ysize, buf, bufxsize,
                bufysize, <GDALDataType>1, bufpixelspace, buflinespace, &extras)

            if retval:
                break

    return exc_wrap_int(retval)
