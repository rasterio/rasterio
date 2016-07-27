# coding: utf-8
"""Manage overviews of a dataset."""

from functools import reduce
import logging
import operator

import click

from . import options
import rasterio
from rasterio.enums import Resampling


def build_handler(ctx, param, value):
    if value:
        try:
            if '^' in value:
                base, exp_range = value.split('^')
                exp_min, exp_max = (int(v) for v in exp_range.split('..'))
                value = [pow(int(base), k) for k in range(exp_min, exp_max + 1)]
            else:
                value = [int(v) for v in value.split(',')]
        except Exception:
            raise click.BadParameter(u"must match 'n,n,n,…' or 'n^n..n'.")
    return value


@click.command('overview', short_help="Construct overviews in an existing dataset.")
@options.file_in_arg
@click.option('--build', callback=build_handler, metavar=u"f1,f2,…|b^min..max",
              help="A sequence of decimation factors specied as "
                   "comma-separated list of numbers or a base and range of "
                   "exponents.")
@click.option('--ls', help="Print the overviews for each band.",
              is_flag=True, default=False)
@click.option('--rebuild', help="Reconstruct existing overviews.",
              is_flag=True, default=False)
@click.option('--resampling', help="Resampling algorithm.",
              type=click.Choice(
                  [it.name for it in Resampling if it.value in [0, 2, 5, 6, 7]]),
              default='nearest', show_default=True)
@click.pass_context
def overview(ctx, input, build, ls, rebuild, resampling):
    """Construct overviews in an existing dataset.

    A pyramid of overviews computed once and stored in the dataset can
    improve performance in some applications.

    The decimation levels at which to build overviews can be specified as
    a comma separated list

      rio overview --build 2,4,8,16

    or a base and range of exponents.

      rio overview --build 2^1..4

    Note that overviews can not currently be removed and are not
    automatically updated when the dataset's primary bands are
    modified.

    Information about existing overviews can be printed using the --ls
    option.

      rio overview --ls

    """
    with ctx.obj['env']:
        with rasterio.open(input, 'r+') as dst:

            if ls:
                resampling_method = dst.tags(
                    ns='rio_overview').get('resampling') or 'unknown'

                click.echo("Overview factors:")
                for idx in dst.indexes:
                    click.echo("  Band %d: %s (method: '%s')" % (
                        idx, dst.overviews(idx) or 'None', resampling_method))

            elif rebuild:
                # Build the same overviews for all bands.
                factors = reduce(
                    operator.or_,
                    [set(dst.overviews(i)) for i in dst.indexes])

                # Attempt to recover the resampling method from dataset tags.
                resampling_method = dst.tags(
                    ns='rio_overview').get('resampling') or resampling

                dst.build_overviews(
                    list(factors), Resampling[resampling_method])

            elif build:
                dst.build_overviews(build, Resampling[resampling])

                # Save the resampling method to a tag.
                dst.update_tags(ns='rio_overview', resampling=resampling)
