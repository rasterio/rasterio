"""A module of errors."""

from click import FileError


class RasterioIOError(IOError):
    """A failure to open a dataset using the presently registered drivers."""


class DriverRegistrationError(ValueError):
    """To be raised when, eg, _gdal.GDALGetDriverByName("MEM") returns NULL."""


class FileOverwriteError(FileError):
    """Rasterio's CLI refuses to implicitly clobber output files."""

    def __init__(self, message):
        super(FileOverwriteError, self).__init__('', hint=message)
