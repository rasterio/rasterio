"""Driver policies and utilities

GDAL has many standard and extension format drivers and completeness of
these drivers varies greatly. It's possible to succeed poorly with some
formats and drivers, meaning that easy problems can be solved but that
harder problems are blocked by limitations of the drivers and formats.

NetCDF writing, for example, is presently blacklisted. Rasterio users
should use netcdf4-python instead:
http://unidata.github.io/netcdf4-python/.
"""

blacklist = {'netCDF': ('r+', 'w')}


def is_blacklisted(name, mode):
    return mode in blacklist.get(name, ())
