# main: loader of all the command entry points.

from pkg_resources import iter_entry_points

from rasterio.rio.cli import cli


# Find and load all entry points in the rasterio.rio_commands group.
# This includes the standard commands included with Rasterio as well
# as commands provided by other packages.
#
# At a mimimum, commands must use the rasterio.rio.cli.cli command
# group decorator like so:
#
#   from rasterio.rio.cli import cli
#
#   @cli.command()
#   def foo(...):
#       ...

for entry_point in iter_entry_points('rasterio.rio_commands'):
    entry_point.load()
