"""Implementation of Apache VFS schemes and URLs."""

import os

from rasterio.five import urlparse


# NB: As not to propagate fallacies of distributed computing, Rasterio
# does not support HTTP or FTP URLs via GDAL's vsicurl handler. Only
# the following local filesystem schemes are supported.
SCHEMES = {'gzip': 'gzip', 'zip': 'zip', 'tar': 'tar', 'https': 'curl',
           'http': 'curl', 's3': 's3'}


def parse_path(path, vfs=None):
    """Parse a file path or Apache VFS URL into its parts."""
    archive = scheme = None
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
        if parts.netloc and parts.netloc != 'localhost':
            path = parts.netloc + path
        if scheme in SCHEMES:
            parts = path.split('!')
            path = parts.pop() if parts else None
            archive = parts.pop() if parts else None
        elif scheme in (None, '', 'file'):
            pass
        else:
            raise ValueError("VFS scheme {0} is unknown".format(scheme))
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
        path = path.strip(os.path.sep)
        result = os.path.sep.join(
            ['/vsi{0}'.format(scheme), archive, path])
    else:
        result = path
    return result
