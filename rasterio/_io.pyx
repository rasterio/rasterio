# cython: boundscheck=False

from __future__ import absolute_import

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
from rasterio._base import (
    crop_window, eval_window, window_shape, window_index, tastes_like_gdal)
from rasterio._drivers import driver_count, GDALEnv
from rasterio._err import CPLErrors, GDALError, CPLE_OpenFailed
from rasterio import dtypes
from rasterio.coords import BoundingBox
from rasterio.errors import DriverRegistrationError, RasterioIOError
from rasterio.five import text_type, string_types
from rasterio.transform import Affine
from rasterio.enums import ColorInterp, MaskFlags, Resampling
from rasterio.sample import sample_gen
from rasterio.vfs import parse_path
from rasterio.warnings import NodataShadowWarning


log = logging.getLogger('rasterio')


cdef bint in_dtype_range(value, dtype):
    """Returns True if value is in the range of dtype, else False."""
    infos = {
        'c': np.finfo,
        'f': np.finfo,
        'i': np.iinfo,
        'u': np.iinfo,
        # Cython 0.22 returns dtype.kind as an int and will not cast to a char
        99: np.finfo,
        102: np.finfo,
        105: np.iinfo,
        117: np.iinfo
    }
    key = np.dtype(dtype).kind
    if np.isnan(value):
        return key in ('c', 'f', 99, 102)

    rng = infos[key](dtype)
    return rng.min <= value <= rng.max

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

    buf = np.zeros(
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


cdef int io_multi_mask(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.uint8_t[:, :, :] buffer,
        long[:] indexes,
        int count):
    cdef int i, j, retval=0
    cdef void *hband
    cdef void *hmask

    for i in range(count):
        j = indexes[i]
        hband = _gdal.GDALGetRasterBand(hds, j)
        if hband == NULL:
            raise ValueError("Null band")
        hmask = _gdal.GDALGetMaskBand(hband)
        if hmask == NULL:
            raise ValueError("Null mask band")
        with nogil:
            retval = _gdal.GDALRasterIO(
                hmask, mode, xoff, yoff, width, height,
                &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 1, 0, 0)
            if retval:
                break
    return retval


cdef int io_auto(image, void *hband, bint write):
    """
    Convenience function to handle IO with a GDAL band and a 2D numpy image

    :param image: a numpy 2D image
    :param hband: an instance of GDALGetRasterBand
    :param write: 1 (True) uses write mode (writes image into band),
                  0 (False) uses read mode (reads band into image)
    :return: the return value from the data-type specific IO function
    """

    cdef int ndims = len(image.shape)
    cdef int height = image.shape[-2]
    cdef int width = image.shape[-1]
    cdef int count
    cdef long[:] indexes
    dtype_name = image.dtype.name

    if ndims == 2:
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
    elif ndims == 3:
        count = image.shape[0]
        indexes = np.arange(1, count + 1)

        dtype_name = image.dtype.name

        if dtype_name == "float32":
            return io_multi_float32(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        elif dtype_name == "float64":
            return io_multi_float64(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        elif dtype_name == "uint8":
            return io_multi_ubyte(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        elif dtype_name == "int16":
            return io_multi_int16(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        elif dtype_name == "int32":
            return io_multi_int32(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        elif dtype_name == "uint16":
            return io_multi_uint16(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        elif dtype_name == "uint32":
            return io_multi_uint32(hband, write, 0, 0, width, height, image,
                                    indexes, count)
        else:
            raise ValueError("Image dtype is not supported for this function."
                             "Must be float32, float64, int16, int32, uint8, "
                             "uint16, or uint32")

    else:
        raise ValueError("Specified image must have 2 or 3 dimensions")


cdef class RasterReader(_base.DatasetReader):

    def read_band(self, bidx, out=None, window=None, masked=False):
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
        warnings.warn(
            "read_band() is deprecated and will be removed by Rasterio 1.0. "
            "Please use read() instead.",
            FutureWarning,
            stacklevel=2)
        return self.read(bidx, out=out, window=window, masked=masked)


    def read(self, indexes=None, out=None, window=None, masked=False,
            boundless=False):
        """Read raster bands as a multidimensional array

        Parameters
        ----------
        indexes : list of ints or a single int, optional
            If `indexes` is a list, the result is a 3D array, but is
            a 2D array if it is a band index number.

        out: numpy ndarray, optional
            As with Numpy ufuncs, this is an optional reference to an
            output array with the same dimensions and shape into which
            data will be placed.
            
            *Note*: the method's return value may be a view on this
            array. In other words, `out` is likely to be an
            incomplete representation of the method's results.

        window : a pair (tuple) of pairs of ints, optional
            The optional `window` argument is a 2 item tuple. The first
            item is a tuple containing the indexes of the rows at which
            the window starts and stops and the second is a tuple
            containing the indexes of the columns at which the window
            starts and stops. For example, ((0, 2), (0, 2)) defines
            a 2x2 window at the upper left of the raster dataset.

        masked : bool, optional
            If `masked` is `True` the return value will be a masked
            array. Otherwise (the default) the return value will be a 
            regular array. Masks will be exactly the inverse of the
            GDAL RFC 15 conforming arrays returned by read_masks().

        boundless : bool, optional (default `False`)
            If `True`, windows that extend beyond the dataset's extent
            are permitted and partially or completely filled arrays will
            be returned as appropriate.

        Returns
        -------
        Numpy ndarray or a view on a Numpy ndarray

        Note: as with Numpy ufuncs, an object is returned even if you
        use the optional `out` argument and the return value shall be
        preferentially used by callers.
        """

        cdef void *hband = NULL

        return2d = False
        if indexes is None:
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

            dtype = self.dtypes[idx]
            check_dtypes.add(dtype)

            ndv = self._nodatavals[idx]
            # Change given nodatavals to the closest value that
            # can be represented by this band's data type to
            # match GDAL's strategy.
            if ndv is not None:
                if np.dtype(dtype).kind in ('i', 'u'):
                    info = np.iinfo(dtype)
                    dt_min, dt_max = info.min, info.max
                elif np.dtype(dtype).kind in ('f', 'c'):
                    info = np.finfo(dtype)
                    dt_min, dt_max = info.min, info.max
                else:
                    dt_min, dt_max = False, True
                if ndv < dt_min:
                    ndv = dt_min
                elif ndv > dt_max:
                    ndv = dt_max

            nodatavals.append(ndv)

        # Mixed dtype reads are not supported at this time.
        if len(check_dtypes) > 1:
            raise ValueError("more than one 'dtype' found")
        elif len(check_dtypes) == 0:
            dtype = self.dtypes[0]
        else:
            dtype = check_dtypes.pop()

        # Get the natural shape of the read window, boundless or not.
        win_shape = (len(indexes),)
        if window:
            if boundless:
                win_shape += (
                        window[0][1]-window[0][0], window[1][1]-window[1][0])
            else:
                window = crop_window(
                    eval_window(window, self.height, self.width),
                    self.height, self.width
                )
                (r_start, r_stop), (c_start, c_stop) = window
                win_shape += (r_stop - r_start, c_stop - c_start)
        else:
            win_shape += self.shape

        if out is not None:
            if out.dtype != dtype:
                raise ValueError(
                    "the array's dtype '%s' does not match "
                    "the file's dtype '%s'" % (out.dtype, dtype))
            if out.shape[0] != win_shape[0]:
                raise ValueError(
                    "'out' shape %s does not match window shape %s" %
                    (out.shape, win_shape))

        # Masking
        # -------
        #
        # If masked is True, we check the GDAL mask flags using
        # GDALGetMaskFlags. If GMF_ALL_VALID for all bands, we do not
        # call read_masks(), but pass `mask=False` to the masked array
        # constructor. Else, we read the GDAL mask bands using
        # read_masks(), invert them and use them in constructing masked
        # arrays.

        if masked:

            mask_flags = [0]*self.count
            for i, j in zip(range(self.count), self.indexes):
                hband = _gdal.GDALGetRasterBand(self._hds, j)
                mask_flags[i] = _gdal.GDALGetMaskFlags(hband)

            all_valid = all([flag & 0x01 == 1 for flag in mask_flags])

            log.debug("all_valid: %s", all_valid)
            log.debug("mask_flags: %r", mask_flags)

        if out is None:
            out = np.zeros(win_shape, dtype)
            for ndv, arr in zip(
                    nodatavals, out if len(out.shape) == 3 else [out]):
                if ndv is not None:
                    arr.fill(ndv)

        # We can jump straight to _read() in some cases. We can ignore
        # the boundless flag if there's no given window.
        if not boundless or not window:
            out = self._read(indexes, out, window, dtype)

            if masked:
                if all_valid:
                    mask = np.ma.nomask
                else:
                    mask = np.empty(out.shape, 'uint8')
                    mask = ~self._read(
                        indexes, mask, window, 'uint8', masks=True
                        ).astype('bool')

                kwds = {'mask': mask}
                # Set a fill value only if the read bands share a
                # single nodata value.
                if len(set(nodatavals)) == 1:
                    if nodatavals[0] is not None:
                        kwds['fill_value'] = nodatavals[0]
                out = np.ma.array(out, **kwds)

        else:
            # Compute the overlap between the dataset and the boundless window.
            overlap = ((
                max(min(window[0][0], self.height), 0),
                max(min(window[0][1], self.height), 0)), (
                max(min(window[1][0], self.width), 0),
                max(min(window[1][1], self.width), 0)))

            if overlap != ((0, 0), (0, 0)):
                # Prepare a buffer.
                window_h, window_w = win_shape[-2:]
                overlap_h = overlap[0][1] - overlap[0][0]
                overlap_w = overlap[1][1] - overlap[1][0]
                scaling_h = float(out.shape[-2:][0])/window_h
                scaling_w = float(out.shape[-2:][1])/window_w
                buffer_shape = (
                        int(round(overlap_h*scaling_h)),
                        int(round(overlap_w*scaling_w)))
                data = np.empty(win_shape[:-2] + buffer_shape, dtype)
                data = self._read(indexes, data, overlap, dtype)

                if masked:
                    mask = np.empty(win_shape[:-2] + buffer_shape, 'uint8')
                    mask = ~self._read(
                        indexes, mask, overlap, 'uint8', masks=True
                        ).astype('bool')
                    kwds = {'mask': mask}
                    if len(set(nodatavals)) == 1:
                        if nodatavals[0] is not None:
                            kwds['fill_value'] = nodatavals[0]
                    data = np.ma.array(data, **kwds)

            else:
                data = None
                if masked:
                    kwds = {'mask': True}
                    if len(set(nodatavals)) == 1:
                        if nodatavals[0] is not None:
                            kwds['fill_value'] = nodatavals[0]
                    out = np.ma.array(out, **kwds)

            if data is not None:
                # Determine where to put the data in the output window.
                data_h, data_w = buffer_shape
                roff = 0
                coff = 0
                if window[0][0] < 0:
                    roff = -window[0][0] * scaling_h
                if window[1][0] < 0:
                    coff = -window[1][0] * scaling_w

                for dst, src in zip(
                        out if len(out.shape) == 3 else [out],
                        data if len(data.shape) == 3 else [data]):
                    dst[roff:roff+data_h, coff:coff+data_w] = src

                if masked:
                    if not hasattr(out, 'mask'):
                        kwds = {'mask': True}
                        if len(set(nodatavals)) == 1:
                            if nodatavals[0] is not None:
                                kwds['fill_value'] = nodatavals[0]
                        out = np.ma.array(out, **kwds)

                    for dst, src in zip(
                            out.mask if len(out.shape) == 3 else [out.mask],
                            data.mask if len(data.shape) == 3 else [data.mask]):
                        dst[roff:roff+data_h, coff:coff+data_w] = src

        if return2d:
            out.shape = out.shape[1:]

        return out


    def read_masks(self, indexes=None, out=None, window=None, boundless=False):
        """Read raster band masks as a multidimensional array

        Parameters
        ----------
        indexes : list of ints or a single int, optional
            If `indexes` is a list, the result is a 3D array, but is
            a 2D array if it is a band index number.

        out: numpy ndarray, optional
            As with Numpy ufuncs, this is an optional reference to an
            output array with the same dimensions and shape into which
            data will be placed.
            
            *Note*: the method's return value may be a view on this
            array. In other words, `out` is likely to be an
            incomplete representation of the method's results.

        window : a pair (tuple) of pairs of ints, optional
            The optional `window` argument is a 2 item tuple. The first
            item is a tuple containing the indexes of the rows at which
            the window starts and stops and the second is a tuple
            containing the indexes of the columns at which the window
            starts and stops. For example, ((0, 2), (0, 2)) defines
            a 2x2 window at the upper left of the raster dataset.

        boundless : bool, optional (default `False`)
            If `True`, windows that extend beyond the dataset's extent
            are permitted and partially or completely filled arrays will
            be returned as appropriate.

        Returns
        -------
        Numpy ndarray or a view on a Numpy ndarray

        Note: as with Numpy ufuncs, an object is returned even if you
        use the optional `out` argument and the return value shall be
        preferentially used by callers.
        """

        return2d = False
        if indexes is None:
            indexes = self.indexes
        elif isinstance(indexes, int):
            indexes = [indexes]
            return2d = True
            if out is not None and out.ndim == 2:
                out.shape = (1,) + out.shape
        if not indexes:
            raise ValueError("No indexes to read")

        # Get the natural shape of the read window, boundless or not.
        win_shape = (len(indexes),)
        if window:
            if boundless:
                win_shape += (
                        window[0][1]-window[0][0], window[1][1]-window[1][0])
            else:
                w = eval_window(window, self.height, self.width)
                minr = min(max(w[0][0], 0), self.height)
                maxr = max(0, min(w[0][1], self.height))
                minc = min(max(w[1][0], 0), self.width)
                maxc = max(0, min(w[1][1], self.width))
                win_shape += (maxr - minr, maxc - minc)
                window = ((minr, maxr), (minc, maxc))
        else:
            win_shape += self.shape
        
        dtype = 'uint8'

        if out is not None:
            if out.dtype != np.dtype(dtype):
                raise ValueError(
                    "the out array's dtype '%s' does not match '%s'"
                    % (out.dtype, dtype))
            if out.shape[0] != win_shape[0]:
                raise ValueError(
                    "'out' shape %s does not match window shape %s" %
                    (out.shape, win_shape))
        if out is None:
            out = np.zeros(win_shape, 'uint8')

        # We can jump straight to _read() in some cases. We can ignore
        # the boundless flag if there's no given window.
        if not boundless or not window:
            out = self._read(indexes, out, window, dtype, masks=True)

        else:
            # Compute the overlap between the dataset and the boundless window.
            overlap = ((
                max(min(window[0][0], self.height), 0),
                max(min(window[0][1], self.height), 0)), (
                max(min(window[1][0], self.width), 0),
                max(min(window[1][1], self.width), 0)))

            if overlap != ((0, 0), (0, 0)):
                # Prepare a buffer.
                window_h, window_w = win_shape[-2:]
                overlap_h = overlap[0][1] - overlap[0][0]
                overlap_w = overlap[1][1] - overlap[1][0]
                scaling_h = float(out.shape[-2:][0])/window_h
                scaling_w = float(out.shape[-2:][1])/window_w
                buffer_shape = (int(overlap_h*scaling_h), int(overlap_w*scaling_w))
                data = np.empty(win_shape[:-2] + buffer_shape, 'uint8')
                data = self._read(indexes, data, overlap, dtype, masks=True)
            else:
                data = None

            if data is not None:
                # Determine where to put the data in the output window.
                data_h, data_w = data.shape[-2:]
                roff = 0
                coff = 0
                if window[0][0] < 0:
                    roff = int(window_h*scaling_h) - data_h
                if window[1][0] < 0:
                    coff = int(window_w*scaling_w) - data_w
                for dst, src in zip(
                        out if len(out.shape) == 3 else [out],
                        data if len(data.shape) == 3 else [data]):
                    dst[roff:roff+data_h, coff:coff+data_w] = src

        if return2d:
            out.shape = out.shape[1:]

        return out


    def _read(self, indexes, out, window, dtype, masks=False):
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

        if self._hds == NULL:
            raise ValueError("can't read closed raster file")

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

        if masks:
            # Warn if nodata attribute is shadowing an alpha band.
            if self.count == 4 and self.colorinterp(4) == ColorInterp.alpha:
                for flags in self.mask_flags:
                    if flags & MaskFlags.nodata:
                        warnings.warn(NodataShadowWarning())

            retval = io_multi_mask(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, indexes_count)
        elif gdt == 1:
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

        return out


    def read_mask(self, indexes=None, out=None, window=None, boundless=False):
        """Read the mask band into an `out` array if provided, 
        otherwise return a new array containing the dataset's
        valid data mask.

        The optional `window` argument takes a tuple like:
        
            ((row_start, row_stop), (col_start, col_stop))
            
        specifying a raster subset to write into.
        """
        cdef void *hband
        cdef void *hmask

        warnings.warn(
            "read_mask() is deprecated and will be removed by Rasterio 1.0. "
            "Please use read_masks() instead.",
            FutureWarning,
            stacklevel=2)

        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
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

        io_ubyte(
            hmask, 0, xoff, yoff, width, height, out)
        return out

    def sample(self, xy, indexes=None):
        """Get the values of a dataset at certain positions

        Values are from the nearest pixel. They are not interpolated.

        Parameters
        ----------
        xy : iterable, pairs of floats
            A sequence or generator of (x, y) pairs.

        indexes : list of ints or a single int, optional
            If `indexes` is a list, the result is a 3D array, but is
            a 2D array if it is a band index number.

        Returns
        -------
        Iterable, yielding dataset values for the specified `indexes`
        as an ndarray.
        """
        # In https://github.com/mapbox/rasterio/issues/378 a user has
        # found what looks to be a Cython generator bug. Until that can
        # be confirmed and fixed, the workaround is a pure Python 
        # generator implemented in sample.py.
        return sample_gen(self, xy, indexes)


cdef class RasterUpdater(RasterReader):
    # Read-write access to raster data and metadata.

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
        cdef char *key_c = NULL
        cdef char *val_c = NULL
        cdef void *drv = NULL
        cdef void *hband = NULL
        cdef int success


        # Is there not a driver manager already?
        if driver_count() == 0 and not self.env:
            # create a local manager and enter
            self.env = GDALEnv(True)
        else:
            self.env = GDALEnv(False)
        self.env.start()

        path, archive, scheme = parse_path(self.name)
        if scheme and scheme != 'file':
            raise TypeError(
                "VFS '{0}' datasets can not be created or updated.".format(
                    scheme))

        name_b = path.encode('utf-8')
        cdef const char *fname = name_b

        kwds = []

        if self.mode == 'w':
            # GDAL can Create() GTiffs. Many other formats only support
            # CreateCopy(). Rasterio lets you write GTiffs *only* for now.
            if self.driver not in ['GTiff']:
                raise ValueError("only GTiffs can be opened in 'w' mode")

            # Delete existing file, create.
            if os.path.exists(path):
                os.unlink(path)
            
            driver_b = self.driver.encode('utf-8')
            drv_name = driver_b
            
            try:
                with CPLErrors() as cple:
                    drv = _gdal.GDALGetDriverByName(drv_name)
                    cple.check()
            except Exception as err:
                self.env.stop()
                raise DriverRegistrationError(str(err))
            
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

                # Guard against block size that exceed image size.
                if k == 'BLOCKXSIZE' and int(v) > self.width:
                    raise ValueError("blockxsize exceeds raster width.")
                if k == 'BLOCKYSIZE' and int(v) > self.height:
                    raise ValueError("blockysize exceeds raster height.")

                key_b = k.encode('utf-8')
                val_b = v.encode('utf-8')
                key_c = key_b
                val_c = val_b
                options = _gdal.CSLSetNameValue(options, key_c, val_c)
                log.debug(
                    "Option: %r\n", 
                    (k, _gdal.CSLFetchNameValue(options, key_c)))

            try:
                with CPLErrors() as cple:
                    self._hds = _gdal.GDALCreate(
                        drv, fname, self.width, self.height, self._count,
                        gdal_dtype, options)
                    cple.check()
            except Exception as err:
                self.env.stop()
                if options != NULL:
                    _gdal.CSLDestroy(options)
                raise

            if self._init_nodata is not None:

                if not in_dtype_range(self._init_nodata, self._init_dtype):
                    raise ValueError(
                        "Given nodata value, %s, is beyond the valid "
                        "range of its data type, %s." % (
                            self._init_nodata, self._init_dtype))

                for i in range(self._count):
                    hband = _gdal.GDALGetRasterBand(self._hds, i+1)
                    success = _gdal.GDALSetRasterNoDataValue(
                                    hband, self._init_nodata)

            if self._transform:
                self.write_transform(self._transform)
            if self._crs:
                self.set_crs(self._crs)
        
        elif self.mode == 'r+':
            try:
                with CPLErrors() as cple:
                    self._hds = _gdal.GDALOpen(fname, 1)
                    cple.check()
            except CPLE_OpenFailed as err:
                self.env.stop()
                raise RasterioIOError(str(err))

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

        if [abs(v) for v in transform] == [0, 1, 0, 0, 0, 1]:
            warnings.warn(
                "Dataset uses default geotransform (Affine.identity). "
                "No transform will be written to the output by GDAL.",
                UserWarning
            )

        cdef double gt[6]
        for i in range(6):
            gt[i] = transform[i]
        err = _gdal.GDALSetGeoTransform(self._hds, gt)
        if err:
            raise ValueError("transform not set: %s" % transform)
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

    def set_nodatavals(self, vals):
        cdef void *hband = NULL
        cdef double nodataval
        cdef int success

        for i, val in zip(self.indexes, vals):
            hband = _gdal.GDALGetRasterBand(self._hds, i)
            nodataval = val
            success = _gdal.GDALSetRasterNoDataValue(hband, nodataval)
            if success:
                raise ValueError("Invalid nodata value: %r", val)
        self._nodatavals = vals

    property nodatavals:
        """A list by band of a dataset's nodata values.
        """

        def __get__(self):
            return self.get_nodatavals()

        def __set__(self, value):
            warnings.warn(
                "nodatavals.__set__() is deprecated and will be removed by "
                "Rasterio 1.0. Please use nodata.__set__() instead.",
                FutureWarning,
                stacklevel=2)
            self.set_nodatavals(value)

    property nodata:
        """The dataset's single nodata value."""

        def __get__(self):
            return self.nodatavals[0]

        def __set__(self, value):
            self.set_nodatavals([value for old_val in self.nodatavals])

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
        if bidx > 0:
            hobj = self.band(bidx)
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
        cdef void *hBand = NULL
        cdef void *hTable
        cdef _gdal.GDALColorEntry color
        if bidx > 0:
            hBand = self.band(bidx)

        # RGB only for now. TODO: the other types.
        # GPI_Gray=0,  GPI_RGB=1, GPI_CMYK=2,     GPI_HLS=3
        hTable = _gdal.GDALCreateColorTable(1)
        vals = range(256)

        for i, rgba in colormap.items():
            if len(rgba) == 4 and self.driver in ('GTiff'):
                warnings.warn(
                    "This format doesn't support alpha in colormap entries. "
                    "The value will be ignored.")

            elif len(rgba) == 3:
                rgba = tuple(rgba) + (255,)

            if i not in vals:
                log.warn("Invalid colormap key %d", i)
                continue

            color.c1, color.c2, color.c3, color.c4 = rgba
            _gdal.GDALSetColorEntry(hTable, i, &color)

        # TODO: other color interpretations?
        _gdal.GDALSetRasterColorInterpretation(hBand, 1)
        _gdal.GDALSetRasterColorTable(hBand, hTable)
        _gdal.GDALDestroyColorTable(hTable)

    def write_mask(self, mask, window=None):
        """Write the valid data mask src array into the dataset's band
        mask.

        The optional `window` argument takes a tuple like:

            ((row_start, row_stop), (col_start, col_stop))

        specifying a raster subset to write into.
        """
        cdef void *hband = NULL
        cdef void *hmask = NULL

        hband = self.band(1)

        try:
            with CPLErrors() as cple:
                retval = _gdal.GDALCreateMaskBand(hband, 0x02)
                cple.check()
                hmask = _gdal.GDALGetMaskBand(hband)
                cple.check()
                log.debug("Created mask band")
        except:
            raise RasterioIOError("Failed to get mask.")

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
        
        if mask is True:
            _gdal.GDALFillRaster(hmask, 255, 0)
        elif mask is False:
            _gdal.GDALFillRaster(hmask, 0, 0)
        elif mask.dtype == np.bool:
            array = 255 * mask.astype(np.uint8)
            retval = io_ubyte(
                hmask, 1, xoff, yoff, width, height, array)
        else:
            retval = io_ubyte(
                hmask, 1, xoff, yoff, width, height, mask)

    def build_overviews(self, factors, resampling=Resampling.nearest):
        """Build overviews at one or more decimation factors for all
        bands of the dataset."""
        cdef int *factors_c = NULL
        cdef const char *resampling_c = NULL

        # Allocate arrays.
        if factors:
            factors_c = <int *>_gdal.CPLMalloc(len(factors)*sizeof(int))
            for i, factor in enumerate(factors):
                factors_c[i] = factor
            try:
                with CPLErrors() as cple:
                    resampling_b = resampling.value.encode('utf-8')
                    resampling_c = resampling_b
                    err = _gdal.GDALBuildOverviews(self._hds, resampling_c,
                        len(factors), factors_c, 0, NULL, NULL, NULL)
                    cple.check()
            finally:
                if factors_c != NULL:
                    _gdal.CPLFree(factors_c)


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

    def __cinit__(self, image, transform=None, crs=None):
        """
        Create in-memory raster dataset, and populate its initial values with
        the values in image.

        :param image: 2D numpy array.  Must be of supported data type
        (see rasterio.dtypes.dtype_rev)
        :param transform: GDAL compatible transform array
        """

        self._image = image
        self.dataset = NULL

        cdef int i = 0  # avoids Cython warning in for loop below
        cdef const char *srcwkt = NULL
        cdef void *osr = NULL
        cdef void *memdriver = NULL

        # Several GDAL operations require the array of band IDs as input
        self.band_ids[0] = 1

        with CPLErrors() as cple:
            memdriver = _gdal.GDALGetDriverByName("MEM")
            cple.check()
            self.dataset = _gdal.GDALCreate(
                memdriver, "output", image.shape[1], image.shape[0],
                1, <_gdal.GDALDataType>dtypes.dtype_rev[image.dtype.name],
                NULL)
            cple.check()

        if transform is not None:
            for i in range(6):
                self.transform[i] = transform[i]
            err = _gdal.GDALSetGeoTransform(self.dataset, self.transform)
            if err:
                raise ValueError("transform not set: %s" % transform)

        # Set projection if specified (for use with 
        # GDALSuggestedWarpOutput2()).
        if crs:
            osr = _base._osr_from_crs(crs)
            _gdal.OSRExportToWkt(osr, &srcwkt)
            _gdal.GDALSetProjection(self.dataset, srcwkt)
            log.debug("Set CRS on temp source dataset: %s", srcwkt)
            _gdal.CPLFree(srcwkt)
            _gdal.OSRDestroySpatialReference(osr)


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
            self.dataset = NULL

    def read(self):
        io_auto(self._image, self.band, False)
        return self._image

    def write(self, image):
        io_auto(image, self.band, True)


cdef class IndirectRasterUpdater(RasterUpdater):

    def __repr__(self):
        return "<%s IndirectRasterUpdater name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open', 
            self.name,
            self.mode)

    def start(self):
        cdef const char *drv_name = NULL
        cdef void *drv = NULL
        cdef void *memdrv = NULL
        cdef void *hband = NULL
        cdef void *temp = NULL
        cdef int success
        name_b = self.name.encode('utf-8')
        cdef const char *fname = name_b

        memdrv = _gdal.GDALGetDriverByName("MEM")

        # Is there not a driver manager already?
        if driver_count() == 0 and not self.env:
            # create a local manager and enter
            self.env = GDALEnv(True)
        else:
            self.env = GDALEnv(False)
        self.env.start()
        
        if self.mode == 'w':
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

            try:
                with CPLErrors() as cple:
                    self._hds = _gdal.GDALCreate(
                        memdrv, "temp", self.width, self.height, self._count,
                        gdal_dtype, NULL)
                    cple.check()
            except:
                self.env.close()
                raise

            if self._init_nodata is not None:
                for i in range(self._count):
                    hband = self.band(i+1)
                    success = _gdal.GDALSetRasterNoDataValue(
                                    hband, self._init_nodata)
            if self._transform:
                self.write_transform(self._transform)
            if self._crs:
                self.set_crs(self._crs)

        elif self.mode == 'r+':
            try:
                with CPLErrors() as cple:
                    temp = _gdal.GDALOpen(fname, 0)
                    cple.check()
            except Exception as exc:
                raise RasterioIOError(str(exc))
            
            try:
                with CPLErrors() as cple:
                    self._hds = _gdal.GDALCreateCopy(
                        memdrv, "temp", temp, 1, NULL, NULL, NULL)
                    cple.check()
            except:
                raise

            drv = _gdal.GDALGetDatasetDriver(temp)
            drv_name = _gdal.GDALGetDriverShortName(drv)
            self.driver = drv_name.decode('utf-8')
            _gdal.GDALClose(temp)

        self._count = _gdal.GDALGetRasterCount(self._hds)
        self.width = _gdal.GDALGetRasterXSize(self._hds)
        self.height = _gdal.GDALGetRasterYSize(self._hds)
        self.shape = (self.height, self.width)

        self._transform = self.read_transform()
        self._crs = self.read_crs()
        self._crs_wkt = self.read_crs_wkt()

        # touch self.meta
        _ = self.meta

        self._closed = False

    def close(self):
        cdef const char *drv_name = NULL
        cdef char **options = NULL
        cdef char *key_c = NULL
        cdef char *val_c = NULL
        cdef void *drv = NULL
        cdef void *temp = NULL
        cdef int success
        name_b = self.name.encode('utf-8')
        cdef const char *fname = name_b

        # Delete existing file, create.
        if os.path.exists(self.name):
            os.unlink(self.name)

        driver_b = self.driver.encode('utf-8')
        drv_name = driver_b
        drv = _gdal.GDALGetDriverByName(drv_name)
        if drv == NULL:
            raise ValueError("NULL driver for %s", self.driver)

        kwds = []
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

        #self.update_tags(ns='rio_creation_kwds', **kwds)
        try:
            with CPLErrors() as cple:
                temp = _gdal.GDALCreateCopy(
                    drv, fname, self._hds, 1, options, NULL, NULL)
                cple.check()
        except:
            raise
        finally:
            if options != NULL:
                _gdal.CSLDestroy(options)
            if temp != NULL:
                _gdal.GDALClose(temp)


def writer(path, mode, **kwargs):
    # Dispatch to direct or indirect writer/updater according to the
    # format driver's capabilities.
    cdef void *hds = NULL
    cdef void *drv = NULL
    cdef const char *drv_name = NULL
    cdef const char *fname = NULL

    path, archive, scheme = parse_path(path)
    if scheme and scheme != 'file':
        raise TypeError(
            "VFS '{0}' datasets can not be created or updated.".format(
                scheme))

    if mode == 'w' and 'driver' in kwargs:
        if kwargs['driver'] == 'GTiff':
            return RasterUpdater(path, mode, **kwargs)
        else:
            return IndirectRasterUpdater(path, mode, **kwargs)
    else:
        # Peek into the dataset at path to determine it's format
        # driver.
        name_b = path.encode('utf-8')
        fname = name_b
        try:
            with CPLErrors() as cple:
                hds = _gdal.GDALOpen(fname, 0)
                cple.check()
        except CPLE_OpenFailed as exc:
            raise RasterioIOError(str(exc))

        drv = _gdal.GDALGetDatasetDriver(hds)
        drv_name = _gdal.GDALGetDriverShortName(drv)
        drv_name_b = drv_name
        driver = drv_name_b.decode('utf-8')
        _gdal.GDALClose(hds)

        if driver == 'GTiff':
            return RasterUpdater(path, mode)
        else:
            return IndirectRasterUpdater(path, mode)


def virtual_file_to_buffer(filename):
    """Read content of a virtual file into a Python bytes buffer."""
    cdef unsigned char *buff = NULL
    cdef const char *cfilename = NULL
    cdef _gdal.vsi_l_offset buff_len = 0
     
    filename_b = filename if not isinstance(filename, string_types) else filename.encode('utf-8')
    cfilename = filename_b
    
    try:
        with CPLErrors() as cple:
            buff = _gdal.VSIGetMemFileBuffer(cfilename, &buff_len, 0)
            cple.check()
    except:
        raise

    n = buff_len
    log.debug("Buffer length: %d bytes", n)
    cdef np.uint8_t[:] buff_view = <np.uint8_t[:n]>buff
    return buff_view


def get_data_window(arr, nodata=None):
    """
    Returns a window for the non-nodata pixels within the input array.

    Parameters
    ----------
    arr: numpy ndarray, <= 3 dimensions
    nodata: number
        If None, will either return a full window if arr is not a masked
        array, or will use the mask to determine non-nodata pixels.
        If provided, it must be a number within the valid range of the dtype
        of the input array.

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))

    """

    num_dims = len(arr.shape)
    if num_dims > 3:
        raise ValueError('get_data_window input array must have no more than '
                         '3 dimensions')

    if nodata is None:
        if not hasattr(arr, 'mask'):
            return ((0, arr.shape[-2]), (0, arr.shape[-1]))
    else:
        arr = np.ma.masked_array(arr, arr == nodata)

    if num_dims == 2:
        data_rows, data_cols = np.where(arr.mask == False)
    else:
        data_rows, data_cols = np.where(
            np.any(np.rollaxis(arr.mask, 0, 3) == False, axis=2)
        )

    if data_rows.size:
        row_range = (data_rows.min(), data_rows.max() + 1)
    else:
        row_range = (0, 0)

    if data_cols.size:
        col_range = (data_cols.min(), data_cols.max() + 1)
    else:
        col_range = (0, 0)

    return (row_range, col_range)


def window_union(windows):
    """
    Union windows and return the outermost extent they cover.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))
    """


    stacked = np.dstack(windows)
    return (
        (stacked[0, 0].min(), stacked[0, 1].max()),
        (stacked[1, 0].min(), stacked[1, 1]. max())
    )


def window_intersection(windows):
    """
    Intersect windows and return the innermost extent they cover.

    Will raise ValueError if windows do not intersect.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))
    """

    if not windows_intersect(windows):
        raise ValueError('windows do not intersect')

    stacked = np.dstack(windows)
    return (
        (stacked[0, 0].max(), stacked[0, 1].min()),
        (stacked[1, 0].max(), stacked[1, 1]. min())
    )


def windows_intersect(windows):
    """
    Test if windows intersect.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    boolean:
        True if all windows intersect.
    """

    from itertools import combinations

    def intersects(range1, range2):
        return not (
            range1[0] > range2[1] or range1[1] < range2[0]
        )

    windows = np.array(windows)

    for i in (0, 1):
        for c in combinations(windows[:, i], 2):
            if not intersects(*c):
                return False

    return True
