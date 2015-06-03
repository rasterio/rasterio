"""
Main click group for CLI
"""


import logging
from pkg_resources import iter_entry_points
import sys

import click
import cligj
import cligj.plugins

import rasterio


def configure_logging(verbosity):
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


@cligj.plugins.group(plugins=(
        ep for ep in list(iter_entry_points('rasterio.rio_commands')) +
                     list(iter_entry_points('rasterio.rio_plugins'))))
@cligj.verbose_opt
@cligj.quiet_opt
@click.version_option(version=rasterio.__version__, message='%(version)s')
@click.pass_context
def main_group(ctx, verbose, quiet):

    """
    Rasterio command line interface.
    """

    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity
