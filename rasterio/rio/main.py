"""
Main command group for Rasterio's CLI.
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
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


class FakeSession(object):
    """Fake AWS Session."""

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

    def open(self, path, mode='r'):
        return rasterio.open(path, mode)


def get_aws_session(profile_name):
    """Return a credentialed AWS session or a fake, depending on 
    whether boto3 could be imported."""
    try:
        import rasterio.aws
        return rasterio.aws.Session(profile_name=profile_name)
    except ImportError:
        return FakeSession()


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
@click.option('--aws-profile', help="Use a specific profile from your shared AWS credentials file")
@click.version_option(version=rasterio.__version__, message='%(version)s')
@click.option('--gdal-version', is_eager=True, is_flag=True, callback=gdal_version_cb)
@click.pass_context
def main_group(ctx, verbose, quiet, aws_profile, gdal_version):

    """
    Rasterio command line interface.
    """

    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity
    ctx.obj['aws_session'] = get_aws_session(aws_profile)
