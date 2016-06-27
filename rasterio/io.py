"""Classes capable of reading and writing datasets

Instances of these classes are called dataset objects.
"""

from rasterio._base import (
    get_dataset_driver, driver_can_create, driver_can_create_copy)
from rasterio._io import (
    RasterReaderBase, RasterUpdaterBase, IndirectRasterWriterBase)


class RasterDataReader(RasterReaderBase):
    """An unbuffered data and metadata reader"""

    def __repr__(self):
        return "<{} RasterDataReader name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class RasterDataWriter(RasterUpdaterBase):
    """An unbuffered data and metadata writer. Its methods write data
    directly to disk.
    """

    def __repr__(self):
        return "<{} RasterDataWriter name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class BufferedRasterDataWriter(IndirectRasterWriterBase):
    """Maintains data and metadata in a buffer, writing to disk or
    network only when `close()` is called.

    This allows incremental updates to datasets using formats that don't
    otherwise support updates, such as JPEG.
    """

    def __repr__(self):
        return "<{} BufferedRasterDataWriter name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


def get_writer_for_driver(driver):
    """Return the writer class appropriate for the specified driver."""
    cls = None
    if driver_can_create(driver):
        cls = RasterDataWriter
    elif driver_can_create_copy(driver):  # pragma: no branch
        cls = BufferedRasterDataWriter
    return cls


def get_writer_for_path(path):
    """Return the writer class appropriate for the existing dataset."""
    cls = None
    driver = get_dataset_driver(path)
    if driver_can_create(driver):
        cls = RasterDataWriter
    elif driver_can_create_copy(driver):  # pragma: no branch
        cls = BufferedRasterDataWriter
    return cls
