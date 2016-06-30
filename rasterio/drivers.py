"""Driver policies and utilities

GDAL has many standard and extension format drivers and completeness of
these drivers varies greatly. It's possible to succeed poorly with some
formats and drivers, meaning that easy problems can be solved but that
harder problems are blocked by limitations of the drivers and formats.

NetCDF writing, for example, is presently blacklisted. Rasterio users
should use netcdf4-python instead:
http://unidata.github.io/netcdf4-python/.
"""

# Methods like `rasterio.open()` may use this blacklist to preempt
# combinations of drivers and file modes.
blacklist = {
    # See https://github.com/mapbox/rasterio/issues/638 for discussion
    # about writing NetCDF files.
    'netCDF': ('r+', 'w')}


def is_blacklisted(name, mode):
    """Returns True if driver `name` and `mode` are blacklisted."""
    return mode in blacklist.get(name, ())
