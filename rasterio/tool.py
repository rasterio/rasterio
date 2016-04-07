"""
DEPRECATED; To be removed in 1.0
"""
from __future__ import absolute_import


def show(*args, **kwargs):
    import rasterio.plot
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.plot.show_hist(*args, **kwargs)


def show_hist(*args, **kwargs):
    import rasterio.plot
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.plot.show_hist(*args, **kwargs)


def stats(*args, **kwargs):
    import rasterio.rio.insp
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.rio.insp.stats(*args, **kwargs)


def main(*args, **kwargs):  # pragma: no cover
    import rasterio.rio.insp
    import warnings
    warnings.warn("Deprecated; Use rasterio.rio.insp instead", DeprecationWarning)
    return rasterio.rio.insp.main(*args, **kwargs)
