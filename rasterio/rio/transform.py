"""Fetch and edit raster dataset metadata from the command line."""

import json

import click
from cligj import precision_opt

from rasterio.rio.helpers import hushpipe
import rasterio.shutil


@click.command(short_help="Transform coordinates.")
@click.argument('INPUT', default='-', required=False)
@click.option('--src-crs', '--src_crs', default='EPSG:4326',
              help="Source CRS.")
@click.option('--dst-crs', '--dst_crs', default='EPSG:4326',
              help="Destination CRS.")
@precision_opt
@click.pass_context
@hushpipe
def transform(ctx, input, src_crs, dst_crs, precision):
    import rasterio.warp

    # Handle the case of file, stream, or string input.
    try:
        src = click.open_file(input).readlines()
    except OSError:
        src = [input]

    with ctx.obj["env"]:

        if src_crs.startswith("EPSG"):
            src_crs = {"init": src_crs}
        elif rasterio.shutil.exists(src_crs):
            with rasterio.open(src_crs) as f:
                src_crs = f.crs

        if dst_crs.startswith("EPSG"):
            dst_crs = {"init": dst_crs}
        elif rasterio.shutil.exists(dst_crs):
            with rasterio.open(dst_crs) as f:
                dst_crs = f.crs

        for line in src:
            coords = json.loads(line)
            xs = coords[::2]
            ys = coords[1::2]
            xs, ys = rasterio.warp.transform(src_crs, dst_crs, xs, ys)

            if precision >= 0:
                xs = [round(v, precision) for v in xs]
                ys = [round(v, precision) for v in ys]

            result = [0] * len(coords)
            result[::2] = xs
            result[1::2] = ys
            click.echo(json.dumps(result))
