# cython: boundscheck=False, c_string_type=unicode, c_string_encoding=utf8

"""Numpy-free base classes."""

from __future__ import absolute_import

import logging
import math
import warnings

from rasterio._err import (
    GDALError, CPLE_IllegalArgError, CPLE_OpenFailedError,
    CPLE_NotSupportedError)
from rasterio._err cimport exc_wrap_pointer, exc_wrap_int

from rasterio.compat import string_types
from rasterio.control import GroundControlPoint
from rasterio.crs import CRS
from rasterio import dtypes
from rasterio.coords import BoundingBox
from rasterio.crs import CRS
from rasterio.enums import (
    ColorInterp, Compression, Interleaving, MaskFlags, PhotometricInterp)
from rasterio.env import Env
from rasterio.errors import (
    RasterioIOError, CRSError, DriverRegistrationError,
    NotGeoreferencedWarning, RasterioDeprecationWarning)
from rasterio.profiles import Profile
from rasterio.transform import Affine, guard_transform, tastes_like_gdal
from rasterio.vfs import parse_path, vsi_path
from rasterio import windows

include "gdal.pxi"


log = logging.getLogger(__name__)


def check_gdal_version(major, minor):
    """Return True if the major and minor versions match."""
    return bool(GDALCheckVersion(int(major), int(minor), NULL))


def gdal_version():
    """Return the version as a major.minor.patchlevel string."""
    return GDALVersionInfo("RELEASE_NAME")


cdef const char *get_driver_name(GDALDriverH driver):
    """Return Python name of the driver"""
    return GDALGetDriverShortName(driver)


def get_dataset_driver(path):
    """Return the name of the driver that would be used to open the
    dataset at the given path."""
    cdef GDALDatasetH dataset = NULL
    cdef GDALDriverH driver = NULL

    path = vsi_path(*parse_path(path))
    path = path.encode('utf-8')

    try:
        dataset = exc_wrap_pointer(GDALOpenShared(<const char *>path, <GDALAccess>0))
        driver = GDALGetDatasetDriver(dataset)
        drivername = get_driver_name(driver)

    except CPLE_OpenFailedError as exc:
        raise TypeError(str(exc))

    finally:
        if dataset != NULL:
            GDALClose(dataset)

    return drivername


def driver_supports_mode(drivername, creation_mode):
    """Return True if the driver supports the mode"""
    cdef GDALDriverH driver = NULL
    cdef char **metadata = NULL

    drivername = drivername.encode('utf-8')
    creation_mode = creation_mode.encode('utf-8')

    driver = GDALGetDriverByName(<const char *>drivername)
    if driver == NULL:
        raise DriverRegistrationError(
            "No such driver registered: %s", drivername)

    metadata = GDALGetMetadata(driver, NULL)
    if metadata == NULL:
        raise ValueError("Driver has no metadata")

    return bool(CSLFetchBoolean(metadata, <const char *>creation_mode, 0))


def driver_can_create(drivername):
    """Return True if the driver has CREATE capability"""
    return driver_supports_mode(drivername, 'DCAP_CREATE')


def driver_can_create_copy(drivername):
    """Return True if the driver has CREATE_COPY capability"""
    return driver_supports_mode(drivername, 'DCAP_CREATECOPY')


