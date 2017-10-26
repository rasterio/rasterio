"""Rasterio input/output."""

from __future__ import absolute_import

include "directives.pxi"
include "gdal.pxi"

import logging
import sys
import uuid
import warnings

import numpy as np

from rasterio._base import tastes_like_gdal
from rasterio._env import driver_count, GDALEnv
from rasterio._err import (
    GDALError, CPLE_OpenFailedError, CPLE_IllegalArgError)
from rasterio.crs import CRS
from rasterio.compat import text_type, string_types
from rasterio import dtypes
from rasterio.enums import ColorInterp, MaskFlags, Resampling
from rasterio.errors import CRSError, DriverRegistrationError
from rasterio.errors import RasterioIOError, NotGeoreferencedWarning
from rasterio.errors import NodataShadowWarning, WindowError
from rasterio.sample import sample_gen
from rasterio.transform import Affine
from rasterio.vfs import parse_path, vsi_path
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window, intersection

from libc.stdio cimport FILE
cimport numpy as np

from rasterio._base cimport (
    _osr_from_crs, _safe_osr_release, get_driver_name, DatasetBase)
from rasterio._err cimport exc_wrap_int, exc_wrap_pointer, exc_wrap_vsilfile
from rasterio._shim cimport (
    delete_nodata_value, io_band, io_multi_band, io_multi_mask)


log = logging.getLogger(__name__)


def _delete_dataset_if_exists(path):

    """Delete dataset if it already exists.  Not a substitute for
    ``rasterio.shutil.exists()`` and ``rasterio.shutil.delete()``.

    Parameters
    ----------
    path : str
        Dataset path
    """

    b_path = path.encode('utf-8')
    cdef char* c_path = b_path
    with nogil:
        h_dataset = GDALOpenShared(c_path, <GDALAccess>0)
    try:
        h_dataset = exc_wrap_pointer(h_dataset)
        h_driver = GDALGetDatasetDriver(h_dataset)
        if h_driver != NULL:
            with nogil:
                GDALDeleteDataset(h_driver, c_path)
    except CPLE_OpenFailedError:
        pass
    finally:
        GDALClose(h_dataset)


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
        117: np.iinfo}

    key = np.dtype(dtype).kind
    if np.isnan(value):
        return key in ('c', 'f', 99, 102)

    rng = infos[key](dtype)
    return rng.min <= value <= rng.max


cdef int io_auto(data, GDALRasterBandH band, bint write, int resampling=0):
    """Convenience function to handle IO with a GDAL band.

    :param data: a numpy ndarray
    :param band: an instance of GDALGetRasterBand
    :param write: 1 (True) uses write mode (writes data into band),
                  0 (False) uses read mode (reads band into data)
    :return: the return value from the data-type specific IO function
    """
    cdef int ndims = len(data.shape)
    cdef float height = data.shape[-2]
    cdef float width = data.shape[-1]

    if ndims == 2:
        return io_band(band, write, 0.0, 0.0, width, height, data,
                       resampling=resampling)
    elif ndims == 3:
        indexes = np.arange(1, data.shape[0] + 1)
        return io_multi_band(band, write, 0.0, 0.0, width, height, data,
                             indexes, resampling=resampling)
    else:
        raise ValueError("Specified data must have 2 or 3 dimensions")


