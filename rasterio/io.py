"""Classes capable of reading and writing datasets

Instances of these classes are called dataset objects.
"""


import logging
import math
import warnings

from rasterio._base import (
    get_dataset_driver, driver_can_create, driver_can_create_copy)
from rasterio._io import (
    DatasetReaderBase, DatasetWriterBase, BufferedDatasetWriterBase,
    MemoryFileBase)
from rasterio import windows
from rasterio.enums import Resampling
from rasterio.env import ensure_env
from rasterio.transform import guard_transform, xy, rowcol


log = logging.getLogger(__name__)


class TransformMethodsMixin(object):
    """Mixin providing methods for calculations related
    to transforming between rows and columns of the raster
    array and the coordinates.

    These methods are wrappers for the functionality in
    `rasterio.transform` module.

    A subclass with this mixin MUST provide a `transform`
    property.
    """

    def xy(self, row, col, offset="center"):
        """Returns the coordinates ``(x, y)`` of a pixel at `row` and `col`.
        The pixel's center is returned by default, but a corner can be returned
        by setting `offset` to one of `ul, ur, ll, lr`.

        Parameters
        ----------
        row : int
            Pixel row.
        col : int
            Pixel column.
        offset : str, optional
            Determines if the returned coordinates are for the center of the
            pixel or for a corner.

        Returns
        -------
        tuple
            ``(x, y)``
        """
        return xy(self.transform, row, col, offset=offset)

    def ul(self, row, col):
        """Returns the coordinates (x, y) of the upper left corner of a
        pixel at `row` and `col` in the units of the dataset's
        coordinate reference system.

        Deprecated; Use `xy(row, col, offset='ul')` instead.
        """
        warnings.warn("ul method is deprecated. Use xy(row, col, offset='ul')",
                      DeprecationWarning)
        return xy(self.transform, row, col, offset='ul')

    def index(self, x, y, op=math.floor, precision=6):
        """
        Returns the (row, col) index of the pixel containing (x, y) given a
        coordinate reference system.

        Use an epsilon, magnitude determined by the precision parameter
        and sign determined by the op function:
            positive for floor, negative for ceil.

        Parameters
        ----------
        x : float
            x value in coordinate reference system
        y : float
            y value in coordinate reference system
        op : function, optional (default: math.floor)
            Function to convert fractional pixels to whole numbers (floor,
            ceiling, round)
        precision : int, optional (default: 6)
            Decimal places of precision in indexing, as in `round()`.

        Returns
        -------
        tuple
            (row index, col index)
        """
        return rowcol(self.transform, x, y, op=op, precision=precision)


class WindowMethodsMixin(object):
    """Mixin providing methods for window-related calculations.
    These methods are wrappers for the functionality in
    `rasterio.windows` module.

    A subclass with this mixin MUST provide the following
    properties: `transform`, `height` and `width`
    """

    def window(self, left, bottom, right, top, boundless=False):
        """Get the window corresponding to the bounding coordinates.

        Parameters
        ----------
        left : float
            Left (west) bounding coordinate
        bottom : float
            Bottom (south) bounding coordinate
        right : float
            Right (east) bounding coordinate
        top : float
            Top (north) bounding coordinate
        boundless: boolean, optional
            If boundless is False, window is limited
            to extent of this dataset.

        Returns
        -------
        window: tuple
            ((row_start, row_stop), (col_start, col_stop))
            corresponding to the bounding coordinates

        """

        transform = guard_transform(self.transform)
        return windows.from_bounds(
            left, bottom, right, top, transform=transform,
            height=self.height, width=self.width, boundless=boundless)

    def window_transform(self, window):
        """Get the affine transform for a dataset window.

        Parameters
        ----------
        window: tuple
            Dataset window tuple

        Returns
        -------
        transform: Affine
            The affine transform matrix for the given window
        """

        transform = guard_transform(self.transform)
        return windows.transform(window, transform)

    def window_bounds(self, window):
        """Get the bounds of a window

        Parameters
        ----------
        window: tuple
            Dataset window tuple

        Returns
        -------
        bounds : tuple
            x_min, y_min, x_max, y_max for the given window
        """

        transform = guard_transform(self.transform)
        return windows.bounds(window, transform)


