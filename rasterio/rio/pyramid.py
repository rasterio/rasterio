"""Manage overviews of a dataset."""

import logging

import click

import rasterio
from rasterio.enums import Resampling

from . import options


@click.command('pyramid', short_help="Construct overviews in an existing dataset.")
@options.file_in_arg
@click.option('--build', help="A comma-separated list of decimation factors.")
@click.option('--ls', help="Print the overviews for each band.",
              is_flag=True, default=False)
@click.option('--resampling', help="Resampling algorithm.",
              type=click.Choice([item.name for item in Resampling]),
              default='nearest', show_default=True)
@click.pass_context
def pyramid(ctx, input, build, ls, resampling):
    """Construct overviews in an existing dataset.

    A pyramid of overviews computed once and stored in the dataset can
    improve performance in some applications.

    The decimation levels at which to build overviews are specified as
    a comma separated list to the --build option.

      rio pyramid --build 2,4,8,16

    Note that overviews can not currently be removed and are not 
    automatically updated when the dataset's primary bands are
    modified.

    Information about existing overviews can be printed using the --ls
    option.

      rio pyramid --ls

    """
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    with rasterio.drivers(CPL_DEBUG=(verbosity > 2)) as env:
        with rasterio.open(input, 'r+') as dst:

            if ls:
                for idx in dst.indexes:
                    listing = ','.join([str(v) for v in dst.overviews(idx)])
                    click.echo(
                        "Band %d: %s" % (idx, listing))

            elif build:
                factors = [int(v) for v in build.split(',')]
                dst.build_overviews(factors, Resampling[resampling])