cdef class DatasetBase(object):
    """Dataset base class."""

    def __init__(self, path, options=None):
        self.name = path
        self.mode = 'r'
        self.options = options or {}
        self._hds = NULL
        self._count = 0
        self._closed = True
        self._dtypes = []
        self._block_shapes = None
        self._nodatavals = []
        self._units = ()
        self._descriptions = ()
        self._crs = None
        self._gcps = None
        self._read = False

    def __repr__(self):
        return "<%s DatasetBase name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open',
            self.name,
            self.mode)

    def start(self):
        """Called to start reading a dataset."""
        cdef GDALDriverH driver = NULL
        cdef GDALDatasetH hds = NULL
        cdef const char *cypath

        path = vsi_path(*parse_path(self.name))
        path = path.encode('utf-8')
        cypath = path

        try:
            with nogil:
                hds = GDALOpenShared(cypath, <GDALAccess>0)
            self._hds = exc_wrap_pointer(hds)
        except CPLE_OpenFailedError as err:
            raise RasterioIOError(err.errmsg)

        driver = GDALGetDatasetDriver(self._hds)
        self.driver = get_driver_name(driver)

        self._count = GDALGetRasterCount(self._hds)
        self.width = GDALGetRasterXSize(self._hds)
        self.height = GDALGetRasterYSize(self._hds)
        self.shape = (self.height, self.width)

        self._transform = self.read_transform()
        self._crs = self.read_crs()

        # touch self.meta
        _ = self.meta

        self._closed = False
        log.debug("Dataset %r is started.", self)

    cdef GDALDatasetH handle(self) except NULL:
        """Return the object's GDAL dataset handle"""
        return self._hds

    cdef GDALRasterBandH band(self, int bidx) except NULL:
        """Return a GDAL raster band handle"""
        cdef GDALRasterBandH band = NULL
        band = GDALGetRasterBand(self.handle(), bidx)
        if band == NULL:
            raise IndexError("No such band index: {!s}".format(bidx))
        return band

    def _has_band(self, bidx):
        cdef GDALRasterBandH band = NULL
        try:
            band = self.band(bidx)
            return True
        except:
            return False

    def _handle_crswkt(self, wkt):
        """Return the GDAL dataset's stored CRS"""
        cdef char *proj = NULL
        cdef OGRSpatialReferenceH osr = NULL
        wkt_b = wkt.encode('utf-8')
        cdef const char *wkt_c = wkt_b

        # Test that the WKT definition isn't just an empty string, which
        # can happen when the source dataset is not georeferenced.
        if len(wkt) > 0:
            crs = CRS()

            osr = OSRNewSpatialReference(wkt_c)
            if osr == NULL:
                raise ValueError("Unexpected NULL spatial reference")
            log.debug("Got coordinate system")

            # Try to find an EPSG code in the spatial referencing.
            if OSRAutoIdentifyEPSG(osr) == 0:
                key = OSRGetAuthorityName(osr, NULL)
                val = OSRGetAuthorityCode(osr, NULL)
                log.debug("Authority key: %s, value: %s", key, val)
                crs['init'] = u'epsg:' + val
            else:
                log.debug("Failed to auto identify EPSG")
                OSRExportToProj4(osr, &proj)
                if proj == NULL:
                    raise ValueError("Unexpected Null spatial reference")

                value = proj
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

            CPLFree(proj)
            OSRRelease(osr)
            return crs

        else:
            log.debug("No projection detected.")

    def read_crs(self):
        """Return the GDAL dataset's stored CRS"""
        cdef const char *wkt_b = GDALGetProjectionRef(self._hds)
        if wkt_b == NULL:
            raise ValueError("Unexpected NULL spatial reference")

        wkt = wkt_b
        return self._handle_crswkt(wkt)

    def read_transform(self):
        """Return the stored GDAL GeoTransform"""
        cdef double gt[6]

        if self._hds == NULL:
            raise ValueError("Null dataset")
        err = GDALGetGeoTransform(self._hds, gt)
        if err == GDALError.failure:
            warnings.warn(
                "Dataset has no geotransform set. Default transform "
                "will be applied (Affine.identity())", NotGeoreferencedWarning)

        return [gt[i] for i in range(6)]

    def stop(self):
        """Ends the dataset's life cycle"""
        if self._hds != NULL:
            GDALClose(self._hds)
        self._hds = NULL
        log.debug("Dataset %r has been stopped.", self)

    def close(self):
        self.stop()
        self._closed = True
        log.debug("Dataset %r has been closed.", self)

    def __enter__(self):
        log.debug("Entering Dataset %r context.", self)
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        log.debug("Exited Dataset %r context.", self)

    def __dealloc__(self):
        if self._hds != NULL:
            GDALClose(self._hds)

    @property
    def closed(self):
        return self._closed

    @property
    def count(self):
        if not self._count:
            if self._hds == NULL:
                raise ValueError("Can't read closed raster file")
            self._count = GDALGetRasterCount(self._hds)
        return self._count

    @property
    def indexes(self):
        return tuple(range(1, self.count+1))

    @property
    def dtypes(self):
        """Returns an ordered tuple of all band data types."""
        cdef GDALRasterBandH band = NULL

        if not self._dtypes:
            for i in range(self._count):
                band = self.band(i + 1)
                self._dtypes.append(
                    dtypes.dtype_fwd[GDALGetRasterDataType(band)])

        return tuple(self._dtypes)

    @property
    def block_shapes(self):
        """Returns an ordered list of block shapes for all bands.

        Shapes are tuples and have the same ordering as the dataset's
        shape: (count of image rows, count of image columns).
        """
        cdef GDALRasterBandH band = NULL
        cdef int xsize
        cdef int ysize

        if self._block_shapes is None:
            self._block_shapes = []

            for i in range(self._count):
                band = self.band(i + 1)
                GDALGetBlockSize(band, &xsize, &ysize)
                self._block_shapes.append((ysize, xsize))

        return tuple(self._block_shapes)

    def get_nodatavals(self):
        cdef GDALRasterBandH band = NULL
        cdef double nodataval
        cdef int success = 0

        if not self._nodatavals:

            for i in range(self._count):
                band = self.band(i + 1)
                dtype = dtypes.dtype_fwd[GDALGetRasterDataType(band)]
                nodataval = GDALGetRasterNoDataValue(band, &success)
                val = nodataval
                # GDALGetRasterNoDataValue() has two ways of telling you that
                # there's no nodata value. The success flag might come back
                # 0 (FALSE). Even if it comes back 1 (TRUE), you still need
                # to check that the return value is within the range of the
                # data type. If so, the band has a nodata value. If not,
                # there's no nodata value.
                if (success == 0 or
                        val < dtypes.dtype_ranges[dtype][0] or
                        val > dtypes.dtype_ranges[dtype][1]):
                    val = None
                log.debug(
                    "Nodata success: %d, Nodata value: %f", success, nodataval)
                self._nodatavals.append(val)

        return tuple(self._nodatavals)

    property nodatavals:
        """Nodata values for each band."""
        def __get__(self):
            return self.get_nodatavals()

    property nodata:
        """The dataset's single nodata value."""
        def __get__(self):
            if self.count == 0:
                return None
            return self.nodatavals[0]

    property _mask_flags:
        """Mask flags for each band."""
        def __get__(self):
            cdef GDALRasterBandH band = NULL
            return tuple(GDALGetMaskFlags(self.band(j)) for j in self.indexes)

    property mask_flag_enums:
        """Sets of flags describing the sources of band masks.

        all_valid: There are no invalid pixels, all mask values will be
            255. When used this will normally be the only flag set.
        per_dataset: The mask band is shared between all bands on the
            dataset.
        alpha: The mask band is actually an alpha band and may have
            values other than 0 and 255.
        nodata: Indicates the mask is actually being generated from
            nodata values (mutually exclusive of "alpha").

        Returns
        -------
        list [, list*]
            One list of rasterio.enums.MaskFlags members per band.

        Examples
        --------

        For a 3 band dataset that has masks derived from nodata values:

        >>> dataset.mask_flag_enums
        ([<MaskFlags.nodata: 8>], [<MaskFlags.nodata: 8>], [<MaskFlags.nodata: 8>])
        >>> band1_flags = dataset.mask_flag_enums[0]
        >>> rasterio.enums.MaskFlags.nodata in band1_flags
        True
        >>> rasterio.enums.MaskFlags.alpha in band1_flags
        False
        """
        def __get__(self):
            return tuple(
                [flag for flag in MaskFlags if x & flag.value]
                for x in self._mask_flags)

    property mask_flags:
        """Mask flags for each band."""
        def __get__(self):
            warnings.warn(
                "'mask_flags' is deprecated. Switch to 'mask_flag_enums'",
                RasterioDeprecationWarning,
                stacklevel=2)
            return self._mask_flags

    property descriptions:
        """Text descriptions for each band."""
        def __get__(self):
            if not self._descriptions:
                descr = [GDALGetDescription(self.band(j)) for j in self.indexes]
                self._descriptions = tuple((d or None) for d in descr)
            return self._descriptions

    property units:
        """Strings defining the units for each band.

        Possible values include 'meters' or 'degC'. See the Pint
        project for a suggested list of units.¬
        """
        def __get__(self):
            if not self._units:
                self._units = tuple(
                    GDALGetRasterUnitType(self.band(j)) for j in self.indexes)
            return self._units

    def block_windows(self, bidx=0):
        """Returns an iterator over a band's blocks and their corresponding
        windows.  Produces tuples like ``(block, window)``.  The primary use
        of this method is to obtain windows to pass to `read()` for highly
        efficient access to raster block data.

        The positional parameter `bidx` takes the index (starting at 1) of the
        desired band.  This iterator yields blocks "left to right" and "top to
        bottom" and is similar to Python's ``enumerate()`` in that the first
        element is the block index and the second is the dataset window.

        Blocks are built-in to a dataset and describe how pixels are grouped
        within each band and provide a mechanism for efficient I/O.  A window
        is a range of pixels within a single band defined by row start, row
        stop, column start, and column stop.  For example, ``((0, 2), (0, 2))``
        defines a ``2 x 2`` window at the upper left corner of a raster band.
        Blocks are referenced by an ``(i, j)`` tuple where ``(0, 0)`` would be
        a band's upper left block.

        Raster I/O is performed at the block level, so accessing a window
        spanning multiple rows in a striped raster requires reading each row.
        Accessing a ``2 x 2`` window at the center of a ``1800 x 3600`` image
        requires reading 2 rows, or 7200 pixels just to get the target 4.  The
        same image with internal ``256 x 256`` blocks would require reading at
        least 1 block (if the window entire window falls within a single block)
        and at most 4 blocks, or at least 512 pixels and at most 2048.

        Given an image that is ``512 x 512`` with blocks that are
        ``256 x 256``, its blocks and windows would look like:

            Blocks:

                    0       256     512
                  0 +--------+--------+
                    |        |        |
                    | (0, 0) | (0, 1) |
                    |        |        |
                256 +--------+--------+
                    |        |        |
                    | (1, 0) | (1, 1) |
                    |        |        |
                512 +--------+--------+


            Windows:

                UL: ((0, 256), (0, 256))
                UR: ((0, 256), (256, 512))
                LL: ((256, 512), (0, 256))
                LR: ((256, 512), (256, 512))


        Parameters
        ----------
        bidx : int
            The band index (using 1-based indexing) from which to extract
            windows. A value less than 1 uses the first band if all bands have
            homogeneous windows and raises an exception otherwise.

        Yields
        ------
        tuple
            ``(block, window)``
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
                yield (j, i), windows.Window(
                    col_off=col, row_off=row, width=width, height=height)

    property bounds:
        """Returns the lower left and upper right bounds of the dataset
        in the units of its coordinate reference system.

        The returned value is a tuple:
        (lower left x, lower left y, upper right x, upper right y)
        """
        def __get__(self):
            a, b, c, d, e, f, _, _, _ = self.transform
            return BoundingBox(c, f + e * self.height, c + a * self.width, f)

    property res:
        """Returns the (width, height) of pixels in the units of its
        coordinate reference system."""
        def __get__(self):
            a, b, c, d, e, f, _, _, _ = self.transform
            if b == d == 0:
                return a, -e
            else:
                return math.sqrt(a * a+ d * d), math.sqrt(b * b + e * e)

    @property
    def meta(self):
        """The basic metadata of this dataset."""
        if self.count == 0:
            dtype = 'float_'
        else:
            dtype = self.dtypes[0]
        m = {
            'driver': self.driver,
            'dtype': dtype,
            'nodata': self.nodata,
            'width': self.width,
            'height': self.height,
            'count': self.count,
            'crs': self.crs,
            'transform': self.transform,
        }
        self._read = True

        return m

    @property
    def compression(self):
        val = self.tags(ns='IMAGE_STRUCTURE').get('COMPRESSION')
        if val:
            # 'YCbCr JPEG' will be normalized to 'JPEG'
            val = val.split(' ')[-1]
            return Compression(val)
        else:
            return None

    @property
    def interleaving(self):
        val = self.tags(ns='IMAGE_STRUCTURE').get('INTERLEAVE')
        if val:
            return Interleaving(val)
        else:
            return None

    @property
    def photometric(self):
        val = self.tags(ns='IMAGE_STRUCTURE').get('SOURCE_COLOR_SPACE')
        if val:
            return PhotometricInterp(val)
        else:
            return None

    @property
    def is_tiled(self):
        if len(self.block_shapes) == 0:
            return False
        return self.block_shapes[0][1] != self.width

    property profile:
        """Basic metadata and creation options of this dataset.

        May be passed as keyword arguments to `rasterio.open()` to
        create a clone of this dataset.
        """
        def __get__(self):
            m = Profile(**self.meta)
            m.update((k, v.lower()) for k, v in self.tags(
                ns='rio_creation_kwds').items())
            if self.is_tiled:
                m.update(
                    blockxsize=self.block_shapes[0][1],
                    blockysize=self.block_shapes[0][0],
                    tiled=True)
            else:
                m.update(tiled=False)
            if self.compression:
                m['compress'] = self.compression.name
            if self.interleaving:
                m['interleave'] = self.interleaving.name
            if self.photometric:
                m['photometric'] = self.photometric.name

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

    def get_transform(self):
        """Returns a GDAL geotransform in its native form."""
        if not self._read and self._transform is None:
            self._transform = self.read_transform()
        return self._transform

    property transform:
        """An instance of ``affine.Affine``, which is a ``namedtuple`` with
        coefficients in the order ``(a, b, c, d, e, f)``.

        Coefficients of the affine transformation that maps ``col,row``
        pixel coordinates to ``x,y`` coordinates in the specified crs. The
        coefficients of the augmented matrix are:

          | x |   | a  b  c | | r |
          | y | = | d  e  f | | c |
          | 1 |   | 0  0  1 | | 1 |
        """
        def __get__(self):
            return Affine.from_gdal(*self.get_transform())

    property affine:
        """This property is deprecated.

        An instance of ``affine.Affine``. This property is a
        transitional feature: see the docstring of ``transform``
        (above) for more details.

        This property was added in ``0.9`` as a transitional feature to aid the
        transition of the `transform` parameter.  Rasterio ``1.0`` completes
        this transition by converting `transform` to an instance of
        ``affine.Affine()``.

        See the `transform`'s docstring for more information.

        See https://github.com/mapbox/rasterio/issues/86 for more details.
        """

        def __get__(self):
            with warnings.catch_warnings():
                warnings.simplefilter('always')
                warnings.warn(
                "'src.affine' is deprecated.  Please switch to "
                "'src.transform'. See "
                "https://github.com/mapbox/rasterio/issues/86 for details.",
                RasterioDeprecationWarning,
                stacklevel=2)
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
        cdef GDALMajorObjectH obj = NULL
        cdef char **metadata = NULL
        cdef const char *domain = NULL

        if bidx > 0:
            obj = self.band(bidx)
        else:
            obj = self._hds
        if ns:
            ns = ns.encode('utf-8')
            domain = ns

        metadata = GDALGetMetadata(obj, domain)
        num_items = CSLCount(metadata)
        return dict(metadata[i].split('=', 1) for i in range(num_items))

    def colorinterp(self, bidx):
        """Returns the color interpretation for a band or None."""
        cdef GDALRasterBandH band = NULL

        band = self.band(bidx)
        value = GDALGetRasterColorInterpretation(band)
        return ColorInterp(value)

    def colormap(self, bidx):
        """Returns a dict containing the colormap for a band or None."""
        cdef GDALRasterBandH band = NULL
        cdef GDALColorTableH colortable = NULL
        cdef GDALColorEntry *color = NULL
        cdef int i

        band = self.band(bidx)
        colortable = GDALGetRasterColorTable(band)
        if colortable == NULL:
            raise ValueError("NULL color table")
        retval = {}

        for i in range(GDALGetColorEntryCount(colortable)):
            color = <GDALColorEntry*>GDALGetColorEntry(colortable, i)
            if color == NULL:
                log.warn("NULL color at %d, skipping", i)
                continue
            log.info(
                "Color: (%d, %d, %d, %d)",
                color.c1, color.c2, color.c3, color.c4)
            retval[i] = (color.c1, color.c2, color.c3, color.c4)

        return retval

    @property
    def kwds(self):
        return self.tags(ns='rio_creation_kwds')

    # Overviews.
    def overviews(self, bidx):
        cdef GDALRasterBandH ovrband = NULL
        cdef GDALRasterBandH band = NULL

        band = self.band(bidx)
        num_overviews = GDALGetOverviewCount(band)
        factors = []

        for i in range(num_overviews):
            ovrband = GDALGetOverview(band, i)
            # Compute the overview factor only from the xsize (width).
            xsize = GDALGetRasterBandXSize(ovrband)
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
        cdef GDALRasterBandH band = NULL
        cdef int xoff, yoff, width, height

        band = self.band(bidx)
        if not window:
            xoff = yoff = 0
            width, height = self.width, self.height
        else:
            window = windows.evaluate(window, self.height, self.width)
            window = windows.crop(window, self.height, self.width)
            xoff = window[1][0]
            width = window[1][1] - xoff
            yoff = window[0][0]
            height = window[0][1] - yoff

        return GDALChecksumImage(band, xoff, yoff, width, height)

    def get_gcps(self):
        """Get GCPs and their associated CRS."""
        cdef const char *wkt_b = GDALGetGCPProjection(self.handle())
        if wkt_b == NULL:
            raise ValueError("Unexpected NULL spatial reference")
        wkt = wkt_b
        crs = self._handle_crswkt(wkt)

        cdef const GDAL_GCP *gcplist = NULL
        gcplist = GDALGetGCPs(self.handle())
        num_gcps = GDALGetGCPCount(self.handle())

        return ([GroundControlPoint(col=gcplist[i].dfGCPPixel,
                                         row=gcplist[i].dfGCPLine,
                                         x=gcplist[i].dfGCPX,
                                         y=gcplist[i].dfGCPY,
                                         z=gcplist[i].dfGCPZ,
                                         id=gcplist[i].pszId,
                                         info=gcplist[i].pszInfo)
                                         for i in range(num_gcps)], crs)

    property gcps:
        def __get__(self):
            if self._gcps is None:
                self._gcps = self.get_gcps()
            return self._gcps



def _transform(src_crs, dst_crs, xs, ys, zs):
    """Transform input arrays from src to dst CRS."""
    cdef double *x = NULL
    cdef double *y = NULL
    cdef double *z = NULL
    cdef OGRSpatialReferenceH src = NULL
    cdef OGRSpatialReferenceH dst = NULL
    cdef OGRCoordinateTransformationH transform = NULL
    cdef int i

    assert len(xs) == len(ys)
    assert zs is None or len(xs) == len(zs)

    src = _osr_from_crs(src_crs)
    dst = _osr_from_crs(dst_crs)

    n = len(xs)
    x = <double *>CPLMalloc(n*sizeof(double))
    y = <double *>CPLMalloc(n*sizeof(double))
    for i in range(n):
        x[i] = xs[i]
        y[i] = ys[i]

    if zs is not None:
        z = <double *>CPLMalloc(n*sizeof(double))
        for i in range(n):
            z[i] = zs[i]

    try:
        transform = OCTNewCoordinateTransformation(src, dst)
        transform = exc_wrap_pointer(transform)

        err = OCTTransform(transform, n, x, y, z)
        err = exc_wrap_int(err)

        res_xs = [0]*n
        res_ys = [0]*n
        for i in range(n):
            res_xs[i] = x[i]
            res_ys[i] = y[i]
        if zs is not None:
            res_zs = [0]*n
            for i in range(n):
                res_zs[i] = z[i]
            retval = (res_xs, res_ys, res_zs)
        else:
            retval = (res_xs, res_ys)

    except CPLE_NotSupportedError as exc:
        raise CRSError(exc.errmsg)

    finally:
        CPLFree(x)
        CPLFree(y)
        CPLFree(z)
        OSRRelease(src)
        OSRRelease(dst)

    return retval


cdef OGRSpatialReferenceH _osr_from_crs(object crs) except NULL:
    """Returns a reference to memory that must be deallocated
    by the caller."""
    if not crs:
        raise CRSError("A defined coordinate reference system is required")

    cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

    if isinstance(crs, string_types):
        proj = crs.encode('utf-8')

    # Make a CRS object from provided dict.
    else:
        crs = CRS(crs)
        # EPSG is a special case.
        init = crs.get('init')
        if init:
            auth, val = init.split(':')

            if not val:
                OSRRelease(osr)
                raise CRSError("Invalid CRS: {!r}".format(crs))

            if auth.upper() == 'EPSG':
                proj = 'EPSG:{}'.format(val).encode('utf-8')
        else:
            crs['wktext'] = True
            params = []
            for k, v in crs.items():
                if v is True or (k in ('no_defs', 'wktext') and v):
                    params.append("+%s" % k)
                else:
                    params.append("+%s=%s" % (k, v))
            proj = " ".join(params)
            log.debug("PROJ.4 to be imported: %r", proj)
            proj = proj.encode('utf-8')

    retval = OSRSetFromUserInput(osr, <const char *>proj)
    log.debug("OSRSetFromUserInput return value: %s", retval)

    if retval:
        OSRRelease(osr)
        raise CRSError("Invalid CRS: {!r}".format(crs))

    return osr


def _can_create_osr(crs):
    """Evaluate if a valid OGRSpatialReference can be created from crs.

    Specifically, it must not be None or an empty dict or string.

    Parameters
    ----------
    crs: Source coordinate reference system, in rasterio dict format.

    Returns
    -------
    out: bool
        True if source coordinate reference appears valid.
    """

    cdef char *wkt = NULL
    cdef OGRSpatialReferenceH osr = NULL

    try:
        # Note: _osr_from_crs() has "except NULL" in its signature.
        # It raises, it does not return NULL.
        osr = _osr_from_crs(crs)
        OSRExportToWkt(osr, &wkt)

        # If input was empty, WKT can be too; otherwise the conversion
        # didn't work properly and indicates an error.
        return wkt != NULL and bool(crs) == (wkt[0] != '\0')

    except CRSError:
        return False

    finally:
        OSRRelease(osr)
        CPLFree(wkt)
