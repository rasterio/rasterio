# cython: boundscheck=False, c_string_type=unicode, c_string_encoding=utf8

"""Numpy-free base classes."""

from __future__ import absolute_import

from collections import defaultdict
import logging
import math
import os
import warnings
from libc.string cimport strncmp

from rasterio._err import (
    GDALError, CPLE_BaseError, CPLE_IllegalArgError, CPLE_OpenFailedError,
    CPLE_NotSupportedError)
from rasterio._err cimport exc_wrap_pointer, exc_wrap_int
from rasterio._shim cimport open_dataset, osr_get_name, osr_set_traditional_axis_mapping_strategy

from rasterio.compat import string_types
from rasterio.control import GroundControlPoint
from rasterio import dtypes
from rasterio.coords import BoundingBox
from rasterio.crs import CRS
from rasterio.enums import (
    ColorInterp, Compression, Interleaving, MaskFlags, PhotometricInterp)
from rasterio.env import Env, env_ctx_if_needed
from rasterio.errors import (
    DatasetAttributeError,
    RasterioIOError, CRSError, DriverRegistrationError, NotGeoreferencedWarning,
    RasterBlockError, BandOverviewError)
from rasterio.profiles import Profile
from rasterio.transform import Affine, guard_transform, tastes_like_gdal
from rasterio.path import parse_path, vsi_path
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
    """Return the name of the driver that opens a dataset

    Parameters
    ----------
    path : rasterio.path.Path
        A remote or local dataset path.

    Returns
    -------
    str
    """
    cdef GDALDatasetH dataset = NULL
    cdef GDALDriverH driver = NULL

    path = vsi_path(path)
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

cdef _band_dtype(GDALRasterBandH band):
    """Resolve dtype of a given band, deals with signed/unsigned byte ambiguity"""
    cdef const char * ptype
    cdef int gdal_dtype = GDALGetRasterDataType(band)
    if gdal_dtype == GDT_Byte:
        # Can be uint8 or int8, need to check PIXELTYPE property
        ptype = GDALGetMetadataItem(band, 'PIXELTYPE', 'IMAGE_STRUCTURE')
        if ptype and strncmp(ptype, 'SIGNEDBYTE', 10) == 0:
            return 'int8'
        else:
            return 'uint8'

    return dtypes.dtype_fwd[gdal_dtype]


