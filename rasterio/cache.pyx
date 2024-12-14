# cython: c_string_type=unicode, c_string_encoding=utf8

"""GDAL's VSI CURL cache."""

include "gdal.pxi"

from rasterio._path import _parse_path


def invalidate(pattern):
    """Invalidate responses in GDAL's VSI CURL cache

    Parameters
    ----------
    pattern : str
        Responses matching this pattern will be invalidated. In
        practice this is used to invalidate sections of a hierarchy
        of responses. "s3://bucket/prefix" will invalidate all
        responses to requests for objects under that prefix.

    Returns
    -------
    None
    """
    path = _parse_path(pattern).as_vsi()
    path = path.encode('utf-8')
    VSICurlPartialClearCache(path)

def invalidate_all():
    """Invalidate all responses in GDAL's VSI CURL cache

    Returns
    -------
    None
    """
    VSICurlClearCache()
