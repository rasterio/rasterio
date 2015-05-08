#!/usr/bin/env python
# main: loader of all the command entry points.

from pkg_resources import iter_entry_points


for entry_point in iter_entry_points('rasterio.rio_commands'):
    entry_point.load()
