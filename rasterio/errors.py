"""A module of errors."""


class RasterioIOError(IOError):
    """A failure to open a dataset using the presently registered drivers."""


class RasterioDriverRegistrationError(ValueError):
    """To be raised when, eg, _gdal.GDALGetDriverByName("MEM") returns NULL"""
