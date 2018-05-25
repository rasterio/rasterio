"""Implementation of Apache VFS schemes and URLs

**DEPRECATED**

This module is replaced by rasterio.path.
"""

import warnings

from rasterio.compat import urlparse
from rasterio.errors import RasterioDeprecationWarning
from rasterio.path import ParsedPath, UnparsedPath
from rasterio.path import parse_path as future_parse_path
from rasterio.path import vsi_path as future_vsi_path


def parse_path(path, vfs=None):
    """Parse a dataset's path into its parts

    **DEPRECATED**

    Parameters
    ----------
    path : str
        The path or filename to be parsed.
    vfs : str, optional **DEPRECATED**
        A virtual file system path.

    Returns
    -------
    path, archive, scheme : str
        Parts of the parsed path.
    """
    warnings.warn(
        "This function will be removed in version 1.0",
        RasterioDeprecationWarning
    )

    if vfs:
        parts = urlparse(vfs)
        scheme = parts.scheme
        archive = parts.path
        if parts.netloc and parts.netloc != 'localhost':  # pragma: no cover
            archive = parts.netloc + archive
        parsed = ParsedPath(path, archive, scheme)
        return parsed.path, parsed.archive, parsed.scheme

    else:
        parsed = future_parse_path(path)
        if isinstance(parsed, ParsedPath):
            return parsed.path, parsed.archive, parsed.scheme
        else:
            return parsed.path, None, None


def vsi_path(path, archive, scheme):
    """Convert a parsed path to a GDAL VSI path

    **DEPRECATED**

    Parameters
    ----------
    path : str
        The path part of a parsed path.
    archive : str
        The archive part of a parsed path.
    scheme : str
        The scheme part of a parsed path.

    Returns
    -------
    str
    """
    warnings.warn(
        "This function will be removed in version 1.0",
        RasterioDeprecationWarning
    )
    if archive or scheme:
        return future_vsi_path(ParsedPath(path, archive, scheme))
    else:
        return future_vsi_path(UnparsedPath(path))
