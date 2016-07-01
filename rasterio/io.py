"""Classes capable of reading and writing datasets

Instances of these classes are called dataset objects.
"""

from rasterio._base import (
    get_dataset_driver, driver_can_create, driver_can_create_copy)
from rasterio._io import (
    DatasetReaderBase, DatasetWriterBase, BufferedDatasetWriterBase)
from rasterio.windows import (
    window, window_transform, window_bounds)


class DatasetCommonBase(object):
    # TODO do we copy the function signature here or
    #     just take *args, **kwargs
    # TODO get docstring from base function or copy

    def window(self, left, bottom, right, top, boundless=False):
        # TODO switch to transform
        return window(self.affine, left, bottom, right, top,
                      height=self.height, width=self.width,
                      boundless=boundless)

    def window_transform(self, window):
        """Returns the affine transform for a dataset window."""
        # TODO switch to transform
        transform = self.affine
        return window_transform(transform, window)

    def window_bounds(self, window):
        """Returns the bounds of a window as x_min, y_min, x_max, y_max."""
        # TODO switch to transform
        transform = self.affine
        return window_bounds(transform, window)


class DatasetReader(DatasetReaderBase, DatasetCommonBase):
    """An unbuffered data and metadata reader"""

    def __repr__(self):
        return "<{} DatasetReader name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class DatasetWriter(DatasetWriterBase, DatasetCommonBase):
    """An unbuffered data and metadata writer. Its methods write data
    directly to disk.
    """

    def __repr__(self):
        return "<{} DatasetWriter name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class BufferedDatasetWriter(BufferedDatasetWriterBase, DatasetCommonBase):
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
