"""
DEPRECATED; To be removed in 1.0
"""
from __future__ import absolute_import

import rasterio.mask


def mask(*args, **kwargs):
    import warnings
    warnings.warn("Deprecated; Use rasterio.mask instead", DeprecationWarning)
    return rasterio.mask.mask(*args, **kwargs)