cdef class DatasetBase(object):
    """Dataset base class

    Attributes
    ----------
    block_shapes
    bounds
    closed
    colorinterp
    count
    crs
    descriptions
    files
    gcps
    indexes
    mask_flag_enums
    meta
    nodata
    nodatavals
    profile
    res
    subdatasets
    transform
    units
    compression : str
        Compression algorithm's short name
    driver : str
        Format driver used to open the dataset
    interleaving : str
        'pixel' or 'band'
    kwds : dict
        Stored creation option tags
    mode : str
        Access mode
    name : str
        Remote or local dataset name
    options : dict
        Copy of opening options
    photometric : str
        Photometric interpretation's short name
    """

    def __init__(self, path=None, driver=None, sharing=True, **kwargs):
        """Construct a new dataset

        Parameters
        ----------
        path : rasterio.path.Path
            Path of the local or remote dataset.
        driver : str or list of str
            A single driver name or a list of driver names to consider when
            opening the dataset.
        sharing : bool, optional
            Whether to share underlying GDAL dataset handles (default: True).
        kwargs : dict
            GDAL dataset opening options.

        Returns
        -------
        dataset
        """
        cdef GDALDatasetH hds = NULL
        cdef int flags = 0
        cdef int sharing_flag = (0x20 if sharing else 0x0)

        log.debug("Sharing flag: %r", sharing_flag)

        self._hds = NULL

        if path is not None:
            filename = vsi_path(path)

            # driver may be a string or list of strings. If the
            # former, we put it into a list.
            if isinstance(driver, string_types):
                driver = [driver]

            # Read-only + Rasters + Sharing + Errors
            flags = 0x00 | 0x02 | sharing_flag | 0x40

            try:
                self._hds = open_dataset(filename, flags, driver, kwargs, None)
            except CPLE_BaseError as err:
                raise RasterioIOError(str(err))

        self.name = path.name
        self.mode = 'r'
        self.options = kwargs.copy()
        self._dtypes = []
        self._block_shapes = None
        self._nodatavals = []
        self._units = ()
        self._descriptions = ()
        self._scales = ()
        self._offsets = ()
        self._gcps = None
        self._read = False

        self._set_attrs_from_dataset_handle()

    def __repr__(self):
        return "<%s DatasetBase name='%s' mode='%s'>" % (
            self.closed and 'closed' or 'open',
            self.name,
            self.mode)

    def _set_attrs_from_dataset_handle(self):
        cdef GDALDriverH driver = NULL
        driver = GDALGetDatasetDriver(self._hds)
        self.driver = get_driver_name(driver)
        self._count = GDALGetRasterCount(self._hds)
        self.width = GDALGetRasterXSize(self._hds)
        self.height = GDALGetRasterYSize(self._hds)
        self.shape = (self.height, self.width)
        self._transform = self.read_transform()
        self._crs = self.read_crs()

        # touch self.meta, triggering data type evaluation.
        _ = self.meta

        self._closed = False
        log.debug("Dataset %r is started.", self)

    cdef GDALDatasetH handle(self) except NULL:
        """Return the object's GDAL dataset handle"""
        if self._hds == NULL:
            raise RasterioIOError("Dataset is closed: {}".format(self.name))
        else:
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
        # No dialect morphing, if the dataset was created using software
        # "speaking" the Esri dialect, we will read Esri WKT.
        if wkt:
            return CRS.from_wkt(wkt)
        else:
            return None

    def read_crs(self):
        """Return the GDAL dataset's stored CRS"""
        cdef const char *wkt_b = GDALGetProjectionRef(self.handle())
        wkt = wkt_b
        if wkt == NULL:
            raise ValueError("Unexpected NULL spatial reference")
        return self._handle_crswkt(wkt)

    def read_transform(self):
        """Return the stored GDAL GeoTransform"""
        cdef double gt[6]

        if self._hds == NULL:
            raise ValueError("Null dataset")
        err = GDALGetGeoTransform(self._hds, gt)
        if err == GDALError.failure:
            warnings.warn(
                "Dataset has no geotransform set. The identity matrix may be returned.",
                NotGeoreferencedWarning)

        return [gt[i] for i in range(6)]

    def stop(self):
        """Ends the dataset's life cycle"""
        if self._hds != NULL:
            GDALClose(self._hds)
        self._hds = NULL

    def close(self):
        self.stop()
        self._closed = True

    def __enter__(self):
        self._env = env_ctx_if_needed()
        self._env.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self._env.__exit__()
        self.close()

    def __dealloc__(self):
        if self._hds != NULL:
            GDALClose(self._hds)

    @property
    def closed(self):
        """Test if the dataset is closed

        Returns
        -------
        bool
        """
        return self._closed

    @property
    def count(self):
        """The number of raster bands in the dataset

        Returns
        -------
        int
        """
        if not self._count:
            if self._hds == NULL:
                raise ValueError("Can't read closed raster file")
            self._count = GDALGetRasterCount(self._hds)
        return self._count

    @property
    def indexes(self):
        """The 1-based indexes of each band in the dataset

        For a 3-band dataset, this property will be ``[1, 2, 3]``.

        Returns
        -------
        list of int
        """
        return tuple(range(1, self.count+1))

    @property
    def dtypes(self):
        """The data types of each band in index order

        Returns
        -------
        list of str
        """
        cdef GDALRasterBandH band = NULL

        if not self._dtypes:
            for i in range(self._count):
                band = self.band(i + 1)
                self._dtypes.append(_band_dtype(band))

        return tuple(self._dtypes)

    @property
    def block_shapes(self):
        """An ordered list of block shapes for each bands

        Shapes are tuples and have the same ordering as the dataset's
        shape: (count of image rows, count of image columns).

        Returns
        -------
        list
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

        return list(self._block_shapes)

    def get_nodatavals(self):
        cdef GDALRasterBandH band = NULL
        cdef double nodataval
        cdef int success = 0

        if not self._nodatavals:

            for i in range(self._count):
                band = self.band(i + 1)
                dtype = _band_dtype(band)
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
        """Nodata values for each band

        Notes
        -----
        This may not be set.

        Returns
        -------
        list of float
        """
        def __get__(self):
            return self.get_nodatavals()

    def _set_nodatavals(self, value):
        raise DatasetAttributeError("read-only attribute")

    property nodata:
        """The dataset's single nodata value

        Notes
        -----
        May be set.

        Returns
        -------
        float
        """

        def __get__(self):
            if self.count == 0:
                return None
            return self.nodatavals[0]

        def __set__(self, value):
            self._set_nodatavals([value for old_val in self.nodatavals])

    def _mask_flags(self):
        """Mask flags for each band."""
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
                for x in self._mask_flags())

    def _set_crs(self, value):
        raise DatasetAttributeError("read-only attribute")

    property crs:
        """The dataset's coordinate reference system

        In setting this property, the value may be a CRS object or an
        EPSG:nnnn or WKT string.

        Returns
        -------
        CRS
        """

        def __get__(self):
            return self._get_crs()

        def __set__(self, value):
            self._set_crs(value)

    def _set_all_descriptions(self, value):
        raise DatasetAttributeError("read-only attribute")

    def _set_all_scales(self, value):
        raise DatasetAttributeError("read-only attribute")

    def _set_all_offsets(self, value):
        raise DatasetAttributeError("read-only attribute")

    def _set_all_units(self, value):
        raise DatasetAttributeError("read-only attribute") 

    property descriptions:
        """Descriptions for each dataset band

        To set descriptions, one for each band is required.

        Returns
        -------
        list of str
        """
        def __get__(self):
            if not self._descriptions:
                descr = [GDALGetDescription(self.band(j)) for j in self.indexes]
                self._descriptions = tuple((d or None) for d in descr)
            return self._descriptions

        def __set__(self, value):
            self._set_all_descriptions(value)

    def write_transform(self, value):
        raise DatasetAttributeError("read-only attribute")

    property transform:
        """The dataset's georeferencing transformation matrix

        This transform maps pixel row/column coordinates to coordinates
        in the dataset's coordinate reference system.

        Returns
        -------
        Affine
        """

        def __get__(self):
            return Affine.from_gdal(*self.get_transform())

        def __set__(self, value):
            self.write_transform(value.to_gdal())

    property offsets:
        """Raster offset for each dataset band

        To set offsets, one for each band is required.

        Returns
        -------
        list of float
        """
        def __get__(self):
            cdef int success = 0
            if not self._offsets:
                offsets = [GDALGetRasterOffset(self.band(j), &success) for j in self.indexes]
                self._offsets = tuple(offsets)
            return self._offsets

        def __set__(self, value):
            self._set_all_offsets(value)

    property scales:
        """Raster scale for each dataset band

        To set scales, one for each band is required.

        Returns
        -------
        list of float
        """
        def __get__(self):
            cdef int success = 0
            if not self._scales:
                scales = [GDALGetRasterScale(self.band(j), &success) for j in self.indexes]
                self._scales = tuple(scales)
            return self._scales

        def __set__(self, value):
            self._set_all_scales(value)

    property units:
        """A list of str: one units string for each dataset band

        Possible values include 'meters' or 'degC'. See the Pint
        project for a suggested list of units.

        To set units, one for each band is required.

        Returns
        -------
        list of str
        """
        def __get__(self):
            if not self._units:
                units = [GDALGetRasterUnitType(self.band(j)) for j in self.indexes]
                self._units = tuple((u or None) for u in units)
            return self._units

        def __set__(self, value):
            self._set_all_units(value)

    def block_window(self, bidx, i, j):
        """Returns the window for a particular block

        Parameters
        ----------
        bidx: int
            Band index, starting with 1.
        i: int
            Row index of the block, starting with 0.
        j: int
            Column index of the block, starting with 0.

        Returns
        -------
        Window
        """
        h, w = self.block_shapes[bidx-1]
        row = i * h
        height = min(h, self.height - row)
        col = j * w
        width = min(w, self.width - col)
        return windows.Window(col, row, width, height)

    def block_size(self, bidx, i, j):
        """Returns the size in bytes of a particular block

        Only useful for TIFF formatted datasets.

        Parameters
        ----------
        bidx: int
            Band index, starting with 1.
        i: int
            Row index of the block, starting with 0.
        j: int
            Column index of the block, starting with 0.

        Returns
        -------
        int
        """
        cdef GDALMajorObjectH obj = NULL
        cdef char *value = NULL
        cdef const char *key_c = NULL

        obj = self.band(bidx)

        key_b = 'BLOCK_SIZE_{0}_{1}'.format(j, i).encode('utf-8')
        key_c = key_b
        value = GDALGetMetadataItem(obj, key_c, 'TIFF')
        if value == NULL:
            raise RasterBlockError(
                "Block i={0}, j={1} size can't be determined".format(i, j))
        else:
            return int(value)

    def block_windows(self, bidx=0):
        """Iterator over a band's blocks and their windows


        The primary use of this method is to obtain windows to pass to
        `read()` for highly efficient access to raster block data.

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
        ``256 x 256``, its blocks and windows would look like::

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
        bidx : int, optional
            The band index (using 1-based indexing) from which to extract
            windows. A value less than 1 uses the first band if all bands have
            homogeneous windows and raises an exception otherwise.

        Yields
        ------
        block, window
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

        # We could call self.block_window() inside the loops but this
        # is faster and doesn't duplicate much code.
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
            width = self.width
            height = self.height
            if b == d == 0:
                return BoundingBox(c, f + e * height, c + a * width, f)
            else:
                c0x, c0y = c, f
                c1x, c1y = self.transform * (0, height)
                c2x, c2y = self.transform * (width, height)
                c3x, c3y = self.transform * (width, 0)
                xs = (c0x, c1x, c2x, c3x)
                ys = (c0y, c1y, c2y, c3y)
                return BoundingBox(min(xs), min(ys), max(xs), max(ys))

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
        return self.block_shapes[0][1] < self.width and self.block_shapes[0][1] <= 1024

    property profile:
        """Basic metadata and creation options of this dataset.

        May be passed as keyword arguments to `rasterio.open()` to
        create a clone of this dataset.
        """
        def __get__(self):
            m = Profile(**self.meta)

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

    def _get_crs(self):
        # _read tells us that the CRS was read before and really is
        # None.
        if not self._read and self._crs is None:
            self._crs = self.read_crs()
        return self._crs

    def get_transform(self):
        """Returns a GDAL geotransform in its native form."""
        if not self._read and self._transform is None:
            self._transform = self.read_transform()
        return self._transform

    property subdatasets:
        """Sequence of subdatasets"""

        def __get__(self):
            tags = self.tags(ns='SUBDATASETS')
            subs = defaultdict(dict)
            for key, val in tags.items():
                _, idx, fld = key.split('_')
                fld = fld.lower()
                if fld == 'desc':
                    fld = 'description'
                if fld == 'name':
                    val = val.replace('NETCDF', 'netcdf')
                subs[idx][fld] = val.replace('"', '')
            return [subs[idx]['name'] for idx in sorted(subs.keys())]


    def get_tag_ns(self, bidx=0):
        """Returns the list of metadata domains.
        
        The optional bidx argument can be used to select a specific band.
        """
        cdef GDALMajorObjectH obj = NULL
        if bidx > 0:
            obj = self.band(bidx)
        else:
            obj = self._hds

        namespaces = GDALGetMetadataDomainList(obj)
        num_items = CSLCount(namespaces)
        try:
            return list([namespaces[i] for i in range(num_items)])
        finally:
            CSLDestroy(namespaces)


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
        cdef char *key = NULL
        cdef char *val = NULL

        if bidx > 0:
            obj = self.band(bidx)
        else:
            obj = self._hds
        if ns:
            ns = ns.encode('utf-8')
            domain = ns

        metadata = GDALGetMetadata(obj, domain)
        num_items = CSLCount(metadata)

        tag_items = []
        for i in range(num_items):
            val = CPLParseNameValue(metadata[i], &key)
            tag_items.append((key[:], val[:]))
            CPLFree(key)

        return dict(tag_items)


    def get_tag_item(self, ns, dm=None, bidx=0, ovr=None):
        """Returns tag item value

        Parameters
        ----------
        ns: str
            The key for the metadata item to fetch.
        dm: str
            The domain to fetch for.
        bidx: int
            Band index, starting with 1.
        ovr: int
            Overview level

        Returns
        -------
        str
        """
        cdef GDALMajorObjectH band = NULL
        cdef GDALMajorObjectH obj = NULL
        cdef char *value = NULL
        cdef const char *name = NULL
        cdef const char *domain = NULL

        ns = ns.encode('utf-8')
        name = ns

        if dm:
            dm = dm.encode('utf-8')
            domain = dm

        if not bidx > 0 and ovr:
            raise Exception("Band index (bidx) option needed for overview level")

        if bidx > 0:
            band = self.band(bidx)
        else:
            band = self._hds

        if ovr is not None:
            obj = GDALGetOverview(band, ovr)
            if obj == NULL:
              raise BandOverviewError(
                  "Failed to retrieve overview {}".format(ovr))
        else:
            obj = band

        value = GDALGetMetadataItem(obj, name, domain)
        if value == NULL:
            return None
        else:
            return value


    property colorinterp:

        """Returns a sequence of ``ColorInterp.<enum>`` representing
        color interpretation in band order.

        To set color interpretation, provide a sequence of
        ``ColorInterp.<enum>``:

            import rasterio
            from rasterio.enums import ColorInterp

            with rasterio.open('rgba.tif', 'r+') as src:
                src.colorinterp = (
                    ColorInterp.red,
                    ColorInterp.green,
                    ColorInterp.blue,
                    ColorInterp.alpha)

        Returns
        -------
        tuple
        """

        def __get__(self):

            """A sequence of ``ColorInterp.<enum>`` in band order.

            Returns
            -------
            tuple
            """

            cdef GDALRasterBandH band = NULL

            out = []
            for bidx in self.indexes:
                value = exc_wrap_int(
                    GDALGetRasterColorInterpretation(self.band(bidx)))
                out.append(ColorInterp(value))
            return tuple(out)

        def __set__(self, value):

            """Set band color interpretation with a sequence of
            ``ColorInterp.<enum>`` in band order.

            Parameters
            ----------
            value : iter
                A sequence of ``ColorInterp.<enum>``.
            """
            if self.mode == 'r':
                raise RasterioIOError(
                    "Can only set color interpretation when dataset is "
                    "opened in 'r+' or 'w' mode, not '{}'.".format(self.mode))
            if len(value) != len(self.indexes):
                raise ValueError(
                    "Must set color interpretation for all bands.  Found "
                    "{} bands but attempting to set color interpretation to: "
                    "{}".format(len(self.indexes), value))

            for bidx, ci in zip(self.indexes, value):
                exc_wrap_int(
                    GDALSetRasterColorInterpretation(self.band(bidx), <GDALColorInterp>ci.value))

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
            xoff = window.col_off
            width = window.width
            yoff = window.row_off
            height = window.height

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

    def _set_gcps(self, values):
        raise DatasetAttributeError("read-only attribute")

    property gcps:
        """ground control points and their coordinate reference system.

        This property is a 2-tuple, or pair: (gcps, crs).

        gcps : list of GroundControlPoint
            Zero or more ground control points.
        crs: CRS
            The coordinate reference system of the ground control points.
        """
        def __get__(self):
            if not self._gcps:
                self._gcps = self.get_gcps()
            return self._gcps

        def __set__(self, value):
            gcps, crs = value
            self._set_gcps(gcps, crs)

    property files:

        """Returns a sequence of files associated with the dataset.

        Returns
        -------
        tuple
        """

        def __get__(self):
            cdef GDALDatasetH h_dataset = NULL
            h_dataset = self.handle()
            with nogil:
                file_list = GDALGetFileList(h_dataset)
            num_items = CSLCount(file_list)
            try:
                return list([file_list[i] for i in range(num_items)])
            finally:
                CSLDestroy(file_list)


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
        exc_wrap_int(OCTTransform(transform, n, x, y, z))

    except CPLE_BaseError as exc:
        log.debug("{}".format(exc))

    except:
        CPLFree(x)
        CPLFree(y)
        CPLFree(z)
        _safe_osr_release(src)
        _safe_osr_release(dst)

    try:
        res_xs = [0]*n
        res_ys = [0]*n
        for i in range(n):
            res_xs[i] = x[i]
            res_ys[i] = y[i]
        if zs is not None:
            res_zs = [0]*n
            for i in range(n):
                res_zs[i] = z[i]
            return (res_xs, res_ys, res_zs)
        else:
            return (res_xs, res_ys)

    finally:
        CPLFree(x)
        CPLFree(y)
        CPLFree(z)
        _safe_osr_release(src)
        _safe_osr_release(dst)