cdef class DatasetReaderBase(DatasetBase):

    def read(self, indexes=None, out=None, window=None, masked=False,
            out_shape=None, boundless=False, resampling=Resampling.nearest,
            fill_value=None):
        """Read raster bands as a multidimensional array

        Parameters
        ----------
        indexes : list of ints or a single int, optional
            If `indexes` is a list, the result is a 3D array, but is
            a 2D array if it is a band index number.

        out : numpy ndarray, optional
            As with Numpy ufuncs, this is an optional reference to an
            output array into which data will be placed. If the height
            and width of `out` differ from that of the specified
            window (see below), the raster image will be decimated or
            replicated using the specified resampling method (also see
            below).

            *Note*: the method's return value may be a view on this
            array. In other words, `out` is likely to be an
            incomplete representation of the method's results.

            This parameter cannot be combined with `out_shape`.

        out_shape : tuple, optional
            A tuple describing the shape of a new output array. See
            `out` (above) for notes on image decimation and
            replication.

            Cannot combined with `out`.

        window : a pair (tuple) of pairs of ints or Window, optional
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

        fill_value : scalar
            Fill value applied in the `boundless=True` case only.

        Returns
        -------
        Numpy ndarray or a view on a Numpy ndarray

        Note: as with Numpy ufuncs, an object is returned even if you
        use the optional `out` argument and the return value shall be
        preferentially used by callers.
        """

        cdef GDALRasterBandH band = NULL

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

            log.debug("Output nodata value read from file: %r", ndv)

            # Change given nodatavals to the closest value that
            # can be represented by this band's data type to
            # match GDAL's strategy.
            if fill_value:
                ndv = fill_value
                log.debug("Output nodata value set from fill value")

            elif ndv is not None:
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

        log.debug("Output nodata values: %r", nodatavals)

        # Mixed dtype reads are not supported at this time.
        if len(check_dtypes) > 1:
            raise ValueError("more than one 'dtype' found")
        elif len(check_dtypes) == 0:
            dtype = self.dtypes[0]
        else:
            dtype = check_dtypes.pop()

        # Get the natural shape of the read window, boundless or not.
        # The window can have float values. In this case, we round up
        # when computing the shape.

        # Stub the win_shape.
        win_shape = (len(indexes),)

        if window:

            if isinstance(window, tuple):
                window = Window.from_slices(
                    *window, height=self.height, width=self.width,
                    boundless=boundless)

            if not boundless:
                window = window.crop(self.height, self.width)

            int_window = window.round_lengths()
            win_shape += (int(int_window.height), int(int_window.width))

        else:
            win_shape += self.shape

        if out is not None and out_shape is not None:
            raise ValueError("out and out_shape are exclusive")

        # `out` takes precedence over `out_shape`.
        elif out is not None:
            if out.dtype != dtype:
                raise ValueError(
                    "the array's dtype '%s' does not match "
                    "the file's dtype '%s'" % (out.dtype, dtype))
            if out.shape[0] != win_shape[0]:
                raise ValueError(
                    "'out' shape %s does not match window shape %s" %
                    (out.shape, win_shape))

        else:
            if out_shape is not None:
                if len(out_shape) == 2:
                    out_shape = (len(indexes),) + out_shape
            else:
                out_shape = win_shape

            # We're filling in both the bounded and boundless cases.
            # TODO: profile and see if we should avoid this in the
            # bounded case.

            if boundless:
                out = np.zeros(out_shape, dtype=dtype)
            else:
                out = np.empty(out_shape, dtype=dtype)

            for i, (ndv, arr) in enumerate(zip(
                    nodatavals, out if len(out.shape) == 3 else [out])):

                if ndv is not None:
                    arr.fill(ndv)

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
            enums = self.mask_flag_enums
            all_valid = all([MaskFlags.all_valid in flags for flags in enums])
            log.debug("all_valid: %s", all_valid)
            log.debug("mask_flags: %r", enums)

        # We can jump straight to _read() in some cases. We can ignore
        # the boundless flag if there's no given window.
        if not boundless or not window:

            log.debug("Jump straight to _read()")
            log.debug("Window: %r", window)

            out = self._read(indexes, out, window, dtype,
                             resampling=resampling)

            if masked:
                if all_valid:
                    mask = np.ma.nomask
                else:
                    mask = np.zeros(out.shape, 'uint8')
                    mask = ~self._read(
                        indexes, mask, window, 'uint8', masks=True,
                        resampling=resampling).astype('bool')

                kwds = {'mask': mask}
                # Set a fill value only if the read bands share a
                # single nodata value.
                if len(set(nodatavals)) == 1:
                    if nodatavals[0] is not None:
                        kwds['fill_value'] = nodatavals[0]
                out = np.ma.array(out, **kwds)

        # If boundless.
        # Create a WarpedVRT to use its window and compositing logic.
        else:
            with WarpedVRT(
                    self,
                    dst_nodata=ndv,
                    dst_crs=self.crs,
                    dst_width=max(self.width, window.num_cols),
                    dst_height=max(self.height, window.num_rows),
                    dst_transform=self.window_transform(window),
                    resampling=resampling) as vrt:
                out = vrt._read(indexes, out, Window(0, 0, window.num_cols, window.num_rows), None)

                if masked:
                    if all_valid:
                        mask = np.ma.nomask
                    else:
                        mask = np.zeros(out.shape, 'uint8')
                        mask = ~vrt._read(
                            indexes, mask, Window(0, 0, window.num_cols, window.num_rows), None, masks=True).astype('bool')

                    kwds = {'mask': mask}
                    # Set a fill value only if the read bands share a
                    # single nodata value.
                    if len(set(nodatavals)) == 1:
                        if nodatavals[0] is not None:
                            kwds['fill_value'] = nodatavals[0]
                    out = np.ma.array(out, **kwds)

        if return2d:
            out.shape = out.shape[1:]

        return out


    def read_masks(self, indexes=None, out=None, out_shape=None, window=None,
                   boundless=False, resampling=Resampling.nearest):
        """Read raster band masks as a multidimensional array

        Parameters
        ----------
        indexes : list of ints or a single int, optional
            If `indexes` is a list, the result is a 3D array, but is
            a 2D array if it is a band index number.

        out : numpy ndarray, optional
            As with Numpy ufuncs, this is an optional reference to an
            output array with the same dimensions and shape into which
            data will be placed.

            *Note*: the method's return value may be a view on this
            array. In other words, `out` is likely to be an
            incomplete representation of the method's results.

            Cannot combine with `out_shape`.

        out_shape : tuple, optional
            A tuple describing the output array's shape.  Allows for decimated
            reads without constructing an output Numpy array.

            Cannot combined with `out`.

        window : a pair (tuple) of pairs of ints or Window, optional
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

        # Stub the win_shape.
        win_shape = (len(indexes),)

        if window:

            if isinstance(window, tuple):
                window = Window.from_slices(
                    *window, height=self.height, width=self.width,
                    boundless=boundless)

            if not boundless:
                window = window.crop(self.height, self.width)

            int_window = window.round_lengths()
            win_shape += (int(int_window.height), int(int_window.width))

        else:
            win_shape += self.shape

        dtype = 'uint8'

        if out is not None and out_shape is not None:
            raise ValueError("out and out_shape are exclusive")
        elif out_shape is not None:
            if len(out_shape) == 2:
                out_shape = (len(indexes),) + out_shape
            out = np.zeros(out_shape, 'uint8')

        if out is not None:
            if out.dtype != np.dtype(dtype):
                raise ValueError(
                    "the out array's dtype '%s' does not match '%s'"
                    % (out.dtype, dtype))
            if out.shape[0] != win_shape[0]:
                raise ValueError(
                    "'out' shape %s does not match window shape %s" %
                    (out.shape, win_shape))
        else:
            out = np.zeros(win_shape, 'uint8')


        # We can jump straight to _read() in some cases. We can ignore
        # the boundless flag if there's no given window.
        if not boundless or not window:
            out = self._read(indexes, out, window, dtype, masks=True,
                             resampling=resampling)

        # If boundless is True.
        # Create a temporary VRT to use its source/dest windowing
        # and compositing logic.
        else:
            with WarpedVRT(
                    self,
                    dst_crs=self.crs,
                    dst_width=max(self.width, window.num_cols),
                    dst_height=max(self.height, window.num_rows),
                    dst_transform=self.window_transform(window),
                    resampling=resampling) as vrt:
                out = vrt._read(indexes, out, Window(0, 0, window.num_cols, window.num_rows), None, masks=True)

        if return2d:
            out.shape = out.shape[1:]

        return out


    def _read(self, indexes, out, window, dtype, masks=False,
              resampling=Resampling.nearest):
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
        cdef int aix, bidx, indexes_count
        cdef double height, width, xoff, yoff
        cdef int retval = 0
        cdef GDALDatasetH dataset = NULL

        if out is None:
            raise ValueError("An output array is required.")

        dataset = self.handle()

        if window:
            if not isinstance(window, Window):
                raise WindowError("window must be an instance of Window")

            yoff = window.row_off
            xoff = window.col_off

            # Now that we have floating point windows it's easy for
            # the number of pixels to read to slip below 1 due to
            # loss of floating point precision. Here we ensure that
            # we're reading at least one pixel.
            height = max(1.0, window.height)
            width = max(1.0, window.width)

        else:
            xoff = yoff = <int>0
            width = <int>self.width
            height = <int>self.height

        log.debug(
            "IO window xoff=%s yoff=%s width=%s height=%s",
            xoff, yoff, width, height)

        # Call io_multi* functions with C type args so that they
        # can release the GIL.
        indexes_arr = np.array(indexes, dtype=int)
        indexes_count = <int>indexes_arr.shape[0]

        if masks:
            # Warn if nodata attribute is shadowing an alpha band.
            if self.count == 4 and self.colorinterp[3] == ColorInterp.alpha:
                for flags in self.mask_flag_enums:
                    if MaskFlags.nodata in flags:
                        warnings.warn(NodataShadowWarning())

            retval = io_multi_mask(
                            self._hds, 0, xoff, yoff, width, height,
                            out, indexes_arr, resampling=resampling)

        else:
            retval = io_multi_band(self._hds, 0, xoff, yoff, width, height,
                                  out, indexes_arr, resampling=resampling)

        if retval in (1, 2, 3):
            raise IOError("Read or write failed")
        elif retval == 4:
            raise ValueError("NULL band")

        return out


    def dataset_mask(self, window=None, boundless=False):
        """Calculate the dataset's 2D mask. Derived from the individual band masks
        provided by read_masks().

        Parameters
        ----------
        window and boundless are passed directly to read_masks()

        Returns
        -------
        ndarray, shape=(self.height, self.width), dtype='uint8'
        0 = nodata, 255 = valid data

        The dataset mask is calculate based on the individual band masks according to
        the following logic, in order of precedence:

        1. If a .msk file, dataset-wide alpha or internal mask exists,
           it will be used as the dataset mask.
        2. If an 4-band RGBA with a shadow nodata value,
           band 4 will be used as the dataset mask.
        3. If a nodata value exists, use the binary OR (|) of the band masks
        4. If no nodata value exists, return a mask filled with 255

        Note that this differs from read_masks and GDAL RFC15
        in that it applies per-dataset, not per-band
        (see https://trac.osgeo.org/gdal/wiki/rfc15_nodatabitmask)
        """
        kwargs = {
            'window': window,
            'boundless': boundless}

        # GDAL found dataset-wide alpha band or mask
        # All band masks are equal so we can return the first
        if MaskFlags.per_dataset in self.mask_flag_enums[0]:
            return self.read_masks(1, **kwargs)

        # use Alpha mask if available and looks like RGB, even if nodata is shadowing
        elif self.count == 4 and self.colorinterp[0] == ColorInterp.red:
            return self.read_masks(4, **kwargs)

        # Or use the binary OR intersection of all GDALGetMaskBands
        else:
            mask = self.read_masks(1, **kwargs)
            for i in range(1, self.count):
                mask = mask | self.read_masks(i, **kwargs)
            return mask

    def read_mask(self, indexes=None, out=None, window=None, boundless=False):
        """Read the mask band into an `out` array if provided,
        otherwise return a new array containing the dataset's
        valid data mask.
        """
        warnings.warn(
            "read_mask() is deprecated and will be removed by Rasterio 1.0. "
            "Please use read_masks() instead.",
            DeprecationWarning,
            stacklevel=2)
        return self.read_masks(1, out=out, window=window, boundless=boundless)

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


cdef class MemoryFileBase(object):
    """Base for a BytesIO-like class backed by an in-memory file."""

    def __init__(self, file_or_bytes=None, filename=None, ext=''):
        """A file in an in-memory filesystem.

        Parameters
        ----------
        file_or_bytes : file or bytes
            A file opened in binary mode or bytes or a bytearray
        filename : str
            A filename for the in-memory file under /vsimem
        ext : str
            A file extension for the in-memory file under /vsimem. Ignored if
            filename was provided.
        """
        cdef VSILFILE *vsi_handle = NULL

        if file_or_bytes:
            if hasattr(file_or_bytes, 'read'):
                initial_bytes = file_or_bytes.read()
            else:
                initial_bytes = file_or_bytes
            if not isinstance(initial_bytes, (bytearray, bytes)):
                raise TypeError(
                    "Constructor argument must be a file opened in binary "
                    "mode or bytes/bytearray.")
        else:
            initial_bytes = b''

        if filename:
            # GDAL's SRTMHGT driver requires the filename to be "correct" (match
            # the bounds being written)
            self.name = '/vsimem/{0}'.format(filename)
        else:
            # GDAL 2.1 requires a .zip extension for zipped files.
            self.name = '/vsimem/{0}.{1}'.format(uuid.uuid4(), ext.lstrip('.'))

        self.path = self.name.encode('utf-8')
        self._pos = 0
        self.closed = False

        self._initial_bytes = initial_bytes
        cdef unsigned char *buffer = self._initial_bytes

        if self._initial_bytes:

            vsi_handle = VSIFileFromMemBuffer(
                self.path, buffer, len(self._initial_bytes), 0)

            if vsi_handle == NULL:
                raise IOError(
                    "Failed to create in-memory file using initial bytes.")

            if VSIFCloseL(vsi_handle) != 0:
                raise IOError(
                    "Failed to properly close in-memory file.")

    def exists(self):
        """Test if the in-memory file exists.

        Returns
        -------
        bool
            True if the in-memory file exists.
        """
        cdef VSILFILE *fp = NULL
        cdef const char *cypath = self.path

        with nogil:
            fp = VSIFOpenL(cypath, 'r')

        if fp != NULL:
            VSIFCloseL(fp)
            return True
        else:
            return False

    def __len__(self):
        """Length of the file's buffer in number of bytes.

        Returns
        -------
        int
        """
        return self.getbuffer().size

    def close(self):
        """Close MemoryFile and release allocated memory."""
        VSIUnlink(self.path)
        self._pos = 0
        self._initial_bytes = None
        self.closed = True

    def read(self, size=-1):
        """Read size bytes from MemoryFile."""
        cdef VSILFILE *fp = NULL
        # Return no bytes immediately if the position is at or past the
        # end of the file.
        length = len(self)

        if self._pos >= length:
            self._pos = length
            return b''

        if size == -1:
            size = length - self._pos
        else:
            size = min(size, length - self._pos)

        cdef unsigned char *buffer = <unsigned char *>CPLMalloc(size)
        cdef bytes result

        fp = VSIFOpenL(self.path, 'r')

        try:
            fp = exc_wrap_vsilfile(fp)
            if VSIFSeekL(fp, self._pos, 0) < 0:
                raise IOError(
                    "Failed to seek to offset %s in %s.",
                    self._pos, self.name)

            objects_read = VSIFReadL(buffer, 1, size, fp)
            result = <bytes>buffer[:objects_read]

        finally:
            VSIFCloseL(fp)
            CPLFree(buffer)

        self._pos += len(result)
        return result

    def seek(self, offset, whence=0):
        """Seek to position in MemoryFile."""
        if whence == 0:
            pos = offset
        elif whence == 1:
            pos = self._pos + offset
        elif whence == 2:
            pos = len(self) - offset
        if pos < 0:
            raise ValueError("negative seek position: {}".format(pos))
        if pos > len(self):
            raise ValueError("seek position past end of file: {}".format(pos))
        self._pos = pos
        return self._pos

    def tell(self):
        """Tell current position in MemoryFile."""
        return self._pos

    def write(self, data):
        """Write data bytes to MemoryFile"""
        cdef VSILFILE *fp = NULL
        cdef const unsigned char *view = <bytes>data
        n = len(data)

        if not self.exists():
            fp = exc_wrap_vsilfile(VSIFOpenL(self.path, 'w'))
        else:
            fp = exc_wrap_vsilfile(VSIFOpenL(self.path, 'r+'))
            if VSIFSeekL(fp, self._pos, 0) < 0:
                raise IOError(
                    "Failed to seek to offset %s in %s.", self._pos, self.name)

        result = VSIFWriteL(view, 1, n, fp)
        VSIFFlushL(fp)
        VSIFCloseL(fp)

        self._pos += result
        return result

    def getbuffer(self):
        """Return a view on bytes of the file."""
        cdef unsigned char *buffer = NULL
        cdef const char *path = NULL
        cdef vsi_l_offset buffer_len = 0
        cdef np.uint8_t [:] buff_view

        buffer = VSIGetMemFileBuffer(self.path, &buffer_len, 0)

        if buffer == NULL or buffer_len == 0:
            buff_view = np.array([], dtype='uint8')
        else:
            buff_view = <np.uint8_t[:buffer_len]>buffer
        return buff_view


cdef class DatasetWriterBase(DatasetReaderBase):
    # Read-write access to raster data and metadata.

    def __init__(self, path, mode, driver=None, width=None, height=None,
                 count=None, crs=None, transform=None, dtype=None, nodata=None,
                 gcps=None, **kwargs):
        """Initialize a DatasetWriterBase instance."""

        cdef char **options = NULL
        cdef char *key_c = NULL
        cdef char *val_c = NULL
        cdef const char *drv_name = NULL
        cdef GDALDriverH drv = NULL
        cdef GDALRasterBandH band = NULL
        cdef const char *fname = NULL

        # Validate write mode arguments.
        log.debug("Path: %s, mode: %s, driver: %s", path, mode, driver)
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

        self._init_dtype = np.dtype(dtype).name

        # Make and store a GDAL dataset handle.

        # Parse the path to determine if there is scheme-specific
        # configuration to be done.
        path, archive, scheme = parse_path(path)
        path = vsi_path(path, archive, scheme)

        if scheme and scheme != 'file':
            raise TypeError(
                "VFS '{0}' datasets can not be created or updated.".format(
                    scheme))

        name_b = path.encode('utf-8')
        fname = name_b

        if mode == 'w':

            _delete_dataset_if_exists(path)

            driver_b = driver.encode('utf-8')
            drv_name = driver_b
            try:
                drv = exc_wrap_pointer(GDALGetDriverByName(drv_name))

            except Exception as err:
                raise DriverRegistrationError(str(err))

            # Find the equivalent GDAL data type or raise an exception
            # We've mapped numpy scalar types to GDAL types so see
            # if we can crosswalk those.
            if self._init_dtype not in dtypes.dtype_rev:
                raise TypeError(
                    "Unsupported dtype: %s" % self._init_dtype)
            else:
                gdal_dtype = dtypes.dtype_rev.get(self._init_dtype)

            # Create a GDAL dataset handle.
            try:
                for k, v in kwargs.items():
                    # Skip items that are definitely *not* valid driver
                    # options.
                    if k.lower() in ['affine']:
                        continue

                    k, v = k.upper(), str(v).upper()

                    # Guard against block size that exceed image size.
                    if k == 'BLOCKXSIZE' and int(v) > width:
                        raise ValueError("blockxsize exceeds raster width.")
                    if k == 'BLOCKYSIZE' and int(v) > height:
                        raise ValueError("blockysize exceeds raster height.")

                    key_b = k.encode('utf-8')
                    val_b = v.encode('utf-8')
                    key_c = key_b
                    val_c = val_b
                    options = CSLSetNameValue(options, key_c, val_c)
                    log.debug(
                        "Option: %r", (k, CSLFetchNameValue(options, key_c)))

                self._hds = exc_wrap_pointer(
                    GDALCreate(drv, fname, width, height,
                               count, gdal_dtype, options))
            finally:
                if options != NULL:
                    CSLDestroy(options)

            if nodata is not None:

                if not in_dtype_range(nodata, dtype):
                    raise ValueError(
                        "Given nodata value, %s, is beyond the valid "
                        "range of its data type, %s." % (
                            nodata, dtype))

                # Broadcast the nodata value to all bands.
                for i in range(count):
                    band = self.band(i + 1)
                    try:
                        exc_wrap_int(
                            GDALSetRasterNoDataValue(band, nodata))
                    except Exception as err:
                        raise RasterioIOError(str(err))

        elif mode == 'r+':
            try:
                self._hds = exc_wrap_pointer(GDALOpenShared(fname, <GDALAccess>1))
            except CPLE_OpenFailedError as err:
                raise RasterioIOError(str(err))

        else:
            # Raise an exception if we have any other mode.
            raise ValueError("Invalid mode: '%s'", mode)

        self.name = path
        self.mode = mode
        self.driver = driver
        self.width = width
        self.height = height
        self._count = count
        self._init_nodata = nodata
        self._count = count
        self._crs = crs
        if transform is not None:
            self._transform = transform.to_gdal()
        self._gcps = None
        self._init_gcps = gcps
        self._closed = True
        self._dtypes = []
        self._nodatavals = []
        self._units = ()
        self._descriptions = ()
        self._options = kwargs.copy()

        if self.mode == 'w':
            if self._transform:
                self.write_transform(self._transform)
            if self._crs:
                self.set_crs(self._crs)
            if self._init_gcps:
                self.set_gcps(self._init_gcps, self.crs)

        drv = GDALGetDatasetDriver(self._hds)
        drv_name = GDALGetDriverShortName(drv)
        self.driver = drv_name.decode('utf-8')

        self._count = GDALGetRasterCount(self._hds)
        self.width = GDALGetRasterXSize(self._hds)
        self.height = GDALGetRasterYSize(self._hds)
        self.shape = (self.height, self.width)

        self._transform = self.read_transform()
        self._crs = self.read_crs()

        # touch self.meta
        _ = self.meta

        self.update_tags(ns='rio_creation_kwds', **kwargs)
        self._closed = False

    def __repr__(self):
        return "<%s RasterUpdater name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open',
            self.name,
            self.mode)

    def start(self):
        pass

    def stop(self):
        """Ends the dataset's life cycle"""
        if self._hds != NULL:
            GDALFlushCache(self._hds)
            GDALClose(self._hds)
        self._hds = NULL
        self._closed = True
        log.debug("Dataset %r has been stopped.", self)

    def set_crs(self, crs):
        """Writes a coordinate reference system to the dataset."""
        cdef char *proj_c = NULL
        cdef char *wkt = NULL
        cdef OGRSpatialReferenceH osr = NULL

        osr = OSRNewSpatialReference(NULL)
        if osr == NULL:
            raise ValueError("Null spatial reference")
        params = []

        log.debug("Input CRS: %r", crs)

        if isinstance(crs, dict):
            crs = CRS(crs)
        if isinstance(crs, CRS):
            # EPSG is a special case.
            init = crs.get('init')
            if init:
                auth, val = init.split(':')
                if auth.upper() == 'EPSG':
                    OSRImportFromEPSG(osr, int(val))
            else:
                for k, v in crs.items():
                    if v is True or (k in ('no_defs', 'wktext') and v):
                        params.append("+%s" % k)
                    else:
                        params.append("+%s=%s" % (k, v))
                proj = " ".join(params)
                log.debug("PROJ.4 to be imported: %r", proj)
                proj_b = proj.encode('utf-8')
                proj_c = proj_b
                OSRImportFromProj4(osr, proj_c)
        # Fall back for CRS strings like "EPSG:3857."
        elif isinstance(crs, str) or crs is None:
            if not crs:
                crs = ''
            proj_b = crs.encode('utf-8')
            proj_c = proj_b
            OSRSetFromUserInput(osr, proj_c)
        else:
            raise CRSError(
                "{!r} does not define a valid CRS".format(crs))

        # Fixup, export to WKT, and set the GDAL dataset's projection.
        OSRFixup(osr)
        OSRExportToWkt(osr, <char**>&wkt)
        wkt_b = wkt
        log.debug("Exported WKT: %s", wkt_b.decode('utf-8'))
        GDALSetProjection(self._hds, wkt)

        CPLFree(wkt)
        _safe_osr_release(osr)
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
                NotGeoreferencedWarning
            )

        cdef double gt[6]
        for i in range(6):
            gt[i] = transform[i]
        err = GDALSetGeoTransform(self._hds, gt)
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
        cdef GDALRasterBandH band = NULL
        cdef double nodataval
        cdef int success

        for i, val in zip(self.indexes, vals):
            band = self.band(i)
            if val is None:
                success = delete_nodata_value(band)
            else:
                nodataval = val
                success = GDALSetRasterNoDataValue(band, nodataval)
            if success:
                raise ValueError("Invalid nodata value: %r", val)
        self._nodatavals = vals

    property nodatavals:
        """A list by band of a dataset's nodata values.
        """

        def __get__(self):
            return self.get_nodatavals()

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
            if isinstance(window, tuple):
                window = Window.from_slices(*window, self.height, self.width)
            yoff = window.row_off
            xoff = window.col_off
            height = window.height
            width = window.width
        else:
            xoff = yoff = <int>0
            width = <int>self.width
            height = <int>self.height

        indexes_arr = np.array(indexes, dtype=int)
        indexes_count = <int>indexes_arr.shape[0]
        retval = io_multi_band(self._hds, 1, xoff, yoff, width, height,
                               src, indexes_arr)

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
        cdef GDALMajorObjectH hobj = NULL
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

        papszStrList = CSLDuplicate(
            GDALGetMetadata(hobj, domain_c))

        for key, value in kwargs.items():
            key_b = text_type(key).encode('utf-8')
            value_b = text_type(value).encode('utf-8')
            key_c = key_b
            value_c = value_b
            papszStrList = CSLSetNameValue(
                    papszStrList, key_c, value_c)

        retval = GDALSetMetadata(hobj, papszStrList, domain_c)
        if papszStrList != NULL:
            CSLDestroy(papszStrList)

        if retval == 2:
            log.warn("Tags accepted but may not be persisted.")
        elif retval == 3:
            raise RuntimeError("Tag update failed.")

    def set_description(self, bidx, value):
        """Sets the description of a dataset band.

        Parameters
        ----------
        bidx : int
            Index of the band (starting with 1).

        value: string
            A description of the band.

        Returns
        -------
        None
        """
        cdef GDALRasterBandH hband = NULL

        hband = self.band(bidx)
        GDALSetDescription(hband, value.encode('utf-8'))
        # Invalidate cached descriptions.
        self._descriptions = ()

    def set_units(self, bidx, value):
        """Sets the units of a dataset band.

        Parameters
        ----------
        bidx : int
            Index of the band (starting with 1).

        value: string
            A label for the band's units such as 'meters' or 'degC'.
            See the Pint project for a suggested list of units.

        Returns
        -------
        None
        """
        cdef GDALRasterBandH hband = NULL

        hband = self.band(bidx)
        GDALSetRasterUnitType(hband, value.encode('utf-8'))
        # Invalidate cached units.
        self._units = ()

    def write_colormap(self, bidx, colormap):
        """Write a colormap for a band to the dataset."""
        cdef GDALRasterBandH hBand = NULL
        cdef GDALColorTableH hTable = NULL
        cdef GDALColorEntry color

        hBand = self.band(bidx)

        # RGB only for now. TODO: the other types.
        # GPI_Gray=0,  GPI_RGB=1, GPI_CMYK=2,     GPI_HLS=3
        hTable = GDALCreateColorTable(1)
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
            GDALSetColorEntry(hTable, i, &color)

        # TODO: other color interpretations?
        GDALSetRasterColorInterpretation(hBand, 1)
        GDALSetRasterColorTable(hBand, hTable)
        GDALDestroyColorTable(hTable)

    def write_mask(self, mask_array, window=None):
        """Write the valid data mask src array into the dataset's band
        mask.

        The optional `window` argument takes a tuple like:

            ((row_start, row_stop), (col_start, col_stop))

        specifying a raster subset to write into.
        """
        cdef GDALRasterBandH band = NULL
        cdef GDALRasterBandH mask = NULL

        band = self.band(1)

        try:
            exc_wrap_int(GDALCreateMaskBand(band, 0x02))
            mask = exc_wrap_pointer(GDALGetMaskBand(band))
            log.debug("Created mask band")
        except:
            raise RasterioIOError("Failed to get mask.")

        if window:
            if isinstance(window, tuple):
                window = Window.from_slices(*window, self.height, self.width)
            yoff = window.row_off
            xoff = window.col_off
            height = window.height
            width = window.width
        else:
            xoff = yoff = 0
            width = self.width
            height = self.height

        if mask_array is True:
            GDALFillRaster(mask, 255, 0)
        elif mask_array is False:
            GDALFillRaster(mask, 0, 0)
        elif mask_array.dtype == np.bool:
            array = 255 * mask_array.astype(np.uint8)
            retval = io_band(mask, 1, xoff, yoff, width, height, array)
        else:
            retval = io_band(mask, 1, xoff, yoff, width, height, mask_array)

    def build_overviews(self, factors, resampling=Resampling.nearest):
        """Build overviews at one or more decimation factors for all
        bands of the dataset."""
        cdef int *factors_c = NULL
        cdef const char *resampling_c = NULL

        try:
            # GDALBuildOverviews() takes a string algo name, not a
            # Resampling enum member (like warping) and accepts only
            # a subset of the warp algorithms. 'NONE' is omitted below
            # (what does that even mean?) and so is 'AVERAGE_MAGPHASE'
            # (no corresponding member in the warp enum).
            resampling_map = {
                0: 'NEAREST',
                2: 'CUBIC',
                5: 'AVERAGE',
                6: 'MODE',
                7: 'GAUSS'}
            resampling_alg = resampling_map[Resampling(resampling.value)]
        except (KeyError, ValueError):
            raise ValueError(
                "resampling must be one of: {0}".format(", ".join(
                    ['Resampling.{0}'.format(Resampling(k).name) for k in
                     resampling_map.keys()])))

        # Allocate arrays.
        if factors:
            factors_c = <int *>CPLMalloc(len(factors)*sizeof(int))
            for i, factor in enumerate(factors):
                factors_c[i] = factor
            try:
                resampling_b = resampling_alg.encode('utf-8')
                resampling_c = resampling_b
                err = exc_wrap_int(
                    GDALBuildOverviews(self._hds, resampling_c,
                                       len(factors), factors_c, 0, NULL, NULL,
                                       NULL))
            finally:
                if factors_c != NULL:
                    CPLFree(factors_c)

    def set_gcps(self, gcps, crs=None):
        cdef char *srcwkt = NULL
        cdef GDAL_GCP *gcplist = <GDAL_GCP *>CPLMalloc(len(gcps) * sizeof(GDAL_GCP))

        try:
            for i, obj in enumerate(gcps):
                ident = str(i).encode('utf-8')
                info = "".encode('utf-8')
                gcplist[i].pszId = ident
                gcplist[i].pszInfo = info
                gcplist[i].dfGCPPixel = obj.col
                gcplist[i].dfGCPLine = obj.row
                gcplist[i].dfGCPX = obj.x
                gcplist[i].dfGCPY = obj.y
                gcplist[i].dfGCPZ = obj.z or 0.0

            # Try to use the primary crs if possible.
            if not crs:
                crs = self.crs

            osr = _osr_from_crs(crs)
            OSRExportToWkt(osr, <char**>&srcwkt)
            GDALSetGCPs(self.handle(), len(gcps), gcplist, srcwkt)
        finally:
            CPLFree(gcplist)
            CPLFree(srcwkt)

        # Invalidate cached value.
        self._gcps = None

    property gcps:
        """ground control points and their coordinate reference system.

        The value of this property is a 2-tuple, or pair: (gcps, crs).

        gcps: a sequence of GroundControlPoints
            Zero or more ground control points.
        crs: a CRS
            The coordinate reference system for ground control points.
        """
        def __get__(self):
            if not self._gcps:
                self._gcps = self.get_gcps()
            return self._gcps

        def __set__(self, values):
            self.set_gcps(values[0], values[1])



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

    def __cinit__(self, image=None, dtype='uint8', count=1, width=None,
                  height=None, transform=None, gcps=None, crs=None):
        """
        Create in-memory raster dataset, and fill its bands with the
        arrays in image.

        An empty in-memory raster with no memory allocated to bands,
        e.g. for use in _calculate_default_transform(), can be created
        by passing dtype, count, width, and height instead.

        :param image: 2D numpy array.  Must be of supported data type
        (see rasterio.dtypes.dtype_rev)
        :param transform: GDAL compatible transform array
        """

        self._image = image

        cdef int i = 0  # avoids Cython warning in for loop below
        cdef const char *srcwkt = NULL
        cdef OGRSpatialReferenceH osr = NULL
        cdef GDALDriverH mdriver = NULL
        cdef GDAL_GCP *gcplist = NULL

        if image is not None:
            if len(image.shape) == 3:
                count, height, width = image.shape
            elif len(image.shape) == 2:
                count = 1
                height, width = image.shape
            dtype = image.dtype.name

        self.band_ids[0] = 1

        memdriver = exc_wrap_pointer(GDALGetDriverByName("MEM"))
        datasetname = str(uuid.uuid4()).encode('utf-8')
        self._hds = exc_wrap_pointer(
            GDALCreate(memdriver, <const char *>datasetname, width, height,
                       count, <GDALDataType>dtypes.dtype_rev[dtype], NULL))

        if transform is not None:
            for i in range(6):
                self.transform[i] = transform[i]
            err = GDALSetGeoTransform(self._hds, self.transform)
            if err:
                raise ValueError("transform not set: %s" % transform)

            if crs:
                osr = _osr_from_crs(crs)
                OSRExportToWkt(osr, <char**>&srcwkt)
                GDALSetProjection(self._hds, srcwkt)
                log.debug("Set CRS on temp source dataset: %s", srcwkt)
                CPLFree(<void *>srcwkt)
                _safe_osr_release(osr)

        elif gcps and crs:
            gcplist = <GDAL_GCP *>CPLMalloc(len(gcps) * sizeof(GDAL_GCP))
            for i, obj in enumerate(gcps):
                ident = str(i).encode('utf-8')
                info = "".encode('utf-8')
                gcplist[i].pszId = ident
                gcplist[i].pszInfo = info
                gcplist[i].dfGCPPixel = obj.col
                gcplist[i].dfGCPLine = obj.row
                gcplist[i].dfGCPX = obj.x
                gcplist[i].dfGCPY = obj.y
                gcplist[i].dfGCPZ = obj.z or 0.0

            osr = _osr_from_crs(crs)
            OSRExportToWkt(osr, <char**>&srcwkt)
            GDALSetGCPs(self._hds, len(gcps), gcplist, srcwkt)
            CPLFree(gcplist)
            CPLFree(<void *>srcwkt)

        if self._image is not None:
            self.write(self._image)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    cdef GDALDatasetH handle(self) except NULL:
        """Return the object's GDAL dataset handle"""
        return self._hds

    cdef GDALRasterBandH band(self, int bidx) except NULL:
        """Return a GDAL raster band handle"""
        cdef GDALRasterBandH band = NULL

        try:
            band = exc_wrap_pointer(GDALGetRasterBand(self._hds, bidx))
        except CPLE_IllegalArgError as exc:
            raise IndexError(str(exc))

        # Don't get here.
        if band == NULL:
            raise ValueError("NULL band")

        return band

    def close(self):
        if self._hds != NULL:
            GDALClose(self._hds)
            self._hds = NULL

    def read(self):
        io_auto(self._image, self.band(1), False)
        return self._image

    def write(self, image):
        io_auto(image, self.band(1), True)