class DatasetReader(DatasetReaderBase, WindowMethodsMixin,
                    TransformMethodsMixin):
    """An unbuffered data and metadata reader"""

    def __repr__(self):
        return "<{} DatasetReader name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class DatasetWriter(DatasetWriterBase, WindowMethodsMixin,
                    TransformMethodsMixin):
    """An unbuffered data and metadata writer. Its methods write data
    directly to disk.
    """

    def __repr__(self):
        return "<{} DatasetWriter name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class BufferedDatasetWriter(BufferedDatasetWriterBase, WindowMethodsMixin,
                            TransformMethodsMixin):
    """Maintains data and metadata in a buffer, writing to disk or
    network only when `close()` is called.

    This allows incremental updates to datasets using formats that don't
    otherwise support updates, such as JPEG.
    """

    def __repr__(self):
        return "<{} BufferedDatasetWriter name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class MemoryFile(MemoryFileBase):
    """A BytesIO-like object, backed by an in-memory file.

    This allows formatted files to be read and written without I/O.

    A MemoryFile created with initial bytes becomes immutable. A
    MemoryFile created without initial bytes may be written to using
    either file-like or dataset interfaces.

    Examples
    --------

    A GeoTIFF can be loaded in memory and accessed using the GeoTIFF
    format driver

    >>> with open('tests/data/RGB.byte.tif', 'rb') as f, MemoryFile(f) as memfile:
    ...     with memfile.open() as src:
    ...         pprint.pprint(src.profile)
    ...
    {'count': 3,
     'crs': CRS({'init': 'epsg:32618'}),
     'driver': 'GTiff',
     'dtype': 'uint8',
     'height': 718,
     'interleave': 'pixel',
     'nodata': 0.0,
     'tiled': False,
     'transform': Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0),
     'width': 791}

    """
    def __init__(self, file_or_bytes=None, ext=''):
        super(MemoryFile, self).__init__(file_or_bytes=file_or_bytes, ext=ext)

    @ensure_env
    def open(self, driver=None, width=None, height=None, count=None, crs=None,
             transform=None, dtype=None, nodata=None, **kwargs):
        """Open the file and return a Rasterio dataset object.

        If data has already been written, the file is opened in 'r+'
        mode. Otherwise, the file is opened in 'w' mode.

        Parameters
        ----------
        Note well that there is no `path` parameter: a `MemoryFile`
        contains a single dataset and there is no need to specify a
        path.

        Other parameters are optional and have the same semantics as the
        parameters of `rasterio.open()`.
        """
        vsi_path = self.name

        if self.closed:
            raise IOError("I/O operation on closed file.")
        if self.exists():
            s = DatasetReader(vsi_path, 'r+')
        else:
            s = DatasetWriter(vsi_path, 'w', driver=driver, width=width,
                              height=height, count=count, crs=crs,
                              transform=transform, dtype=dtype,
                              nodata=nodata, **kwargs)
        s.start()
        return s

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()


class ZipMemoryFile(MemoryFile):
    """A read-only BytesIO-like object backed by an in-memory zip file.

    This allows a zip file containing formatted files to be read
    without I/O.
    """

    def __init__(self, file_or_bytes=None):
        super(ZipMemoryFile, self).__init__(file_or_bytes, ext='zip')

    @ensure_env
    def open(self, path):
        """Open a dataset within the zipped stream.

        Parameters
        ----------
        path : str
            Path to a dataset in the zip file, relative to the root of the
            archive.

        Returns
        -------
        A Rasterio dataset object
        """
        vsi_path = '/vsizip{0}/{1}'.format(self.name, path.lstrip('/'))

        if self.closed:
            raise IOError("I/O operation on closed file.")
        s = DatasetReader(vsi_path, 'r')
        s.start()
        return s


def get_writer_for_driver(driver):
    """Return the writer class appropriate for the specified driver."""
    cls = None
    if driver_can_create(driver):
        cls = DatasetWriter
    elif driver_can_create_copy(driver):  # pragma: no branch
        cls = BufferedDatasetWriter
    return cls


def get_writer_for_path(path):
    """Return the writer class appropriate for the existing dataset."""
    driver = get_dataset_driver(path)
    return get_writer_for_driver(driver)
