"""Implementation of Apache VFS schemes and URLs."""

import os

from rasterio.compat import urlparse


SCHEMES = {
    'gzip': 'gzip',
    'gzip+file': 'gzip',
    'zip': 'zip',
    'zip+file': 'zip',
    'tar': 'tar',
    'tar+file': 'tar',
    'https': 'curl',
    'http': 'curl',
    's3': 's3'}

FILE_SCHEMES = [
    '', 'file', 'gzip', 'gzip+file', 'zip', 'zip+file', 'tar', 'tar+file']


def parse_path(uri, vfs=None):
    """Parse a URI or Apache VFS URL into its parts

    Returns: tuple
        (path, archive, scheme)
    """
    archive = scheme = None
    path = uri
    if vfs:
        parts = urlparse(vfs)
        scheme = parts.scheme
        archive = parts.path
        if parts.netloc and parts.netloc != 'localhost':  # pragma: no cover
            archive = parts.netloc + archive
    else:
        parts = urlparse(path)
        scheme = parts.scheme
        path = parts.path
        if parts.query:
            path += "?" + parts.query
        if parts.netloc and parts.netloc != 'localhost':
            path = parts.netloc + path
        # There are certain URI schemes we favor over GDAL's names.
        if scheme in SCHEMES:
            parts = path.split('!')
            path = parts.pop() if parts else None
            archive = parts.pop() if parts else None
        # For filesystem paths.
        elif scheme.lower() in FILE_SCHEMES:
            pass
        # We permit GDAL's idiosyncratic URI-like dataset paths such as
        # 'netcdf':... to fall right through with no parsed archive
        # or scheme.
        else:
            archive = scheme = None
            path = uri

    return path, archive, scheme


def vsi_path(path, archive=None, scheme=None):
    """Convert a parsed path to a GDAL VSI path."""
    # If a VSF and archive file are specified, we convert the path to
    # a GDAL VSI path (see cpl_vsi.h).
    if scheme and scheme.startswith('http'):
        result = "/vsicurl/{0}://{1}".format(scheme, path)
    elif scheme and scheme == 's3':
        result = "/vsis3/{0}".format(path)
    elif scheme and scheme != 'file':
        if archive:
            result = '/vsi{0}/{1}/{2}'.format(
                scheme, archive, path.lstrip('/'))
        else:
            result = '/vsi{0}/{1}'.format(scheme, path.lstrip('/'))
    else:
        result = path
    return result


class GDALFilename(object):
    """A GDAL filename object

    All legacy GDAL filenames must be wrapped using this class.

    Attributes
    ----------
    filename : str
        A GDAL filename such as "/vsicurl/https://example.com/data.tif".
    """

    def __init__(self, filename):
        self.filename = filename

    def __repr__(self):
        return "<GDALFilename filename={}>".format(self.filename)
