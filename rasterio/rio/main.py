"""
Main command group for Rasterio's CLI.

Subcommands developed as a part of the Rasterio package have their own
modules under ``rasterio.rio`` (like ``rasterio/rio/info.py``) and are
registered in the 'rasterio.rio_commands' entry point group in
Rasterio's ``setup.py``:

    entry_points='''
        [console_scripts]
        rio=rasterio.rio.main:main_group

        [rasterio.rio_commands]
        bounds=rasterio.rio.bounds:bounds
        calc=rasterio.rio.calc:calc
        ...

Users may create their own ``rio`` subcommands by writing modules that
register entry points in Rasterio's 'rasterio.rio_plugins' group. See
for example https://github.com/sgillies/rio-plugin-example, which has
been published to PyPI as ``rio-metasay``.

There's no advantage to making a ``rio`` subcommand which doesn't
import rasterio. But if you are using rasterio, you may profit from
Rasterio's CLI infrastructure and the network of existing commands.
Please add yours to the registry

  https://github.com/mapbox/rasterio/wiki/Rio-plugin-registry

so that other ``rio`` users may find it.
"""


import logging
from pkg_resources import iter_entry_points
import sys

from click_plugins import with_plugins
import click
import cligj

from . import options
import rasterio


def configure_logging(verbosity):
    log_level = max(10, 30 - 10 * verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


def gdal_version_cb(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo("{0}".format(rasterio.__gdal_version__), color=ctx.color)
    ctx.exit()


@with_plugins(ep for ep in list(iter_entry_points('rasterio.rio_commands')) +
              list(iter_entry_points('rasterio.rio_plugins')))
@click.group()
@cligj.verbose_opt
@cligj.quiet_opt
@click.option('--aws-profile',
              help="Selects a profile from your shared AWS credentials file")
@click.version_option(version=rasterio.__version__, message='%(version)s')
@click.option('--gdal-version', is_eager=True, is_flag=True,
              callback=gdal_version_cb)
@click.pass_context
def main_group(ctx, verbose, quiet, aws_profile, gdal_version):
    """Rasterio command line interface.
    """
    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity
    ctx.obj['aws_profile'] = aws_profile
    ctx.obj['env'] = rasterio.Env(CPL_DEBUG=(verbosity > 2),
                                  profile_name=aws_profile)
