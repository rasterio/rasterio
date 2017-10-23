"""Classes capable of reading and writing datasets

Instances of these classes are called dataset objects.
"""


import logging

from rasterio._base import (
    get_dataset_driver, driver_can_create, driver_can_create_copy)
from rasterio._io import (
    DatasetReaderBase, DatasetWriterBase, BufferedDatasetWriterBase,
    MemoryFileBase)
from rasterio.windows import WindowMethodsMixin
from rasterio.env import ensure_env
from rasterio.transform import TransformMethodsMixin


log = logging.getLogger(__name__)


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
    def __init__(self, file_or_bytes=None, filename=None, ext=''):
        super(MemoryFile, self).__init__(
            file_or_bytes=file_or_bytes, filename=filename, ext=ext)

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
            return DatasetReader(vsi_path, 'r+')
        else:
            writer = get_writer_for_driver(driver)
            return writer(vsi_path, 'w', driver=driver, width=width,
                          height=height, count=count, crs=crs,
                          transform=transform, dtype=dtype,
                          nodata=nodata, **kwargs)

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
        return DatasetReader(vsi_path, 'r')


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
