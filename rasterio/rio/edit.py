"""Edit raster dataset metadata from the command line."""

import json
import logging

import click

import rasterio
from rasterio.rio.cli import cli, file_in_arg
from rasterio.transform import guard_transform


@cli.command(short_help="Edit dataset metadata.")
@file_in_arg
@click.option('--nodata', type=float, default=None,
              help="New nodata value")
@click.option('--crs', help="New coordinate reference system")
@click.option('--transform', help="New affine transform matrix")
@click.option('--tag', 'tags', multiple=True, metavar='KEY=VAL',
              help="New tag.")
@click.pass_context
def edit(ctx, input, nodata, crs, transform, tags):
    """Edit a dataset's metadata: coordinate reference system, affine
    transformation matrix, nodata value, and tags.

    CRS may be either a PROJ.4 or EPSG:nnnn string, or a JSON-encoded
    PROJ.4 object.

    Transforms are either JSON-encoded Affine objects (preferred) like

      [300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]

    or JSON-encoded GDAL geotransform arrays like

      [101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]
    """
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    with rasterio.drivers(CPL_DEBUG=(verbosity > 2)) as env:
        with rasterio.open(input, 'r+') as dst:

            # Update nodata.
            if nodata:
                dst.nodata = nodata

            # Update CRS. Value might be a PROJ.4 string or a JSON
            # encoded dict.
            if crs:
                crs = crs.strip()
                try:
                    crs = json.loads(crs)
                except ValueError:
                    pass
                dst.crs = crs

            # Update transform. Value might be a JSON encoded
            # Affine object or a GDAL geotransform array.
            if transform:
                dst.transform = guard_transform(json.loads(transform))

            # Update tags.
            if tags:
                tags = dict(p.split('=') for p in tags)
                dst.update_tags(**tags)
