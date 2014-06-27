# cython: boundscheck(False)

import logging
import math
import os
import os.path
import sys
import warnings

from libc.stdlib cimport malloc, free
import numpy as np
cimport numpy as np

from rasterio cimport _gdal, _ogr, _io
from rasterio._drivers import driver_count, GDALEnv
from rasterio._err import cpl_errs
from rasterio import dtypes
from rasterio.coords import BoundingBox
from rasterio.five import text_type
from rasterio.transform import Affine

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
        np.ndarray[DTYPE_UBYTE_t, ndim=2, mode='c'] buffer):
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
        np.ndarray[DTYPE_UINT16_t, ndim=2, mode='c'] buffer):
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
        np.ndarray[DTYPE_INT16_t, ndim=2, mode='c'] buffer):
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
        np.ndarray[DTYPE_UINT32_t, ndim=2, mode='c'] buffer):
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
        np.ndarray[DTYPE_INT32_t, ndim=2, mode='c'] buffer):
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
        np.ndarray[DTYPE_FLOAT32_t, ndim=2, mode='c'] buffer):
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
        np.ndarray[DTYPE_FLOAT64_t, ndim=2, mode='c'] buffer):
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
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    1, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_uint16(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.uint16_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    2, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_int16(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.int16_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    3, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_uint32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.uint32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    4, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_int32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.int32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    5, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_float32(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.float32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    6, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_float64(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.float64_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buffer[i, 0, 0], buffer.shape[2], buffer.shape[1], 
                    7, 0, 0)
                if retval > 0:
                    break
    return retval

cdef int io_multi_cint16(
        void *hds,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height,
        np.int16_t[:, :] buf,
        int buf_width,
        int buf_height,
        long[:] indexes,
        int count) nogil:
    cdef int i, retval=0
    cdef void *hband = NULL
    with nogil:
        for i in range(count):
            hband = _gdal.GDALGetRasterBand(hds, <int>indexes[i])
            if hband == NULL:
                retval = 4
                break
            else:
                retval = _gdal.GDALRasterIO(
                    hband, mode, xoff, yoff, width, height,
                    &buf[i, 0], buf_width, buf_height,
                    8, 0, 0)
                if retval > 0:
                    break
    return retval

cdef void to_cint16(
        np.complex_t[:, :, :] out,
        np.int16_t[:, :] buf):
    cdef int I, J, K
    cdef int i, j, k
    cdef np.int16_t real, imag

    I = out.shape[0]
    J = out.shape[1]
    K = out.shape[2]
    for i in range(I):
        for j in range(J):
            for k in range(K):
                real = buf[i, 2*(j*K+k)]
                imag = buf[i, 2*(j*K+k)+1]
                out[i,j,k].real = real
                out[i,j,k].imag = imag

# Window utils
# A window is a 2D ndarray indexer in the form of a tuple:
# ((row_start, row_stop), (col_start, col_stop))

cpdef eval_window(object window, int height, int width):
    """Evaluates a window tuple that might contain negative values
    in the context of a raster height and width."""
    cdef int r_start, r_stop, c_start, c_stop
    try:
        r, c = window
        assert len(r) == 2
        assert len(c) == 2
    except (ValueError, TypeError, AssertionError):
        raise ValueError("invalid window structure; expecting "
                         "((row_start, row_stop), (col_start, col_stop))")
    r_start = r[0] or 0
    if r_start < 0:
        if height < 0:
            raise ValueError("invalid height: %d" % height)
        r_start += height
    r_stop = r[1] or height
    if r_stop < 0:
        if height < 0:
            raise ValueError("invalid height: %d" % height)
        r_stop += height
    if not r_stop >= r_start:
        raise ValueError(
            "invalid window: row range (%d, %d)" % (r_start, r_stop))
    c_start = c[0] or 0
    if c_start < 0:
        if width < 0:
            raise ValueError("invalid width: %d" % width)
        c_start += width
    c_stop = c[1] or width
    if c_stop < 0:
        if width < 0:
            raise ValueError("invalid width: %d" % width)
        c_stop += width
    if not c_stop >= c_start:
        raise ValueError(
            "invalid window: col range (%d, %d)" % (c_start, c_stop))
    return (r_start, r_stop), (c_start, c_stop)

def window_shape(window, height=-1, width=-1):
    """Returns shape of a window.

    height and width arguments are optional if there are no negative
    values in the window.
    """
    (a, b), (c, d) = eval_window(window, height, width)
    return b-a, d-c

def window_index(window):
    return tuple(slice(*w) for w in window)

def tastes_like_gdal(t):
    return t[2] == t[4] == 0.0 and t[1] > 0 and t[5] < 0


cdef class RasterReader(object):

    def __init__(self, path):
        self.name = path
        self.mode = 'r'
        self._hds = NULL
        self._count = 0
        self._closed = True
        self._dtypes = []
        self._block_shapes = None
        self._nodatavals = []
        self._crs = None
        self._crs_wkt = None
        self._read = False
        self.env = None
    
    def __repr__(self):
        return "<%s RasterReader name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open', 
            self.name,
            self.mode)

    def start(self):
        # Is there not a driver manager already?
        if driver_count() == 0 and not self.env:
            # create a local manager and enter
            self.env = GDALEnv(True)
        else:
            # create a local manager and enter
            self.env = GDALEnv(False)
        self.env.start()

        name_b = self.name.encode('utf-8')
        cdef const char *fname = name_b
        with cpl_errs:
            self._hds = _gdal.GDALOpen(fname, 0)
        if self._hds == NULL:
            raise ValueError("Null dataset")

        cdef void *drv
        cdef const char *drv_name
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

        # touch self.meta
        _ = self.meta

        self._closed = False

    cdef void *band(self, int bidx):
        if self._hds == NULL:
            raise ValueError("Null dataset")
        cdef void *hband = _gdal.GDALGetRasterBand(self._hds, bidx)
        if hband == NULL:
            raise ValueError("Null band")
        return hband

    def read_crs(self):
        cdef char *proj_c = NULL
        cdef void *osr = NULL
        if self._hds == NULL:
            raise ValueError("Null dataset")
        crs = {}
        cdef const char *proj = _gdal.GDALGetProjectionRef(self._hds)
        proj_b = proj
        if len(proj_b) > 0:
            osr = _gdal.OSRNewSpatialReference(proj)
            if osr == NULL:
                raise ValueError("Unexpected NULL spatial reference")
            log.debug("Got coordinate system")
            _gdal.OSRExportToProj4(osr, &proj_c)
            if proj_c == NULL:
                raise ValueError("Unexpected Null spatial reference")
            proj_b = proj_c
            log.debug("Params: %s", proj_b)
            value = proj_b.decode()
            value = value.strip()
            for param in value.split():
                kv = param.split("=")
                if len(kv) == 2:
                    k, v = kv
                    try:
                        v = float(v)
                        if v % 1 == 0:
                            v = int(v)
                    except ValueError:
                        # Leave v as a string
                        pass
                elif len(kv) == 1:
                    k, v = kv[0], True
                else:
                    raise ValueError("Unexpected proj parameter %s" % param)
                k = k.lstrip("+")
                crs[k] = v
            _gdal.CPLFree(proj_c)
            _gdal.OSRDestroySpatialReference(osr)
        else:
            log.debug("Projection not found (cogr_crs was NULL)")
        return crs

    def read_crs_wkt(self):
        cdef char *proj_c = NULL
        if self._hds == NULL:
            raise ValueError("Null dataset")
        cdef void *osr = _gdal.OSRNewSpatialReference(
            _gdal.GDALGetProjectionRef(self._hds))
        log.debug("Got coordinate system")
        crs = {}
        if osr != NULL:
            _gdal.OSRExportToWkt(osr, &proj_c)
            if proj_c == NULL:
                raise ValueError("Null projection")
            proj_b = proj_c
            crs_wkt = proj_b.decode('utf-8')
            _gdal.CPLFree(proj_c)
            _gdal.OSRDestroySpatialReference(osr)
        else:
            log.debug("Projection not found (cogr_crs was NULL)")
        return crs_wkt

    def read_transform(self):
        if self._hds == NULL:
            raise ValueError("Null dataset")
        cdef double gt[6]
        _gdal.GDALGetGeoTransform(self._hds, gt)
        transform = [0]*6
        for i in range(6):
            transform[i] = gt[i]
        return transform

    def stop(self):
        if self._hds != NULL:
            _gdal.GDALFlushCache(self._hds)
            _gdal.GDALClose(self._hds)
        if self.env:
            self.env.stop()
        self._hds = NULL

    def close(self):
        self.stop()
        self._closed = True
    
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __dealloc__(self):
        if self._hds != NULL:
            _gdal.GDALClose(self._hds)

    @property
    def closed(self):
        return self._closed

    @property
    def count(self):
        if not self._count:
            if self._hds == NULL:
                raise ValueError("Can't read closed raster file")
            self._count = _gdal.GDALGetRasterCount(self._hds)
        return self._count

    @property
    def indexes(self):
        return list(range(1, self.count+1))

    @property
    def dtypes(self):
        """Returns an ordered list of all band data types."""
        cdef void *hband = NULL
        if not self._dtypes:
            if self._hds == NULL:
                raise ValueError("can't read closed raster file")
            for i in range(self._count):
                hband = _gdal.GDALGetRasterBand(self._hds, i+1)
                self._dtypes.append(
                    dtypes.dtype_fwd[_gdal.GDALGetRasterDataType(hband)])
        return self._dtypes
    
    @property
    def block_shapes(self):
        """Returns an ordered list of block shapes for all bands.
        
        Shapes are tuples and have the same ordering as the dataset's
        shape: (count of image rows, count of image columns).
        """
        cdef void *hband = NULL
        cdef int xsize, ysize
        if self._block_shapes is None:
            if self._hds == NULL:
                raise ValueError("can't read closed raster file")
            self._block_shapes = []
            for i in range(self._count):
                hband = _gdal.GDALGetRasterBand(self._hds, i+1)
                if hband == NULL:
                    raise ValueError("Null band")
                _gdal.GDALGetBlockSize(hband, &xsize, &ysize)
                self._block_shapes.append((ysize, xsize))
        return self._block_shapes

    @property
    def nodatavals(self):
        """Returns a band-ordered list of nodata values."""
        cdef void *hband = NULL
        cdef object val
        cdef int success
        if not self._nodatavals:
            if self._hds == NULL:
                raise ValueError("can't read closed raster file")
            for i in range(self._count):
                hband = _gdal.GDALGetRasterBand(self._hds, i+1)
                if hband == NULL:
                    raise ValueError("Null band")
                val = _gdal.GDALGetRasterNoDataValue(hband, &success)
                if not success:
                    val = None
                self._nodatavals.append(val)
        return self._nodatavals

    def block_windows(self, bidx=0):
        """Returns an iterator over a band's block windows and their
        indexes.

        The positional parameter `bidx` takes the index (starting at 1)
        of the desired band. Block windows are tuples

            ((row_start, row_stop), (col_start, col_stop))

        For example, ((0, 2), (0, 2)) defines a 2 x 2 block at the upper
        left corner of the raster dataset.

        This iterator yields blocks "left to right" and "top to bottom"
        and is similar to Python's enumerate() in that it also returns
        indexes.

        The primary use of this function is to obtain windows to pass to
        read_band() for highly efficient access to raster block data.
        """
        cdef int i, j
        block_shapes = self.block_shapes
        if bidx < 1:
            if len(set(block_shapes)) > 1:
                raise ValueError(
                    "A band index must be provided when band block shapes"
                    "are inhomogeneous")
            bidx = 1
        h, w = block_shapes[bidx-1]
        d, m = divmod(self.height, h)
        nrows = d + int(m>0)
        d, m = divmod(self.width, w)
        ncols = d + int(m>0)
        for j in range(nrows):
            row = j * h
            height = min(h, self.height - row)
            for i in range(ncols):
                col = i * w
                width = min(w, self.width - col)
                yield (j, i), ((row, row+height), (col, col+width))

    property bounds:
        """Returns the lower left and upper right bounds of the dataset
        in the units of its coordinate reference system.
        
        The returned value is a tuple:
        (lower left x, lower left y, upper right x, upper right y)
        """
        def __get__(self):
            a, b, c, d, e, f, _, _, _ = self.affine
            return BoundingBox(c, f+e*self.height, c+a*self.width, f)
    
    property res:
        """Returns the (width, height) of pixels in the units of its
        coordinate reference system."""
        def __get__(self):
            a, b, c, d, e, f, _, _, _ = self.affine
            if b == d == 0:
                return a, -e
            else:
                return math.sqrt(a*a+d*d), math.sqrt(b*b+e*e)

    def ul(self, row, col):
        """Returns the coordinates (x, y) of the upper left corner of a 
        pixel at `row` and `col` in the units of the dataset's
        coordinate reference system.
        """
        a, b, c, d, e, f, _, _, _ = self.affine
        if col < 0:
            col += self.width
        if row < 0:
            row += self.height
        return c+a*col, f+e*row

    def index(self, x, y):
        """Returns the (row, col) index of the pixel containing (x, y)."""
        a, b, c, d, e, f, _, _, _ = self.affine
        return int(round((y-f)/e)), int(round((x-c)/a))

    def window(self, left, bottom, right, top):
        """Returns the window corresponding to the world bounding box."""
        ul = self.index(left, top)
        lr = self.index(right, bottom)
        if ul[0] < 0 or ul[1] < 0 or lr[0] > self.height or lr[1] > self.width:
            raise ValueError("Bounding box overflows the dataset extents")
        else:
            return tuple(zip(ul, lr))

    @property
    def meta(self):
        m = {
            'driver': self.driver,
            'dtype': self.dtypes[0],
            'nodata': self.nodatavals[0],
            'width': self.width,
            'height': self.height,
            'count': self.count,
            'crs': self.crs,
            'transform': self.affine.to_gdal(),
            'affine': self.affine }
        self._read = True
        return m

    def get_crs(self):
        # _read tells us that the CRS was read before and really is
        # None.
        if not self._read and self._crs is None:
            self._crs = self.read_crs()
        return self._crs

    property crs:
        """A mapping of PROJ.4 coordinate reference system params.
        """
        def __get__(self):
            return self.get_crs()

    property crs_wkt:
        """An OGC WKT string representation of the coordinate reference
        system.
        """
        def __get__(self):
            if not self._read and self._crs_wkt is None:
                self._crs = self.read_crs_wkt()
            return self._crs_wkt

    def get_transform(self):
        """Returns a GDAL geotransform in its native form."""
        if not self._read and self._transform is None:
            self._transform = self.read_transform()
        return self._transform

    property transform:
        """Coefficients of the affine transformation that maps col,row
        pixel coordinates to x,y coordinates in the specified crs. The
        coefficients of the augmented matrix are shown below.
        
          | x |   | a  b  c | | r |
          | y | = | d  e  f | | c |
          | 1 |   | 0  0  1 | | 1 |
        
        In Rasterio versions before 1.0 the value of this property
        is a list of coefficients ``[c, a, b, f, d, e]``. This form
        is *deprecated* beginning in 0.9 and in version 1.0 this 
        property will be replaced by an instance of ``affine.Affine``,
        which is a namedtuple with coefficients in the order
        ``(a, b, c, d, e, f)``.

        Please see https://github.com/mapbox/rasterio/issues/86
        for more details.
        """
        def __get__(self):
            warnings.warn(
                    "The value of this property will change in version 1.0. "
                    "Please see https://github.com/mapbox/rasterio/issues/86 "
                    "for details.",
                    FutureWarning,
                    stacklevel=2)
            return self.get_transform()

    property affine:
        """An instance of ``affine.Affine``. This property is a
        transitional feature: see the docstring of ``transform``
        (above) for more details.
        """
        def __get__(self):
            return Affine.from_gdal(*self.get_transform())

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
        cdef void *hband = NULL
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
            io_buffer = np.empty(
                (out.shape[0], 2*out.shape[2]*out.shape[1]), dtype=np.int16)
            retval = io_multi_cint16(
                            self._hds, 0, xoff, yoff, width, height,
                            io_buffer, out.shape[2], out.shape[1],
                            indexes_arr, indexes_count)
            to_cint16(out, io_buffer)

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

    def tags(self, bidx=0, ns=None):
        """Returns a dict containing copies of the dataset or band's
        tags.

        Tags are pairs of key and value strings. Tags belong to
        namespaces.  The standard namespaces are: default (None) and
        'IMAGE_STRUCTURE'.  Applications can create their own additional
        namespaces.

        The optional bidx argument can be used to select the tags of
        a specific band. The optional ns argument can be used to select
        a namespace other than the default.
        """
        cdef char *item_c
        cdef void *hobj
        cdef const char *domain_c
        cdef char **papszStrList
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
        papszStrList = _gdal.GDALGetMetadata(hobj, domain_c)
        num_items = _gdal.CSLCount(papszStrList)
        retval = {}
        for i in range(num_items):
            item_c = papszStrList[i]
            item_b = item_c
            item = item_b.decode('utf-8')
            key, value = item.split('=')
            retval[key] = value
        return retval

    def colormap(self, bidx):
        """Returns a dict containing the colormap for a band or None."""
        cdef void *hBand
        cdef void *hTable
        cdef int i
        cdef _gdal.GDALColorEntry *color
        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
        if bidx > 0:
            if bidx not in self.indexes:
                raise ValueError("Invalid band index")
            hBand = _gdal.GDALGetRasterBand(self._hds, bidx)
            if hBand == NULL:
                raise ValueError("NULL band")
        hTable = _gdal.GDALGetRasterColorTable(hBand)
        if hTable == NULL:
            raise ValueError("NULL color table")
        retval = {}

        for i in range(_gdal.GDALGetColorEntryCount(hTable)):
            color = _gdal.GDALGetColorEntry(hTable, i)
            if color == NULL:
                log.warn("NULL color at %d, skipping", i)
                continue
            log.info("Color: (%d, %d, %d, %d)", color.c1, color.c2, color.c3, color.c4)
            retval[i] = (color.c1, color.c2, color.c3, color.c4)
        return retval

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

    @property
    def kwds(self):
        return self.tags(ns='rio_creation_kwds')


cdef class RasterUpdater(RasterReader):
    # Read-write access to raster data and metadata.
    # TODO: the r+ mode.

    def __init__(
            self, path, mode, driver=None,
            width=None, height=None, count=None, 
            crs=None, transform=None, dtype=None,
            nodata=None,
            **kwargs):
        self.name = path
        self.mode = mode
        self.driver = driver
        self.width = width
        self.height = height
        self._count = count
        self._init_dtype = dtype
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
                self.write_crs(self._crs)
        
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

    def write_crs(self, crs):
        if self._hds == NULL:
            raise ValueError("Can't read closed raster file")
        cdef void *osr = _gdal.OSRNewSpatialReference(NULL)
        if osr == NULL:
            raise ValueError("Null spatial reference")
        params = []
        for k, v in crs.items():
            if v is True or (k == 'no_defs' and v):
                params.append("+%s" % k)
            else:
                params.append("+%s=%s" % (k, v))
        proj = " ".join(params)
        proj_b = proj.encode()
        cdef const char *proj_c = proj_b
        _gdal.OSRImportFromProj4(osr, proj_c)
        cdef char *wkt
        _gdal.OSRExportToWkt(osr, &wkt)
        _gdal.GDALSetProjection(self._hds, wkt)
        _gdal.CPLFree(wkt)
        _gdal.OSRDestroySpatialReference(osr)
        self._crs = crs

    property crs:
        """A mapping of PROJ.4 coordinate reference system params.
        """

        def __get__(self):
            return self.get_crs()

        def __set__(self, value):
            self.write_crs(value)

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

    def write_band(self, bidx, src, window=None):
        """Write the src array into the `bidx` band.

        Band indexes begin with 1: read_band(1) returns the first band.

        The optional `window` argument takes a tuple like:
        
            ((row_start, row_stop), (col_start, col_stop))

        specifying a raster subset to write into.
        """
        if bidx not in self.indexes:
            raise IndexError("band index out of range")
        i = self.indexes.index(bidx)
        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
        if src is not None and src.dtype != self.dtypes[i]:
            raise ValueError(
                "the array's dtype '%s' does not match "
                "the file's dtype '%s'" % (src.dtype, self.dtypes[i]))
        
        cdef void *hband = _gdal.GDALGetRasterBand(self._hds, bidx)
        if hband == NULL:
            raise ValueError("NULL band")
        
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
        dtype = self.dtypes[i]
        if dtype == dtypes.ubyte:
            retval = io_ubyte(
                hband, 1, xoff, yoff, width, height, src)
        elif dtype == dtypes.uint16:
            retval = io_uint16(
                hband, 1, xoff, yoff, width, height, src)
        elif dtype == dtypes.int16:
            retval = io_int16(
                hband, 1, xoff, yoff, width, height, src)
        elif dtype == dtypes.uint32:
            retval = io_uint32(
                hband, 1, xoff, yoff, width, height, src)
        elif dtype == dtypes.int32:
            retval = io_int32(
                hband, 1, xoff, yoff, width, height, src)
        elif dtype == dtypes.float32:
            retval = io_float32(
                hband, 1, xoff, yoff, width, height, src)
        elif dtype == dtypes.float64:
            retval = io_float64(
                hband, 1, xoff, yoff, width, height, src)
        else:
            raise ValueError("Invalid dtype")
        # TODO: handle errors (by retval).

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
        cdef char *key_c, *value_c
        cdef void *hobj
        cdef const char *domain_c
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
        cdef char **papszStrList = _gdal.GDALGetMetadata(hobj, domain_c)
        for key, value in kwargs.items():
            key_b = text_type(key).encode('utf-8')
            value_b = text_type(value).encode('utf-8')
            key_c = key_b
            value_c = value_b
            i = _gdal.CSLFindName(papszStrList, key_c)
            if i < 0:
                papszStrList = _gdal.CSLAddNameValue(papszStrList, key_c, value_c)
            else:
                papszStrList = _gdal.CSLSetNameValue(papszStrList, key_c, value_c)
        retval = _gdal.GDALSetMetadata(hobj, papszStrList, domain_c)

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

