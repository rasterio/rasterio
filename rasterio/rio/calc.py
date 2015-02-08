# Calc command.

import logging
import math
import os.path
import re
import sys
import warnings

import click
from cligj import files_inout_arg

import rasterio
from rasterio.rio.cli import cli


@cli.command(short_help="Raster data calculator.")
@click.argument('command')
@files_inout_arg
@click.pass_context
def calc(ctx, command, files):
    import numpy as np

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            output = files[-1]
            files = files[:-1]

            with rasterio.open(files[0]) as first:
                kwargs = first.meta
                kwargs['transform'] = kwargs.pop('affine')

                sources = [rasterio.open(path).read() for path in files]


                # TODO: implement a real parser for calc expressions,
                # perhaps using numexpr's parser as a guide, instead
                # eval'ing any string.

                parts = command.split(';')
                if len(parts) == 1:
                    with rasterio.open(output, 'w', **kwargs) as dst:

                        # This one translates, eg, '{1}' to
                        # 'sources[0]'.
                        cmd = re.sub(
                                r'{(\d)}',
                                lambda m: 'sources[%d]' % (int(m.group(1))-1),
                                parts.pop())

                        logger.debug("Translated cmd: %r", cmd)

                        # TODO: enable output dtype selection.
                        results = eval(cmd).astype(kwargs['dtype'])
                        dst.write(results)

                else:
                    parts = list(filter(lambda p: p.strip(), parts))
                    kwargs['count'] = len(parts)
                    with rasterio.open(output, 'w', **kwargs) as dst:

                        for i, part in enumerate(parts, 1):
                            cmd = re.sub(
                                    r'{(\d)\s*,\s*(\d)}',
                                    lambda m: 'sources[%d][%d]' % (
                                        int(m.group(1))-1, int(m.group(2))-1),
                                    part)

                            logger.debug("Translated cmd: %r", cmd)

                            # TODO: enable output dtype selection.
                            result = eval(cmd).astype(kwargs['dtype'])
                            dst.write(result, i)

        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
