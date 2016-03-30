"""
Main click group for CLI
"""


import logging
from pkg_resources import iter_entry_points
import sys

import click
from click_plugins import with_plugins
import cligj

from . import options
import rasterio
from rasterio import aws


def configure_logging(verbosity):
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


class FakeSession(object):
    """Fake AWS Session."""

    def __enter__(self):
        pass

    def __exit__(self):
        pass

    def open(self, path, mode='r'):
        return rasterio.open(path, mode)


def get_aws_session(profile_name):
    try:
        import rasterio.aws
        return rasterio.aws.Session(profile_name=profile_name)
    except ImportError:
        return FakeSession()


@with_plugins(ep for ep in list(iter_entry_points('rasterio.rio_commands')) +
              list(iter_entry_points('rasterio.rio_plugins')))
@click.group()
@cligj.verbose_opt
@cligj.quiet_opt
@click.option('--aws-profile', help="AWS credentials profile name")
@click.version_option(version=rasterio.__version__, message='%(version)s')
@click.pass_context
def main_group(ctx, verbose, quiet, aws_profile):

    """
    Rasterio command line interface.
    """

    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity
    ctx.obj['aws_session'] = get_aws_session(aws_profile)
