#!/usr/bin/env python

"""Copy a raster with various options."""

import rasterio


def main(source, destination, opts, template=None, log=None):
    """Copy from source to destination with new options"""

    with rasterio.drivers():

        try:

            with rasterio.open(source) as src:

                # First, copy the opts to the destination's kwargs.
                kwargs = src.meta
                kwargs.update(opts)

                # If there's a template file, overlay its georeferencing.
                if template is not None:
                    with rasterio.open(template) as tmpl:
                        kwargs['transform'] = tmpl.transform
                        kwargs['crs'] = tmpl.crs

                # Write to the destination.
                # TODO: use shortcut to source buffer.
                with rasterio.open(destination, 'w', **kwargs) as dst:
                    for i in dst.indexes:
                        dst.write_band(i, src.read_band(i))

        except:
            log.exception("rio_cp failed, exception caught")
            return 1

    return 0


if __name__ == '__main__':

    import argparse
    import logging
    import sys

    parser = argparse.ArgumentParser(
        description="Copy raster file with options")
    parser.add_argument(
        'source',
        metavar='SOURCE',
        help="Source file name")
    parser.add_argument(
        'destination',
        metavar='DESTINATION',
        help="Destination file name")
    # TODO: add a short option for the following.
    parser.add_argument(
        '--template-file',
        metavar='FILE',
        help="Use a georeferenced file as a template")
    parser.add_argument(
        '-z', '--lzw',
        action='store_true',
        help="Compress destination using LZW")
    parser.add_argument(
        '--interleave-band',
        action='store_true',
        help="Band rather than pixel interleaved")
    parser.add_argument(
        '-t', '--tiled',
        action='store_true',
        help="Tiled rather than striped TIFFs")
    parser.add_argument(
        '--block-height',
        metavar='HEIGHT',
        help="Tile or strip height")
    parser.add_argument(
        '--block-width',
        metavar='WIDTH',
        help="Tile width")
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase verbosity")
    parser.add_argument(
        '-q', '--quiet',
        action='count',
        default=0,
        help="Decrease verbosity")
    args = parser.parse_args()

    verbosity = args.verbose - args.quiet
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)
    logger = logging.getLogger('rio_cp')

    # TODO: quick check of filenames before we call main().

    options = {}
    if args.interleave_band:
        options['interleave'] = 'band'
    if args.lzw:
        options['compress'] = 'LZW'
    if args.tiled:
        options['tiled'] = True
    if args.block_height:
        options['blockysize'] = args.block_height
    if args.block_width:
        options['blockxsize'] = args.block_width

    # TODO: support other formats.
    options['driver'] = 'GTiff'

    sys.exit(
        main(
            args.source,
            args.destination,
            options,
            args.template_file,
            log=logger))

