import logging
import sys

import click

from rasterio.rio import options

def configure_logging(verbosity):
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


# The CLI command group.
@click.group(help="Rasterio command line interface.")
@options.verbose
@options.quiet
@click.pass_context
def cli(ctx, verbose, quiet):
    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity
