# cython: boundscheck=False

import logging
import math
import os
import os.path
import sys
import warnings

from libc.stdlib cimport malloc, free
import numpy as np
cimport numpy as np

from rasterio cimport _base, _gdal, _ogr, _io
from rasterio._base import eval_window, window_shape, window_index, tastes_like_gdal
from rasterio._drivers import driver_count, GDALEnv
from rasterio._err import cpl_errs
from rasterio import dtypes
from rasterio.coords import BoundingBox
from rasterio.five import text_type, string_types
from rasterio.transform import Affine
from rasterio.enums import ColorInterp

log = logging.getLogger('rasterio')
if 'all' in sys.warnoptions:
    # show messages in console with: python -W all
    logging.basicConfig()
else:
    # no handler messages shown
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

    log.addHandler(NullHandler())

# Single band IO functions.

cdef int io_ubyte(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.uint8_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 1, 0, 0)

cdef int io_uint16(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.uint16_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 2, 0, 0)

cdef int io_int16(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.int16_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 3, 0, 0)

cdef int io_uint32(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.uint32_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 4, 0, 0)

cdef int io_int32(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.int32_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 5, 0, 0)

cdef int io_float32(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.float32_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 6, 0, 0)

cdef int io_float64(
        void *hband,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.float64_t[:, :] buffer):
    with nogil:
        return _gdal.GDALRasterIO(
            hband, mode, xoff, yoff, width, height,
            &buffer[0, 0], buffer.shape[1], buffer.shape[0], 7, 0, 0)

# The multi-band IO functions.

cdef int io_multi_ubyte(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.uint8_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buffer[0, 0, 0], buffer.shape[2], buffer.shape[1], 
                        1, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval

cdef int io_multi_uint16(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.uint16_t[:, :, :] buf,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf[0, 0, 0], buf.shape[2], buf.shape[1], 
                        2, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval

cdef int io_multi_int16(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.int16_t[:, :, :] buf,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf[0, 0, 0], buf.shape[2], buf.shape[1], 
                        3, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval

cdef int io_multi_uint32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.uint32_t[:, :, :] buf,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf[0, 0, 0], buf.shape[2], buf.shape[1], 
                        4, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval

cdef int io_multi_int32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.int32_t[:, :, :] buf,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf[0, 0, 0], buf.shape[2], buf.shape[1], 
                        5, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval


cdef int io_multi_float32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.float32_t[:, :, :] buf,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf[0, 0, 0], buf.shape[2], buf.shape[1], 
                        6, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval

cdef int io_multi_float64(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.float64_t[:, :, :] buf,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    cdef int *bandmap
    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf[0, 0, 0], buf.shape[2], buf.shape[1], 
                        7, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)
    return retval

cdef int io_multi_cint16(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.complex_t[:, :, :] out,
        long[:] indexes,
        int count):
    
    cdef int retval=0
    cdef int *bandmap
    cdef int I, J, K
    cdef int i, j, k
    cdef np.int16_t real, imag

    buf = np.empty(
            (out.shape[0], 2*out.shape[2]*out.shape[1]), 
            dtype=np.int16)
    cdef np.int16_t[:, :] buf_view = buf

    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf_view[0, 0], out.shape[2], out.shape[1],
                        8, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)

        if retval > 0:
            return retval

        I = out.shape[0]
        J = out.shape[1]
        K = out.shape[2]
        for i in range(I):
            for j in range(J):
                for k in range(K):
                    real = buf_view[i, 2*(j*K+k)]
                    imag = buf_view[i, 2*(j*K+k)+1]
                    out[i,j,k].real = real
                    out[i,j,k].imag = imag

    return retval

cdef int io_multi_cint32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.complex_t[:, :, :] out,
        long[:] indexes,
        int count):
    
    cdef int retval=0
    cdef int *bandmap
    cdef int I, J, K
    cdef int i, j, k
    cdef np.int32_t real, imag

    buf = np.empty(
            (out.shape[0], 2*out.shape[2]*out.shape[1]), 
            dtype=np.int32)
    cdef np.int32_t[:, :] buf_view = buf

    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf_view[0, 0], out.shape[2], out.shape[1],
                        9, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)

        if retval > 0:
            return retval

        I = out.shape[0]
        J = out.shape[1]
        K = out.shape[2]
        for i in range(I):
            for j in range(J):
                for k in range(K):
                    real = buf_view[i, 2*(j*K+k)]
                    imag = buf_view[i, 2*(j*K+k)+1]
                    out[i,j,k].real = real
                    out[i,j,k].imag = imag

    return retval

cdef int io_multi_cfloat32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.complex64_t[:, :, :] out,
        long[:] indexes,
        int count):
    
    cdef int retval=0
    cdef int *bandmap
    cdef int I, J, K
    cdef int i, j, k
    cdef np.float32_t real, imag

    buf = np.empty(
            (out.shape[0], 2*out.shape[2]*out.shape[1]), 
            dtype=np.float32)
    cdef np.float32_t[:, :] buf_view = buf

    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf_view[0, 0], out.shape[2], out.shape[1],
                        10, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)

        if retval > 0:
            return retval

        I = out.shape[0]
        J = out.shape[1]
        K = out.shape[2]
        for i in range(I):
            for j in range(J):
                for k in range(K):
                    real = buf_view[i, 2*(j*K+k)]
                    imag = buf_view[i, 2*(j*K+k)+1]
                    out[i,j,k].real = real
                    out[i,j,k].imag = imag

    return retval

cdef int io_multi_cfloat64(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.complex128_t[:, :, :] out,
        long[:] indexes,
        int count):
    
    cdef int retval=0
    cdef int *bandmap
    cdef int I, J, K
    cdef int i, j, k
    cdef np.float64_t real, imag

    buf = np.empty(
            (out.shape[0], 2*out.shape[2]*out.shape[1]), 
            dtype=np.float64)
    cdef np.float64_t[:, :] buf_view = buf

    with nogil:
        bandmap = <int *>_gdal.CPLMalloc(count*sizeof(int))
        for i in range(count):
            bandmap[i] = indexes[i]
        retval = _gdal.GDALDatasetRasterIO(
                        hds, mode, xoff, yoff, width, height,
                        &buf_view[0, 0], out.shape[2], out.shape[1],
                        11, count, bandmap, 0, 0, 0)
        _gdal.CPLFree(bandmap)

        if retval > 0:
            return retval

        I = out.shape[0]
        J = out.shape[1]
        K = out.shape[2]
        for i in range(I):
            for j in range(J):
                for k in range(K):
                    real = buf_view[i, 2*(j*K+k)]
                    imag = buf_view[i, 2*(j*K+k)+1]
                    out[i,j,k].real = real
                    out[i,j,k].imag = imag

    return retval


cdef int io_auto(image, void *hband, bint write):
    """
    Convenience function to handle IO with a GDAL band and a 2D numpy image

    :param image: a numpy 2D image
    :param hband: an instance of GDALGetRasterBand
    :param write: 1 (True) uses write mode, 0 (False) uses read
    :return: the return value from the data-type specific IO function
    """

    if not len(image.shape) == 2:
        raise ValueError("Specified image must have 2 dimensions")

    cdef int width = image.shape[1]
    cdef int height = image.shape[0]

    dtype_name = image.dtype.name

    if dtype_name == "float32":
        return io_float32(hband, write, 0, 0, width, height, image)
    elif dtype_name == "float64":
        return io_float64(hband, write, 0, 0, width, height, image)
    elif dtype_name == "uint8":
        return io_ubyte(hband, write, 0, 0, width, height, image)
    elif dtype_name == "int16":
        return io_int16(hband, write, 0, 0, width, height, image)
    elif dtype_name == "int32":
        return io_int32(hband, write, 0, 0, width, height, image)
    elif dtype_name == "uint16":
        return io_uint16(hband, write, 0, 0, width, height, image)
    elif dtype_name == "uint32":
        return io_uint32(hband, write, 0, 0, width, height, image)
    else:
        raise ValueError("Image dtype is not supported for this function."
                         "Must be float32, float64, int16, int32, uint8, "
                         "uint16, or uint32")


cdef class RasterReader(_base.DatasetReader):

    def read_band(self, bidx, out=None, window=None, masked=None):
        """Read the `bidx` band into an `out` array if provided, 
        otherwise return a new array.

        Band indexes begin with 1: read_band(1) returns the first band.

        The optional `window` argument is a 2 item tuple. The first item
        is a tuple containing the indexes of the rows at which the
        window starts and stops and the second is a tuple containing the
        indexes of the columns at which the window starts and stops. For
        example, ((0, 2), (0, 2)) defines a 2x2 window at the upper left
        of the raster dataset.
        """
        return self.read(bidx, out=out, window=window, masked=masked)

    def read(self, indexes=None, out=None, window=None, masked=None):
        """Read raster bands as a multidimensional array

        If `indexes` is a list, the result is a 3D array, but
        is a 2D array if it is a band index number.

        Optional `out` argument is a reference to an output array with the
        same dimensions and shape.

        See `read_band` for usage of the optional `window` argument.

        The return type will be either a regular NumPy array, or a masked
        NumPy array depending on the `masked` argument. The return type is
        forced if either `True` or `False`, but will be chosen if `None`.
        For `masked=None` (default), the array will be the same type as
        `out` (if used), or will be masked if any of the nodatavals are
        not `None`.
        """
        cdef int height, width, xoff, yoff, aix, bidx, indexes_count
        cdef int retval = 0
        return2d = False

        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
        if indexes is None:  # Default: read all bands
            indexes = self.indexes
        elif isinstance(indexes, int):
            indexes = [indexes]
            return2d = True
            if out is not None and out.ndim == 2:
                out.shape = (1,) + out.shape
        if not indexes:
            raise ValueError("No indexes to read")
        check_dtypes = set()
        nodatavals = []
        # Check each index before processing 3D array
        for bidx in indexes:
            if bidx not in self.indexes:
                raise IndexError("band index out of range")
            idx = self.indexes.index(bidx)
            check_dtypes.add(self.dtypes[idx])
            nodatavals.append(self.nodatavals[idx])
        if len(check_dtypes) > 1:
            raise ValueError("more than one 'dtype' found")
        elif len(check_dtypes) == 0:
            dtype = self.dtypes[0]
        else:  # unique dtype; normal case
            dtype = check_dtypes.pop()
        out_shape = (len(indexes),) + (
            window
            and window_shape(window, self.height, self.width)
            or self.shape)
        if out is not None:
            if out.dtype != dtype:
                raise ValueError(
                    "the array's dtype '%s' does not match "
                    "the file's dtype '%s'" % (out.dtype, dtype))
            if out.shape[0] != out_shape[0]:
                raise ValueError(
                    "'out' shape %s does not mach raster slice shape %s" %
                    (out.shape, out_shape))
            if masked is None:
                masked = hasattr(out, 'mask')
        if masked is None:
            masked = any([x is not None for x in nodatavals])
        if out is None:
            if masked:
                out = np.ma.empty(out_shape, dtype)
            else:
                out = np.empty(out_shape, dtype)

        # Prepare the IO window.
        if window:
            window = eval_window(window, self.height, self.width)
            yoff = <int>window[0][0]
            xoff = <int>window[1][0]
            height = <int>window[0][1] - yoff
            width = <int>window[1][1] - xoff
        else:
            xoff = yoff = <int>0
            width = <int>self.width
            height = <int>self.height

        # Call io_multi* functions with C type args so that they
        # can release the GIL.
        indexes_arr = np.array(indexes, dtype=int)
        indexes_count = <int>indexes_arr.shape[0]
        gdt = dtypes.dtype_rev[dtype]

        if gdt == 1:
            retval = io_multi_ubyte(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 2:
            retval = io_multi_uint16(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 3:
            retval = io_multi_int16(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 4:
            retval = io_multi_uint32(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 5:
            retval = io_multi_int32(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 6:
            retval = io_multi_float32(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 7:
            retval = io_multi_float64(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 8:
            retval = io_multi_cint16(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 9:
            retval = io_multi_cint32(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 10:
            retval = io_multi_cfloat32(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 11:
            retval = io_multi_cfloat64(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)

        if retval in (1, 2, 3):
            raise IOError("Read or write failed")
        elif retval == 4:
            raise ValueError("NULL band")

        # Masking the output. TODO: explain the logic better.
        if masked:
            test1nodata = set(nodatavals)
            if len(test1nodata) == 1:
                if nodatavals[0] is None:
                    out = np.ma.masked_array(out, copy=False)
                elif np.isnan(nodatavals[0]):
                    out = np.ma.masked_where(np.isnan(out), out, copy=False)
                else:
                    out = np.ma.masked_equal(out, nodatavals[0], copy=False)
            else:
                out = np.ma.masked_array(out, copy=False)
                for aix in range(len(indexes)):
                    if nodatavals[aix] is None:
                        band_mask = False
                    elif np.isnan(nodatavals[aix]):
                        band_mask = np.isnan(out[aix])
                    else:
                        band_mask = out[aix] == nodatavals[aix]
                    out[aix].mask = band_mask
        
        if return2d:
            out.shape = out.shape[1:]
        return out

    def read_mask(self, out=None, window=None):
        """Read the mask band into an `out` array if provided, 
        otherwise return a new array containing the dataset's
        valid data mask.

        The optional `window` argument takes a tuple like:
        
            ((row_start, row_stop), (col_start, col_stop))
            
        specifying a raster subset to write into.
        """
        cdef void *hband
        cdef void *hmask
        if self._hds == NULL:
            raise ValueError("can't write closed raster file")
        hband = _gdal.GDALGetRasterBand(self._hds, 1)
        if hband == NULL:
            raise ValueError("NULL band mask")
        hmask = _gdal.GDALGetMaskBand(hband)
        if hmask == NULL:
            return None
        if out is None:
            out_shape = (
                window 
                and window_shape(window, self.height, self.width) 
                or self.shape)
            out = np.empty(out_shape, np.uint8)
        if window:
            window = eval_window(window, self.height, self.width)
            yoff = window[0][0]
            xoff = window[1][0]
            height = window[0][1] - yoff
            width = window[1][1] - xoff
        else:
            xoff = yoff = 0
            width = self.width
            height = self.height
        retval = io_ubyte(
            hmask, 0, xoff, yoff, width, height, out)
        return out


cdef class RasterUpdater(RasterReader):
    # Read-write access to raster data and metadata.
    # TODO: the r+ mode.

    def __init__(
            self, path, mode, driver=None,
            width=None, height=None, count=None, 
            crs=None, transform=None, dtype=None,
            nodata=None,
            **kwargs):
        # Validate write mode arguments.
        if mode == 'w':
            if not isinstance(driver, string_types):
                raise TypeError("A driver name string is required.")
            try:
                width = int(width)
                height = int(height)
            except:
                raise TypeError("Integer width and height are required.")
            try:
                count = int(count)
            except:
                raise TypeError("Integer band count is required.")
            try:
                assert dtype is not None
                _ = np.dtype(dtype)
            except:
                raise TypeError("A valid dtype is required.")
        self.name = path
        self.mode = mode
        self.driver = driver
        self.width = width
        self.height = height
        self._count = count
        self._init_dtype = np.dtype(dtype).name
        self._init_nodata = nodata
        self._hds = NULL
        self._count = count
        self._crs = crs
        if transform is not None:
            self._transform = transform.to_gdal()
        self._closed = True
        self._dtypes = []
        self._nodatavals = []
        self._options = kwargs.copy()
    
    def __repr__(self):
        return "<%s RasterUpdater name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open', 
            self.name,
            self.mode)

    def start(self):
        cdef const char *drv_name = NULL
        cdef char **options = NULL
        cdef char *key_c, *val_c = NULL
        cdef void *drv = NULL
        cdef void *hband = NULL
        cdef int success
        name_b = self.name.encode('utf-8')
        cdef const char *fname = name_b

        # Is there not a driver manager already?
        if driver_count() == 0 and not self.env:
            # create a local manager and enter
            self.env = GDALEnv(True)
        else:
            self.env = GDALEnv(False)
        self.env.start()
        
        kwds = []

        if self.mode == 'w':
            # GDAL can Create() GTiffs. Many other formats only support
            # CreateCopy(). Rasterio lets you write GTiffs *only* for now.
            if self.driver not in ['GTiff']:
                raise ValueError("only GTiffs can be opened in 'w' mode")

            # Delete existing file, create.
            if os.path.exists(self.name):
                os.unlink(self.name)
            
            driver_b = self.driver.encode('utf-8')
            drv_name = driver_b
            drv = _gdal.GDALGetDriverByName(drv_name)
            if drv == NULL:
                raise ValueError("NULL driver for %s", self.driver)
            
            # Find the equivalent GDAL data type or raise an exception
            # We've mapped numpy scalar types to GDAL types so see
            # if we can crosswalk those.
            if hasattr(self._init_dtype, 'type'):
                tp = self._init_dtype.type
                if tp not in dtypes.dtype_rev:
                    raise ValueError(
                        "Unsupported dtype: %s" % self._init_dtype)
                else:
                    gdal_dtype = dtypes.dtype_rev.get(tp)
            else:
                gdal_dtype = dtypes.dtype_rev.get(self._init_dtype)

            # Creation options
            for k, v in self._options.items():
                # Skip items that are definitely *not* valid driver options.
                if k.lower() in ['affine']:
                    continue
                kwds.append((k.lower(), v))
                k, v = k.upper(), str(v).upper()
                key_b = k.encode('utf-8')
                val_b = v.encode('utf-8')
                key_c = key_b
                val_c = val_b
                options = _gdal.CSLSetNameValue(options, key_c, val_c)
                log.debug(
                    "Option: %r\n", 
                    (k, _gdal.CSLFetchNameValue(options, key_c)))

            self._hds = _gdal.GDALCreate(
                drv, fname, self.width, self.height, self._count,
                gdal_dtype, options)
            if self._hds == NULL:
                raise ValueError("NULL dataset")

            if self._init_nodata is not None:
                for i in range(self._count):
                    hband = _gdal.GDALGetRasterBand(self._hds, i+1)
                    success = _gdal.GDALSetRasterNoDataValue(
                                    hband, self._init_nodata)

            if self._transform:
                self.write_transform(self._transform)
            if self._crs:
                self.set_crs(self._crs)
        
        elif self.mode == 'r+':
            with cpl_errs:
                self._hds = _gdal.GDALOpen(fname, 1)
            if self._hds == NULL:
                raise ValueError("NULL dataset")

        drv = _gdal.GDALGetDatasetDriver(self._hds)
        drv_name = _gdal.GDALGetDriverShortName(drv)
        self.driver = drv_name.decode('utf-8')

        self._count = _gdal.GDALGetRasterCount(self._hds)
        self.width = _gdal.GDALGetRasterXSize(self._hds)
        self.height = _gdal.GDALGetRasterYSize(self._hds)
        self.shape = (self.height, self.width)

        self._transform = self.read_transform()
        self._crs = self.read_crs()
        self._crs_wkt = self.read_crs_wkt()

        if options != NULL:
            _gdal.CSLDestroy(options)
        
        # touch self.meta
        _ = self.meta

        self.update_tags(ns='rio_creation_kwds', **kwds)
        self._closed = False

    def set_crs(self, crs):
        """Writes a coordinate reference system to the dataset."""
        cdef char *proj_c = NULL
        cdef char *wkt = NULL
        if self._hds == NULL:
            raise ValueError("Can't read closed raster file")
        cdef void *osr = _gdal.OSRNewSpatialReference(NULL)
        if osr == NULL:
            raise ValueError("Null spatial reference")
        params = []

        log.debug("Input CRS: %r", crs)

        # Normally, we expect a CRS dict.
        if isinstance(crs, dict):
            # EPSG is a special case.
            init = crs.get('init')
            if init:
                auth, val = init.split(':')
                if auth.upper() == 'EPSG':
                    _gdal.OSRImportFromEPSG(osr, int(val))
            else:
                crs['wktext'] = True
                for k, v in crs.items():
                    if v is True or (k in ('no_defs', 'wktext') and v):
                        params.append("+%s" % k)
                    else:
                        params.append("+%s=%s" % (k, v))
                proj = " ".join(params)
                log.debug("PROJ.4 to be imported: %r", proj)
                proj_b = proj.encode('utf-8')
                proj_c = proj_b
                _gdal.OSRImportFromProj4(osr, proj_c)
        # Fall back for CRS strings like "EPSG:3857."
        else:
            proj_b = crs.encode('utf-8')
            proj_c = proj_b
            _gdal.OSRSetFromUserInput(osr, proj_c)

        # Fixup, export to WKT, and set the GDAL dataset's projection.
        _gdal.OSRFixup(osr)
        _gdal.OSRExportToWkt(osr, &wkt)
        wkt_b = wkt
        log.debug("Exported WKT: %s", wkt_b.decode('utf-8'))
        _gdal.GDALSetProjection(self._hds, wkt)

        _gdal.CPLFree(wkt)
        _gdal.OSRDestroySpatialReference(osr)
        self._crs = crs
        log.debug("Self CRS: %r", self._crs)

    property crs:
        """A mapping of PROJ.4 coordinate reference system params.
        """

        def __get__(self):
            return self.get_crs()

        def __set__(self, value):
            self.set_crs(value)

    def write_transform(self, transform):
        if self._hds == NULL:
            raise ValueError("Can't read closed raster file")
        cdef double gt[6]
        for i in range(6):
            gt[i] = transform[i]
        retval = _gdal.GDALSetGeoTransform(self._hds, gt)
        self._transform = transform

    property transform:
        """An affine transformation that maps pixel row/column
        coordinates to coordinates in the specified crs. The affine
        transformation is represented by a six-element sequence.
        Reference system coordinates can be calculated by the
        following formula

        X = Item 0 + Column * Item 1 + Row * Item 2
        Y = Item 3 + Column * Item 4 + Row * Item 5

        See also this class's ul() method.
        """

        def __get__(self):
            return Affine.from_gdal(*self.get_transform())

        def __set__(self, value):
            self.write_transform(value.to_gdal())

    def write(self, src, indexes=None, window=None):
        """Write the src array into indexed bands of the dataset.

        If `indexes` is a list, the src must be a 3D array of
        matching shape. If an int, the src must be a 2D array.

        See `read()` for usage of the optional `window` argument.
        """
        cdef int height, width, xoff, yoff, indexes_count
        cdef int retval = 0

        if self._hds == NULL:
            raise ValueError("can't write to closed raster file")

        if indexes is None:
            indexes = self.indexes
        elif isinstance(indexes, int):
            indexes = [indexes]
            src = np.array([src])
        if len(src.shape) != 3 or src.shape[0] != len(indexes):
            raise ValueError(
                "Source shape is inconsistent with given indexes")

        check_dtypes = set()
        # Check each index before processing 3D array
        for bidx in indexes:
            if bidx not in self.indexes:
                raise IndexError("band index out of range")
            idx = self.indexes.index(bidx)
            check_dtypes.add(self.dtypes[idx])
        if len(check_dtypes) > 1:
            raise ValueError("more than one 'dtype' found")
        elif len(check_dtypes) == 0:
            dtype = self.dtypes[0]
        else:  # unique dtype; normal case
            dtype = check_dtypes.pop()

        if src is not None and src.dtype != dtype:
            raise ValueError(
                "the array's dtype '%s' does not match "
                "the file's dtype '%s'" % (src.dtype, dtype))

        # Require C-continguous arrays (see #108).
        src = np.require(src, dtype=dtype, requirements='C')

        # Prepare the IO window.
        if window:
            window = eval_window(window, self.height, self.width)
            yoff = <int>window[0][0]
            xoff = <int>window[1][0]
            height = <int>window[0][1] - yoff
            width = <int>window[1][1] - xoff
        else:
            xoff = yoff = <int>0
            width = <int>self.width
            height = <int>self.height

        # Call io_multi* functions with C type args so that they
        # can release the GIL.
        indexes_arr = np.array(indexes, dtype=int)
        indexes_count = <int>indexes_arr.shape[0]
        gdt = dtypes.dtype_rev[dtype]
        if gdt == 1:
            retval = io_multi_ubyte(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 2:
            retval = io_multi_uint16(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 3:
            retval = io_multi_int16(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 4:
            retval = io_multi_uint32(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 5:
            retval = io_multi_int32(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 6:
            retval = io_multi_float32(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 7:
            retval = io_multi_float64(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 8:
            retval = io_multi_cint16(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 9:
            retval = io_multi_cint32(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 10:
            retval = io_multi_cfloat32(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)
        elif gdt == 11:
            retval = io_multi_cfloat64(
                            self._hds, 1, xoff, yoff, width, height,
                            src, indexes_arr, indexes_count)

        if retval in (1, 2, 3):
            raise IOError("Read or write failed")
        elif retval == 4:
            raise ValueError("NULL band")

    def write_band(self, bidx, src, window=None):
        """Write the src array into the `bidx` band.

        Band indexes begin with 1: read_band(1) returns the first band.

        The optional `window` argument takes a tuple like:

            ((row_start, row_stop), (col_start, col_stop))

        specifying a raster subset to write into.
        """
        self.write(src, bidx, window=window)

    def update_tags(self, bidx=0, ns=None, **kwargs):
        """Updates the tags of a dataset or one of its bands.

        Tags are pairs of key and value strings. Tags belong to
        namespaces.  The standard namespaces are: default (None) and
        'IMAGE_STRUCTURE'.  Applications can create their own additional
        namespaces.

        The optional bidx argument can be used to select the dataset
        band. The optional ns argument can be used to select a namespace
        other than the default.
        """
        cdef char *key_c = NULL
        cdef char *value_c = NULL
        cdef void *hobj = NULL
        cdef const char *domain_c = NULL
        cdef char **papszStrList = NULL
        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
        if bidx > 0:
            if bidx not in self.indexes:
                raise ValueError("Invalid band index")
            hobj = _gdal.GDALGetRasterBand(self._hds, bidx)
            if hobj == NULL:
                raise ValueError("NULL band")
        else:
            hobj = self._hds
        if ns:
            domain_b = ns.encode('utf-8')
            domain_c = domain_b
        else:
            domain_c = NULL
        
        papszStrList = _gdal.CSLDuplicate(
            _gdal.GDALGetMetadata(hobj, domain_c))

        for key, value in kwargs.items():
            key_b = text_type(key).encode('utf-8')
            value_b = text_type(value).encode('utf-8')
            key_c = key_b
            value_c = value_b
            papszStrList = _gdal.CSLSetNameValue(
                    papszStrList, key_c, value_c)

        retval = _gdal.GDALSetMetadata(hobj, papszStrList, domain_c)
        if papszStrList != NULL:
            _gdal.CSLDestroy(papszStrList)

        if retval == 2:
            log.warn("Tags accepted but may not be persisted.")
        elif retval == 3:
            raise RuntimeError("Tag update failed.")

    def write_colormap(self, bidx, colormap):
        """Write a colormap for a band to the dataset."""
        cdef void *hBand
        cdef void *hTable
        cdef _gdal.GDALColorEntry color
        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
        if bidx > 0:
            if bidx not in self.indexes:
                raise ValueError("Invalid band index")
            hBand = _gdal.GDALGetRasterBand(self._hds, bidx)
            if hBand == NULL:
                raise ValueError("NULL band")
        # RGB only for now. TODO: the other types.
        # GPI_Gray=0,  GPI_RGB=1, GPI_CMYK=2,     GPI_HLS=3
        hTable = _gdal.GDALCreateColorTable(1)
        vals = range(256)
        for i, rgba in colormap.items():
            if i not in vals:
                log.warn("Invalid colormap key %d", i)
                continue
            color.c1, color.c2, color.c3, color.c4 = rgba
            _gdal.GDALSetColorEntry(hTable, i, &color)
        # TODO: other color interpretations?
        _gdal.GDALSetRasterColorInterpretation(hBand, 2)
        _gdal.GDALSetRasterColorTable(hBand, hTable)
        _gdal.GDALDestroyColorTable(hTable)

    def write_mask(self, src, window=None):
        """Write the valid data mask src array into the dataset's band
        mask.

        The optional `window` argument takes a tuple like:
        
            ((row_start, row_stop), (col_start, col_stop))
            
        specifying a raster subset to write into.
        """
        cdef void *hband
        cdef void *hmask
        if self._hds == NULL:
            raise ValueError("can't write closed raster file")
        hband = _gdal.GDALGetRasterBand(self._hds, 1)
        if hband == NULL:
            raise ValueError("NULL band mask")
        if _gdal.GDALCreateMaskBand(hband, 0x02) != 0:
            raise RuntimeError("Failed to create mask")
        hmask = _gdal.GDALGetMaskBand(hband)
        if hmask == NULL:
            raise ValueError("NULL band mask")
        log.debug("Created mask band")
        if window:
            window = eval_window(window, self.height, self.width)
            yoff = window[0][0]
            xoff = window[1][0]
            height = window[0][1] - yoff
            width = window[1][1] - xoff
        else:
            xoff = yoff = 0
            width = self.width
            height = self.height
        if src.dtype == np.bool:
            array = 255 * src.astype(np.uint8)
            retval = io_ubyte(
                hmask, 1, xoff, yoff, width, height, array)
        else:
            retval = io_ubyte(
                hmask, 1, xoff, yoff, width, height, src)


cdef class InMemoryRaster:
    """
    Class that manages a single-band in memory GDAL raster dataset.  Data type
    is determined from the data type of the input numpy 2D array (image), and
    must be one of the data types supported by GDAL
    (see rasterio.dtypes.dtype_rev).  Data are populated at create time from
    the 2D array passed in.

    Use the 'with' pattern to instantiate this class for automatic closing
    of the memory dataset.

    This class includes attributes that are intended to be passed into GDAL
    functions:
    self.dataset
    self.band
    self.band_ids  (single element array with band ID of this dataset's band)
    self.transform (GDAL compatible transform array)

    This class is only intended for internal use within rasterio to support
    IO with GDAL.  Other memory based operations should use numpy arrays.
    """

    def __init__(self, image, transform):
        """
        Create in-memory raster dataset, and populate its initial values with
        the values in image.

        :param image: 2D numpy array.  Must be of supported data type
        (see rasterio.dtypes.dtype_rev)
        :param transform: GDAL compatible transform array
        """

        self._image = image
        self.dataset = NULL

        cdef void *memdriver = _gdal.GDALGetDriverByName("MEM")

        # Several GDAL operations require the array of band IDs as input
        self.band_ids[0] = 1

        self.dataset = _gdal.GDALCreate(
            memdriver,
            "output",
            image.shape[1],
            image.shape[0],
            1,
            <_gdal.GDALDataType>dtypes.dtype_rev[image.dtype.name],
            NULL
        )

        if self.dataset == NULL:
            raise ValueError("NULL output datasource")

        for i in range(6):
            self.transform[i] = transform[i]
        err = _gdal.GDALSetGeoTransform(self.dataset, self.transform)
        if err:
            raise ValueError("transform not set: %s" % transform)

        self.band = _gdal.GDALGetRasterBand(self.dataset, 1)
        if self.band == NULL:
            raise ValueError("NULL output band: {0}".format(i))

        self.write(image)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def close(self):
        if self.dataset != NULL:
            _gdal.GDALClose(self.dataset)

    def read(self):
        io_auto(self._image, self.band, False)
        return self._image

    def write(self, image):
        io_auto(image, self.band, True)
