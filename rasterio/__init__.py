#

import os

from six import string_types

from rasterio._io import RasterReadSession, RasterUpdateSession

def open(path, mode='r', driver=None):
    """."""
    if not isinstance(path, string_types):
        raise TypeError("invalid path: %r" % path)
    if mode and not isinstance(mode, string_types):
        raise TypeError("invalid mode: %r" % mode)
    if driver and not isinstance(driver, string_types):
        raise TypeError("invalid driver: %r" % driver)
    if mode in ('a', 'r'):
        if not os.path.exists(path):
            raise IOError("no such file or directory: %r" % path)
    if mode == 'a':
        s = RasterUpdateSession(path, mode, driver=None)
    elif mode == 'r':
        s = RasterReadSession(path)
    elif mode == 'w':
        s = RasterUpdateSession(path, mode, driver=driver)
    else:
        raise ValueError(
            "mode string must be one of 'r', 'w', or 'a', not %s" % mode)
    s.start()
    return s

