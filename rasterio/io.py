"""Classes capable of reading and writing datasets

Instances of these classes are called dataset objects.
"""

from rasterio._base import (
    get_dataset_driver, driver_can_create, driver_can_create_copy)
from rasterio._io import (
    DatasetReaderBase, DatasetWriterBase, BufferedDatasetWriterBase)
from rasterio.windows import (
    window, window_transform, window_bounds)


class WindowMethodsMixin(object):
    """Mixin providing methods for window-related calculations.
    These methods are wrappers for the functionality in
    `rasterio.windows` module.

    A subclass with this mixin MUST provide the following
    properties: `transform`, `height` and `width`
    """

    def window(self, left, bottom, right, top, boundless=False):
        """Returns the window corresponding to the bounding coordinates.
        If boundless is False, window is limited to extent of this dataset."""

        transform = self.affine  # TODO
        return window(transform, left, bottom, right, top,
                      height=self.height, width=self.width,
                      boundless=boundless)

    def window_transform(self, window):
        """Returns the affine transform for a dataset window."""

        transform = self.affine # TODO
        return window_transform(transform, window)

    def window_bounds(self, window):
        """Returns the bounds of a window as x_min, y_min, x_max, y_max."""

        transform = self.affine  # TODO
        return window_bounds(transform, window)


class DatasetReader(DatasetReaderBase, WindowMethodsMixin):
    """An unbuffered data and metadata reader"""

    def __repr__(self):
        return "<{} DatasetReader name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class DatasetWriter(DatasetWriterBase, WindowMethodsMixin):
    """An unbuffered data and metadata writer. Its methods write data
    directly to disk.
    """

    def __repr__(self):
        return "<{} DatasetWriter name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class BufferedDatasetWriter(BufferedDatasetWriterBase, WindowMethodsMixin):
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
