"""Raster dataset profiles."""

from rasterio.dtypes import uint8


class Profile:
    """Base class for Rasterio dataset profiles.

    Subclasses will declare a format driver and driver-specific
    creation options.
    """
    driver = None
    defaults = {}

    def __call__(self, **kwargs):
        """Returns a mapping of keyword args for writing a new datasets.

        Example:

            profile = SomeProfile()
            with rasterio.open('foo.tif', 'w', **profile()) as dst:
                # Write data ...

        """
        if kwargs.get('driver', self.driver) != self.driver:
            raise ValueError(
                "Overriding this profile's driver is not allowed.")
        profile = self.defaults.copy()
        profile.update(**kwargs)
        profile['driver'] = self.driver
        return profile


class DefaultGTiffProfile(Profile):
    """A tiled, band-interleaved, LZW-compressed, 8-bit GTiff profile."""
    driver = 'GTiff'
    defaults = {
        'interleave': 'band',
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
        'compress': 'lzw',
        'nodata': 0,
        'dtype': uint8
    }


default_gtiff_profile = DefaultGTiffProfile()
