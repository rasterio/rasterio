"""Classes capable of reading and writing datasets

Instances of these classes are called dataset objects.
"""

import math
import warnings

from rasterio._base import (
    get_dataset_driver, driver_can_create, driver_can_create_copy)
from rasterio._io import (
    DatasetReaderBase, DatasetWriterBase, BufferedDatasetWriterBase)
from rasterio import enums, windows
from rasterio.transform import guard_transform, xy, rowcol


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

    @property
    def mask_flag_enums(self):
        """Sets of flags describing the sources of band masks.

        Returns
        -------
        list [, list*]
            One list of rasterio.enums.MaskFlags members per band.

        Examples
        --------

        For a 3 band dataset that has masks derived from nodata values:

        >>> dataset = rasterio.open('tests/data/RGB.byte.tif')
        >>> dataset.mask_flag_enums
        ([<MaskFlags.nodata: 8>], [<MaskFlags.nodata: 8>], [<MaskFlags.nodata: 8>])
        >>> band1_flags = dataset.mask_flag_enums[0]
        >>> rio.enums.MaskFlags.nodata in band1_flags
        True
        >>> rio.enums.MaskFlags.alpha in band1_flags
        False

        """
        return tuple(
            [flag for flag in enums.MaskFlags if x & flag.value]
            for x in self.mask_flags)

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
