# The Numpy-free base classes.

# cython: boundscheck=False

import logging
import math
import sys
import warnings

from libc.stdlib cimport malloc, free

from rasterio cimport _gdal, _ogr
from rasterio._drivers import driver_count, GDALEnv
from rasterio._err import cpl_errs
from rasterio import dtypes
from rasterio.coords import BoundingBox
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


cdef class DatasetReader(object):

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
        cdef const char * auth_key = NULL
        cdef const char * auth_val = NULL
        cdef void *osr = NULL
        if self._hds == NULL:
            raise ValueError("Null dataset")
        crs = {}
        cdef const char * wkt = _gdal.GDALGetProjectionRef(self._hds)
        if wkt is NULL:
            raise ValueError("Unexpected NULL spatial reference")
        wkt_b = wkt
        if len(wkt_b) > 0:
            osr = _gdal.OSRNewSpatialReference(wkt)
            if osr == NULL:
                raise ValueError("Unexpected NULL spatial reference")
            log.debug("Got coordinate system")

            retval = _gdal.OSRAutoIdentifyEPSG(osr)
            if retval > 0:
                log.info("Failed to auto identify EPSG: %d", retval)
            
            auth_key = _gdal.OSRGetAuthorityName(osr, NULL)
            auth_val = _gdal.OSRGetAuthorityCode(osr, NULL)

            if auth_key != NULL and auth_val != NULL:
                key_b = auth_key
                key = key_b.decode('utf-8')
                if key == 'EPSG':
                    val_b = auth_val
                    val = val_b.decode('utf-8')
                    crs['init'] = "epsg:" + val
            else:
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
                        raise ValueError(
                            "Unexpected proj parameter %s" % param)
                    k = k.lstrip("+")
                    crs[k] = v

            _gdal.CPLFree(proj_c)
            _gdal.OSRDestroySpatialReference(osr)
        else:
            log.debug("GDAL dataset has no projection.")
        return crs

    def read_crs_wkt(self):
        cdef char *proj_c = NULL
        cdef char *key_c = NULL
        cdef void *osr = NULL
        cdef const char * wkt = NULL
        if self._hds == NULL:
            raise ValueError("Null dataset")
        wkt = _gdal.GDALGetProjectionRef(self._hds)
        if wkt is NULL:
            raise ValueError("Unexpected NULL spatial reference")
        wkt_b = wkt
        if len(wkt_b) > 0:
            osr = _gdal.OSRNewSpatialReference(wkt)
            log.debug("Got coordinate system")
            if osr != NULL:
                retval = _gdal.OSRAutoIdentifyEPSG(osr)
                if retval > 0:
                    log.info("Failed to auto identify EPSG: %d", retval)
                _gdal.OSRExportToWkt(osr, &proj_c)
                if proj_c == NULL:
                    raise ValueError("Null projection")
                proj_b = proj_c
                crs_wkt = proj_b.decode('utf-8')
                _gdal.CPLFree(proj_c)
                _gdal.OSRDestroySpatialReference(osr)
        else:
            log.debug("GDAL dataset has no projection.")
            crs_wkt = None
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

    def get_nodatavals(self):
        cdef void *hband = NULL
        cdef double nodataval
        cdef int success

        if not self._nodatavals:
            if self._hds == NULL:
                raise ValueError("can't read closed raster file")
            for i in range(self._count):
                hband = _gdal.GDALGetRasterBand(self._hds, i+1)
                if hband == NULL:
                    raise ValueError("Null band")
                nodataval = _gdal.GDALGetRasterNoDataValue(hband, &success)
                val = nodataval
                if not success:
                    val = None
                self._nodatavals.append(val)
        return self._nodatavals

    property nodatavals:
        """Nodata values for each band."""

        def __get__(self):
            return self.get_nodatavals()

    property nodata:
        """The dataset's single nodata value."""
        def __get__(self):
            return self.nodatavals[0]

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

    def index(self, x, y, op=math.floor):
        """Returns the (row, col) index of the pixel containing (x, y)."""
        return get_index(x, y, self.affine)

    def window(self, left, bottom, right, top, boundless=False):
        """Returns the window corresponding to the world bounding box.
        If boundless is False, window is limited to extent of this dataset."""

        window = get_window(left, bottom, right, top, self.affine)
        if boundless:
            return window
        else:
            return crop_window(window, self.height, self.width)

    def window_transform(self, window):
        """Returns the affine transform for a dataset window."""
        (r, _), (c, _) = window
        return self.affine * Affine.translation(c or 0, r or 0)

    def window_bounds(self, window):
        """Returns the bounds of a window as x_min, y_min, x_max, y_max."""
        ((row_min, row_max), (col_min, col_max)) = window
        x_min, y_min = (col_min, row_max) * self.affine
        x_max, y_max = (col_max, row_min) * self.affine
        return x_min, y_min, x_max, y_max

    @property
    def meta(self):
        """The basic metadata of this dataset."""
        m = {
            'driver': self.driver,
            'dtype': self.dtypes[0],
            'nodata': self.nodata,
            'width': self.width,
            'height': self.height,
            'count': self.count,
            'crs': self.crs,
            'transform': self.affine.to_gdal(),
            'affine': self.affine,
        }
        self._read = True
        return m


    property profile:
        """Basic metadata and creation options of this dataset.

        May be passed as keyword arguments to `rasterio.open()` to
        create a clone of this dataset.
        """
        def __get__(self):
            m = self.meta
            m.update(self.tags(ns='rio_creation_kwds'))
            m.update(
                blockxsize=self.block_shapes[0][1],
                blockysize=self.block_shapes[0][0],
                tiled=self.block_shapes[0][1] != self.width)
            return m


    def lnglat(self):
        w, s, e, n = self.bounds
        cx = (w + e)/2.0
        cy = (s + n)/2.0
        lng, lat = _transform(
                self.crs, {'init': 'epsg:4326'}, [cx], [cy], None)
        return lng.pop(), lat.pop()

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
            key, value = item.split('=', 1)
            retval[key] = value
        return retval
    
    def colorinterp(self, bidx):
        """Returns the color interpretation for a band or None."""
        cdef void *hBand
        
        if self._hds == NULL:
          raise ValueError("can't read closed raster file")
        if bidx not in self.indexes:
            raise ValueError("Invalid band index")
        hBand = _gdal.GDALGetRasterBand(self._hds, bidx)
        if hBand == NULL:
            raise ValueError("NULL band")
        value = _gdal.GDALGetRasterColorInterpretation(hBand)
        return ColorInterp(value)
    
    def colormap(self, bidx):
        """Returns a dict containing the colormap for a band or None."""
        cdef void *hBand
        cdef void *hTable
        cdef int i
        cdef const _gdal.GDALColorEntry * color
        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
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

    @property
    def kwds(self):
        return self.tags(ns='rio_creation_kwds')

    # Overviews.
    def overviews(self, bidx):
        cdef void *hovband = NULL
        cdef void *hband = self.band(bidx)
        num_overviews = _gdal.GDALGetOverviewCount(hband)
        factors = []
        for i in range(num_overviews):
            hovband = _gdal.GDALGetOverview(hband, i)
            # Compute the overview factor only from the xsize (width).
            xsize = _gdal.GDALGetRasterBandXSize(hovband)
            factors.append(int(round(float(self.width)/float(xsize))))
        return factors

    def checksum(self, bidx, window=None):
        """Compute an integer checksum for the stored band

        Parameters
        ----------
        bidx : int
            The band's index (1-indexed).
        window: tuple, optional
            A window of the band. Default is the entire extent of the band.

        Returns
        -------
        An int.
        """
        cdef void *hband = NULL
        cdef int xoff, yoff, width, height
        if self._hds == NULL:
            raise ValueError("can't read closed raster file")
        hband = _gdal.GDALGetRasterBand(self._hds, bidx)
        if hband == NULL:
            raise ValueError("NULL band")
        if not window:
            xoff = yoff = 0
            width, height = self.width, self.height
        else:
            window = eval_window(window, self.height, self.width)
            window = crop_window(window, self.height, self.width)
            xoff = window[1][0]
            width = window[1][1] - xoff
            yoff = window[0][0]
            height = window[0][1] - yoff
        return _gdal.GDALChecksumImage(hband, xoff, yoff, width, height)


