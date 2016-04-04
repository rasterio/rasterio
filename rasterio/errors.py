"""A module of errors."""

from click import FileError


class CRSError(ValueError):
    """Raised when a CRS string or mapping is invalid or cannot serve
    to define a coordinate transformation."""


class DriverRegistrationError(ValueError):
    """Raised when a format driver is requested but is not registered."""


class FileOverwriteError(FileError):
    """Raised when Rasterio's CLI refuses to clobber output files."""

    def __init__(self, message):
        super(FileOverwriteError, self).__init__('', hint=message)


class RasterioIOError(IOError):
    """Raised when a dataset cannot be opened using one of the
    registered format drivers."""
