#!/usr/bin/env python

"""Warp a raster."""

import argparse
import logging
import sys

from pyproj import Proj, transform

import rasterio


def main():
    """Copy from source to destination with new options"""

    parser = argparse.ArgumentParser(
        description="Warp a raster file")
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
        '--destination-crs',
        metavar='CRS',
        help="Destination coordinate reference system")
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

    verbosity = args.v - args.q
    logging.basicConfig(stream=sys.stderr, level=(30 - 10*verbosity))
    logger = logging.getLogger('rasterio')

    # TODO: quick check of filenames before we call main().

    # TODO: support other formats.
    options['driver'] = 'GTiff'

    source = args.source
    destination = args.destination
    dest_crs = args.destination_crs
    template=args.template_file
    log=logger

    with rasterio.drivers():

        try:

            with rasterio.open(source) as src:

                # First, copy the opts to the destination's kwargs.
                kwargs = src.meta.copy()
                kwargs.update(opts)

                # If there's a template file, overlay its georeferencing.
                if template is not None:
                    with rasterio.open(template) as tmpl:
                        kwargs['transform'] = tmpl.transform
                        kwargs['crs'] = tmpl.crs

                # Determine the output extent.
                minx, miny = src.bounds[:2]
                ulx, uly = transform(Proj(src.crs), Proj(dst.crs), 
                                     minx, maxy)
                
                dst_transform = [ulx, dest_res, 0.0, uly, 0.0, -dest_res]



                # Write to the destination.
                # TODO: use shortcut to source buffer
                with rasterio.open(destination, 'w', **kwargs) as dst:
                    for i in src.indexes:
                        dst.write_band(i, src.read_band(i))

        except:
            log.exception("rio_cp failed, exception caught")
            sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