# Window utils
# A window is a 2D ndarray indexer in the form of a tuple:
# ((row_start, row_stop), (col_start, col_stop))

cpdef crop_window(object window, int height, int width):
    """Returns a window cropped to fall within height and width."""
    cdef int r_start, r_stop, c_start, c_stop
    (r_start, r_stop), (c_start, c_stop) = window
    return (
        (min(max(r_start, 0), height), max(0, min(r_stop, height))),
        (min(max(c_start, 0), width), max(0, min(c_stop, width)))
    )


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


def get_index(x, y, affine, op=math.floor):
    """
    Returns the (row, col) index of the pixel containing (x, y) given a
    coordinate reference system.

    Parameters
    ----------
    x : float
        x value in coordinate reference system
    y : float
        y value in coordinate reference system
    affine : tuple
        Coefficients mapping pixel coordinates to coordinate reference system.
    op : function
        Function to convert fractional pixels to whole numbers (floor, ceiling, round)

    Returns
    -------
    row : int
        row index
    col : int
        col index
    """

    row = int(op((y - affine[5]) / affine[4]))
    col = int(op((x - affine[2]) / affine[0]))

    return row, col


def get_window(left, bottom, right, top, affine):
    """
    Returns a window tuple given coordinate bounds and the coordinate reference
    system.

    Parameters
    ----------
    left : float
        Left edge of window
    bottom : float
        Bottom edge of window
    right : float
        Right edge of window
    top : float
        top edge of window
    affine : tuple
        Coefficients mapping pixel coordinates to coordinate reference system.
    """

    EPS = 1.0e-8
    window_start = get_index(left + EPS, top - EPS, affine, op=math.floor)
    window_stop = get_index(right - EPS, bottom + EPS, affine, op=math.ceil)
    window = tuple(zip(window_start, window_stop))

    return window


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