cdef OGRSpatialReferenceH _osr_from_crs(object crs) except NULL:
    """Returns a reference to memory that must be deallocated
    by the caller."""
    crs = CRS.from_user_input(crs)

    # EPSG is a special case.
    init = crs.get('init')
    if init:
        auth, val = init.strip().split(':')

        if not val or auth.upper() != 'EPSG':
            raise CRSError("Invalid CRS: {!r}".format(crs))
        proj = 'EPSG:{}'.format(val).encode('utf-8')
    else:
        proj = crs.to_string().encode('utf-8')
        log.debug("PROJ.4 to be imported: %r", proj)

    cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)
    try:
        retval = exc_wrap_int(OSRSetFromUserInput(osr, <const char *>proj))
        if retval:
            _safe_osr_release(osr)
            raise CRSError("Invalid CRS: {!r}".format(crs))
    except CPLE_BaseError as exc:
        _safe_osr_release(osr)
        raise CRSError(str(exc))
    else:
        if not gdal_version().startswith("3"):
            exc_wrap_int(OSRMorphFromESRI(osr))
        osr_set_traditional_axis_mapping_strategy(osr)
        return osr


cdef _safe_osr_release(OGRSpatialReferenceH srs):
    """Wrapper to handle OSR release when NULL."""

    if srs != NULL:
        OSRRelease(srs)
    srs = NULL


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
        _safe_osr_release(osr)
        CPLFree(wkt)
