# coding: utf-8
"""Manage overviews of a dataset."""

import logging

import click

import rasterio
from rasterio.enums import Resampling

from . import options


def build_handler(ctx, param, value):
    if value:
        try:
            if '^' in value:
                base, exp_range = value.split('^')
                exp_min, exp_max = (int(v) for v in exp_range.split('..'))
                value = [pow(int(base), k) for k in range(exp_min, exp_max+1)]
            else:
                value = [int(v) for v in value.split(',')]
        except Exception as exc:
            raise click.BadParameter(u"must match 'n,n,n,…' or 'n^n..n'.")
    return value


@click.command('pyramid', short_help="Construct overviews in an existing dataset.")
@options.file_in_arg
@click.option('--build', callback=build_handler, metavar=u"f1,f2,…|b^min..max",
              help="A sequence of decimation factors specied as "
                   "comma-separated list of numbers or a base and range of "
                   "exponents.")
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

    The decimation levels at which to build overviews can be specified as
    a comma separated list

      rio pyramid --build 2,4,8,16

    or a base and range of exponents.

      rio pyramid --build 2^1..4

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
                dst.build_overviews(build, Resampling[resampling])