cdef class BufferedDatasetWriterBase(DatasetWriterBase):

    def __repr__(self):
        return "<%s IndirectRasterUpdater name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open',
            self.name,
            self.mode)

    def __init__(self, path, mode, driver=None, width=None, height=None,
                 count=None, crs=None, transform=None, dtype=None, nodata=None,
                 gcps=None, **kwargs):

        cdef char **options = NULL
        cdef char *key_c = NULL
        cdef char *val_c = NULL
        cdef GDALDriverH drv = NULL
        cdef GDALRasterBandH band = NULL
        cdef int success = -1
        cdef const char *fname = NULL
        cdef const char *drv_name = NULL
        cdef GDALDriverH memdrv = NULL
        cdef GDALDatasetH temp = NULL

        # Validate write mode arguments.

        log.debug("Path: %s, mode: %s, driver: %s", path, mode, driver)
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

        self._init_dtype = np.dtype(dtype).name

        self.name = path
        self.mode = mode
        self.driver = driver
        self.width = width
        self.height = height
        self._count = count
        self._init_nodata = nodata
        self._count = count
        self._crs = crs
        if transform is not None:
            self._transform = transform.to_gdal()
        self._gcps = None
        self._init_gcps = gcps
        self._closed = True
        self._dtypes = []
        self._nodatavals = []
        self._units = ()
        self._descriptions = ()
        self._options = kwargs.copy()

        # Make and store a GDAL dataset handle.

        # Parse the path to determine if there is scheme-specific
        # configuration to be done.
        path = vsi_path(*parse_path(path))
        name_b = path.encode('utf-8')

        memdrv = GDALGetDriverByName("MEM")

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

            self._hds = exc_wrap_pointer(
                GDALCreate(memdrv, "temp", self.width, self.height,
                           self._count, gdal_dtype, NULL))

            if self._init_nodata is not None:
                for i in range(self._count):
                    band = self.band(i+1)
                    success = GDALSetRasterNoDataValue(
                        band, self._init_nodata)
            if self._transform:
                self.write_transform(self._transform)
            if self._crs:
                self.set_crs(self._crs)
            if self._gcps:
                self.set_gcps(self._gcps, self._crs)

        elif self.mode == 'r+':
            try:
                temp = exc_wrap_pointer(GDALOpenShared(fname, <GDALAccess>0))
            except Exception as exc:
                raise RasterioIOError(str(exc))

            self._hds = exc_wrap_pointer(
                GDALCreateCopy(memdrv, "temp", temp, 1, NULL, NULL, NULL))

            drv = GDALGetDatasetDriver(temp)
            self.driver = get_driver_name(drv)
            GDALClose(temp)

        # Instead of calling _begin() we do the following.

        self._count = GDALGetRasterCount(self._hds)
        self.width = GDALGetRasterXSize(self._hds)
        self.height = GDALGetRasterYSize(self._hds)
        self.shape = (self.height, self.width)

        self._transform = self.read_transform()
        self._crs = self.read_crs()

        if options != NULL:
            CSLDestroy(options)

        # touch self.meta
        _ = self.meta

        self.update_tags(ns='rio_creation_kwds', **kwargs)
        self._closed = False

    def close(self):
        cdef const char *drv_name = NULL
        cdef char **options = NULL
        cdef char *key_c = NULL
        cdef char *val_c = NULL
        cdef GDALDriverH drv = NULL
        cdef GDALDatasetH temp = NULL
        cdef int success = -1
        cdef const char *fname = NULL

        name_b = self.name.encode('utf-8')
        fname = name_b

        # Delete existing file, create.
        _delete_dataset_if_exists(self.name)

        driver_b = self.driver.encode('utf-8')
        drv_name = driver_b
        drv = GDALGetDriverByName(drv_name)
        if drv == NULL:
            raise ValueError("NULL driver for %s", self.driver)

        # Creation options
        for k, v in self._options.items():
            # Skip items that are definitely *not* valid driver options.
            if k.lower() in ['affine']:
                continue
            k, v = k.upper(), str(v).upper()
            key_b = k.encode('utf-8')
            val_b = v.encode('utf-8')
            key_c = key_b
            val_c = val_b
            options = CSLSetNameValue(options, key_c, val_c)
            log.debug(
                "Option: %r\n",
                (k, CSLFetchNameValue(options, key_c)))

        try:
            temp = exc_wrap_pointer(
                GDALCreateCopy(drv, fname, self._hds, 1, options, NULL, NULL))
        finally:
            if options != NULL:
                CSLDestroy(options)
            if temp != NULL:
                GDALClose(temp)


def virtual_file_to_buffer(filename):
    """Read content of a virtual file into a Python bytes buffer."""
    cdef unsigned char *buff = NULL
    cdef const char *cfilename = NULL
    cdef vsi_l_offset buff_len = 0
    filename_b = filename if not isinstance(filename, string_types) else filename.encode('utf-8')
    cfilename = filename_b
    buff = VSIGetMemFileBuffer(cfilename, &buff_len, 0)
    n = buff_len
    log.debug("Buffer length: %d bytes", n)
    cdef np.uint8_t[:] buff_view = <np.uint8_t[:n]>buff
    return buff_view
