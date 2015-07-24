import logging

import click
from cligj import files_inout_arg, format_opt

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio.five import zip_longest


PHOTOMETRIC_CHOICES = [val.lower() for val in [
    'MINISBLACK',
    'MINISWHITE',
    'RGB',
    'CMYK',
    'YCBCR',
    'CIELAB',
    'ICCLAB',
    'ITULAB']]


# Stack command.
@click.command(short_help="Stack a number of bands into a multiband dataset.")
@files_inout_arg
@options.output_opt
@format_opt
@options.bidx_mult_opt
@click.option('--rgb', 'photometric', flag_value='rgb', default=False,
              help="Set RGB photometric interpretation")
@options.creation_options
@click.pass_context
def stack(ctx, files, output, driver, bidx, photometric, creation_options):
    """Stack a number of bands from one or more input files into a
    multiband dataset.

    Input datasets must be of a kind: same data type, dimensions, etc. The
    output is cloned from the first input.

    By default, rio-stack will take all bands from each input and write them
    in same order to the output. Optionally, bands for each input may be
    specified using a simple syntax:

      --bidx N takes the Nth band from the input (first band is 1).

      --bidx M,N,0 takes bands M, N, and O.

      --bidx M..O takes bands M-O, inclusive.

      --bidx ..N takes all bands up to and including N.

      --bidx N.. takes all bands from N to the end.

    Examples, using the Rasterio testing dataset, which produce a copy.

      rio stack RGB.byte.tif -o stacked.tif

      rio stack RGB.byte.tif --bidx 1,2,3 -o stacked.tif

      rio stack RGB.byte.tif --bidx 1..3 -o stacked.tif

      rio stack RGB.byte.tif --bidx ..2 RGB.byte.tif --bidx 3.. -o stacked.tif

    """

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 2
    logger = logging.getLogger('rio')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            output, files = resolve_inout(files=files, output=output)
            output_count = 0
            indexes = []
            for path, item in zip_longest(files, bidx, fillvalue=None):
                with rasterio.open(path) as src:
                    src_indexes = src.indexes
                if item is None:
                    indexes.append(src_indexes)
                    output_count += len(src_indexes)
                elif '..' in item:
                    start, stop = map(
                        lambda x: int(x) if x else None, item.split('..'))
                    if start is None:
                        start = 1
                    indexes.append(src_indexes[slice(start-1, stop)])
                    output_count += len(src_indexes[slice(start-1, stop)])
                else:
                    parts = list(map(int, item.split(',')))
                    if len(parts) == 1:
                        indexes.append(parts[0])
                        output_count += 1
                    else:
                        parts = list(parts)
                        indexes.append(parts)
                        output_count += len(parts)

            with rasterio.open(files[0]) as first:
                kwargs = first.meta
                kwargs.update(**creation_options)
                kwargs['transform'] = kwargs.pop('affine')

            kwargs.update(
                driver=driver,
                count=output_count)

            if photometric:
                kwargs['photometric'] = photometric

            with rasterio.open(output, 'w', **kwargs) as dst:
                dst_idx = 1
                for path, index in zip(files, indexes):
                    with rasterio.open(path) as src:
                        if isinstance(index, int):
                            data = src.read(index)
                            dst.write(data, dst_idx)
                            dst_idx += 1
                        elif isinstance(index, list):
                            data = src.read(index)
                            dst.write(data, range(dst_idx, dst_idx+len(index)))
                            dst_idx += len(index)

    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
