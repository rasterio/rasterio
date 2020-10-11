"""Rasterio shim for GDAL 1.x"""
# cython: boundscheck=False

# The baseline GDAL API.
include "gdal.pxi"

import os
from rasterio import dtypes

cimport numpy as np
from rasterio._err cimport exc_wrap_int, exc_wrap_pointer


IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (2, 0):
    include "shim_rasterioex.pxi"

    cdef extern from "gdal.h" nogil:

        GDALDatasetH GDALOpenEx(const char *filename, int flags, const char **allowed_drivers, const char **options, const char **siblings) # except -1


IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (2, 1):
    cdef extern from "gdal.h" nogil:

        cdef CPLErr GDALDeleteRasterNoDataValue(GDALRasterBandH hBand)


IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 0):
    cdef extern from "ogr_srs_api.h" nogil:

        ctypedef enum OSRAxisMappingStrategy:
            OAMS_TRADITIONAL_GIS_ORDER

        const char* OSRGetName(OGRSpatialReferenceH hSRS)
        void OSRSetAxisMappingStrategy(OGRSpatialReferenceH hSRS, OSRAxisMappingStrategy)
        void OSRSetPROJSearchPaths(const char *const *papszPaths)


cdef GDALDatasetH open_dataset(
        object filename, int flags, object allowed_drivers,
        object open_options, object siblings) except NULL:
    """Open a dataset and return a handle"""

    cdef GDALDatasetH hds = NULL
    cdef const char *fname = NULL

    filename = filename.encode('utf-8')
    fname = filename

    IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (2, 0):
        cdef char **drivers = NULL
        cdef char **options = NULL
        # Construct a null terminated C list of driver
        # names for GDALOpenEx.
        if allowed_drivers:
            for name in allowed_drivers:
                name = name.encode('utf-8')
                drivers = CSLAddString(drivers, <const char *>name)

        if open_options:
            for k, v in open_options.items():
                k = k.upper().encode('utf-8')

                # Normalize values consistent with code in _env module.
                if isinstance(v, bool):
                    v = ('ON' if v else 'OFF').encode('utf-8')
                else:
                    v = str(v).encode('utf-8')

                options = CSLAddNameValue(options, <const char *>k, <const char *>v)

        # Support for sibling files is not yet implemented.
        if siblings:
            raise NotImplementedError(
                "Sibling files are not implemented")

        # Ensure raster flags
        flags = flags | 0x02

        with nogil:
            hds = GDALOpenEx(fname, flags, drivers, options, NULL)
        try:
            return exc_wrap_pointer(hds)
        finally:
                CSLDestroy(drivers)
                CSLDestroy(options)
    ELSE:
        if flags & 0x20:
            with nogil:
                hds = GDALOpenShared(fname, <GDALAccess>(flags & 0x01))
        else:
            with nogil:
                hds = GDALOpen(fname, <GDALAccess>(flags & 0x01))
        return exc_wrap_pointer(hds)


cdef int delete_nodata_value(GDALRasterBandH hBand) except 3:
    IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) < (2, 1):
        raise NotImplementedError(
            "GDAL versions < 2.1 do not support nodata deletion")
    ELSE:
        return GDALDeleteRasterNoDataValue(hBand)


IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) < (2, 0):
    cdef int io_band(
            GDALRasterBandH band, int mode, double x0, double y0,
            double width, double height, object data, int resampling=0) except -1:
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

        return exc_wrap_int(retval)


    cdef int io_multi_band(
            GDALDatasetH hds, int mode, double x0, double y0, double width,
            double height, object data, Py_ssize_t[:] indexes, int resampling=0) except -1:
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

        bandmap = <int *>CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = <int>indexes[i]

        try:
            with nogil:
                retval = GDALDatasetRasterIO(
                    hds, mode, xoff, yoff, xsize, ysize, buf,
                    bufxsize, bufysize, buftype, count, bandmap,
                    bufpixelspace, buflinespace, bufbandspace)

            return exc_wrap_int(retval)

        finally:
            CPLFree(bandmap)


    cdef int io_multi_mask(
            GDALDatasetH hds, int mode, double x0, double y0, double width,
            double height, object data, Py_ssize_t[:] indexes, int resampling=0) except -1:
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
                retval = GDALRasterIO(
                    hmask, mode, xoff, yoff, xsize, ysize, buf, bufxsize,
                    bufysize, 1, bufpixelspace, buflinespace)
                if retval:
                    break

        return exc_wrap_int(retval)


cdef const char* osr_get_name(OGRSpatialReferenceH hSrs):
    IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 0):
        return OSRGetName(hSrs)
    ELSE:
        return ''


cdef void osr_set_traditional_axis_mapping_strategy(OGRSpatialReferenceH hSrs):
    IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 0):
        OSRSetAxisMappingStrategy(hSrs, OAMS_TRADITIONAL_GIS_ORDER)
    ELSE:
        pass


cdef void set_proj_search_path(object path):
    IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 0):
        cdef char **paths = NULL
        cdef const char *path_c = NULL
        path_b = path.encode("utf-8")
        path_c = path_b
        paths = CSLAddString(paths, path_c)
        OSRSetPROJSearchPaths(paths)
    ELSE:
        os.environ["PROJ_LIB"] = path
