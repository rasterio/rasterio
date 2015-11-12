"""Implementation of Apache VFS schemes and URLs"""


SCHEMES = ['gzip', 'zip', 'tar']


def parse_path(path, vfs=None):
    """Parse a file path or Apache VFS URL into its parts."""
    archive = scheme = None
    if vfs:
        parts = vfs.split("://")
        scheme = parts.pop(0) if parts else None
        archive = parts.pop(0) if parts else None
    else:
        parts = path.split("://")
        path = parts.pop() if parts else None
        scheme = parts.pop() if parts else None
        if scheme in SCHEMES:
            parts = path.split('!')
            path = parts.pop() if parts else None
            archive = parts.pop() if parts else None
        elif scheme in (None, 'file'):
            pass
        elif scheme not in SCHEMES:
            raise ValueError("VFS scheme {0} is unknown".format(scheme))
    return path, archive, scheme


def vsi_path(path, archive=None, scheme=None):
    """Convert a parsed path to a GDAL VSI path."""
    # If a VSF and archive file are specified, we convert the path to
    # a GDAL VSI path (see cpl_vsi.h).
    if vsi and vsi != 'file':
        path = path.strip(os.path.sep)
        if archive:
            result = os.path.sep.join(['/vsi{0}'.format(vsi), archive, path])
        else:
            result = os.path.sep.join(['/vsi{0}'.format(vsi), path])
    else:
        result = path
    return result
