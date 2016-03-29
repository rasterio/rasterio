"""
DEPRECATED; To be removed in 1.0
"""
from __future__ import absolute_import

import rasterio.merge


def merge(*args, **kwargs):
    import warnings
    warnings.warn("Deprecated; Use rasterio.merge instead", DeprecationWarning)
    return rasterio.merge.merge(*args, **kwargs)
