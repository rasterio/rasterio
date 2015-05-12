# main: loader of all the command entry points.

import sys
import traceback

from pkg_resources import iter_entry_points

from rasterio.rio.cli import BrokenCommand, cli


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
    try:
        entry_point.load()
    except Exception:
        # Catch this so a busted plugin doesn't take down the CLI.
        # Handled by registering a dummy command that does nothing
        # other than explain the error.
        cli.add_command(
            BrokenCommand(entry_point.name))