cdef void *_osr_from_crs(object crs):
    cdef char *proj_c = NULL
    cdef void *osr = _gdal.OSRNewSpatialReference(NULL)
    params = []
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
    return osr


def _transform(src_crs, dst_crs, xs, ys, zs):
    cdef double *x = NULL
    cdef double *y = NULL
    cdef double *z = NULL
    cdef char *proj_c = NULL
    cdef void *src = NULL
    cdef void *dst = NULL
    cdef void *transform = NULL
    cdef int i

    assert len(xs) == len(ys)
    assert zs is None or len(xs) == len(zs)

    src = _osr_from_crs(src_crs)
    dst = _osr_from_crs(dst_crs)

    n = len(xs)
    x = <double *>_gdal.CPLMalloc(n*sizeof(double))
    y = <double *>_gdal.CPLMalloc(n*sizeof(double))
    for i in range(n):
        x[i] = xs[i]
        y[i] = ys[i]

    if zs is not None:
        z = <double *>_gdal.CPLMalloc(n*sizeof(double))
        for i in range(n):
            z[i] = zs[i]

    transform = _gdal.OCTNewCoordinateTransformation(src, dst)
    res = _gdal.OCTTransform(transform, n, x, y, z)
    #if res:
    #    raise ValueError("Failed coordinate transformation")

    res_xs = [0]*n
    res_ys = [0]*n

    for i in range(n):
        res_xs[i] = x[i]
        res_ys[i] = y[i]

    if zs is not None:
        res_zs = [0]*n
        for i in range(n):
            res_zs[i] = z[i]
        _gdal.CPLFree(z)

        retval = (res_xs, res_ys, res_zs)
    else:
        retval = (res_xs, res_ys)

    _gdal.CPLFree(x)
    _gdal.CPLFree(y)
    _gdal.OCTDestroyCoordinateTransformation(transform)
    _gdal.OSRDestroySpatialReference(src)
    _gdal.OSRDestroySpatialReference(dst)
    return retval


def is_geographic_crs(crs):
    cdef void *osr_crs = _osr_from_crs(crs)
    cdef int retval = _gdal.OSRIsGeographic(osr_crs)
    _gdal.OSRDestroySpatialReference(osr_crs)

    return retval == 1


def is_projected_crs(crs):
    cdef void *osr_crs = _osr_from_crs(crs)
    cdef int retval = _gdal.OSRIsProjected(osr_crs)
    _gdal.OSRDestroySpatialReference(osr_crs)

    return retval == 1


def is_same_crs(crs1, crs2):
    cdef void *osr_crs1 = _osr_from_crs(crs1)
    cdef void *osr_crs2 = _osr_from_crs(crs2)
    cdef int retval = _gdal.OSRIsSame(osr_crs1, osr_crs2)
    _gdal.OSRDestroySpatialReference(osr_crs1)
    _gdal.OSRDestroySpatialReference(osr_crs2)

    return retval == 1
