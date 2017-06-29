"""Raster dataset profiles."""

import warnings

from rasterio.compat import UserDict
from rasterio.dtypes import uint8
from rasterio.errors import RasterioDeprecationWarning


class Profile(UserDict):
    """Base class for Rasterio dataset profiles.

    Subclasses will declare driver-specific creation options.
    """

    defaults = {}

    def __init__(self, data={}, **kwds):
        """Create a new profile based on the class defaults, which are
        overlaid with items from the `data` dict and keyword arguments."""
        UserDict.__init__(self)
        initdata = self.defaults.copy()
        initdata.update(data)
        initdata.update(**kwds)

        if 'affine' in initdata and 'transform' in initdata:
            warnings.warn("affine item is deprecated, use transform only",
                          RasterioDeprecationWarning)
            del initdata['affine']
        elif 'affine' in initdata:
            warnings.warn("affine item is deprecated, use transform instead",
                          RasterioDeprecationWarning)
            initdata['transform'] = initdata.pop('affine')

        self.data.update(initdata)

    def __getitem__(self, key):
        """Like normal item access but with affine alias."""
        if key == 'affine':
            key = 'transform'
            warnings.warn("affine item is deprecated, use transform instead",
                          RasterioDeprecationWarning)
        return self.data[key]

    def __setitem__(self, key, val):
        """Like normal item setter but forbidding affine item."""
        if key == 'affine':
            raise TypeError("affine key is prohibited")
        self.data[key] = val

    def __call__(self, **kwds):
        """Return a mapping of keyword args.

        DEPRECATED.
        """
        warnings.warn("__call__() is deprecated, use mapping methods instead",
                      RasterioDeprecationWarning)
        profile = self.data.copy()
        profile.update(**kwds)
        return profile


class DefaultGTiffProfile(Profile):
    """Tiled, band-interleaved, LZW-compressed, 8-bit GTiff."""

    defaults = {
        'driver': 'GTiff',
        'interleave': 'band',
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
        'compress': 'lzw',
        'nodata': 0,
        'dtype': uint8
    }


default_gtiff_profile = DefaultGTiffProfile()
