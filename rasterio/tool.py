"""
DEPRECATED; To be removed in 1.0
"""
from __future__ import absolute_import
import rasterio.rio.insp


def show(*args, **kwargs):
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.rio.insp.show(*args, **kwargs)


def stats(*args, **kwargs):
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.rio.insp.stats(*args, **kwargs)


def show_hist(*args, **kwargs):
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.rio.insp.show_hist(*args, **kwargs)


def main(*args, **kwargs):
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.rio.insp.main(*args, **kwargs)
