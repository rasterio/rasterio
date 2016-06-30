"""$ rio blocks"""


import json
import logging
import os.path

import click
import cligj

import rasterio
from rasterio.rio import options
from rasterio.rio.helpers import write_features
from rasterio.warp import transform_bounds


logger = logging.getLogger('rio')


class _Collection(object):

    """For use with `rasterio.rio.helpers.write_features()`."""

    def __init__(self, src, bidx, precision=6, geographic=True):

        """Export raster dataset windows to GeoJSON polygon features.

        Parameters
        ----------
        src : RasterReader
            An open datasource.
        bidx : int
            Extract windows from this band.
        precision : int, optional
            Coordinate precision.
        geographic : bool, optional
            Reproject geometries to ``EPSG:4326`` if ``True``.

        Yields
        ------
        dict
            GeoJSON polygon feature.
        """

        self._src = src
        self._bidx = bidx
        self._precision = precision
        self._geographic = geographic

    def _normalize_bounds(self, bounds):
        if self._geographic:
            bounds = transform_bounds(self._src.crs, 'EPSG:4326', *bounds)
        if self._precision >= 0:
            bounds = (round(v, self._precision) for v in bounds)
        return bounds

    @property
    def bbox(self):
        return tuple(self._normalize_bounds(self._src.bounds))

    def __call__(self):
        gen = self._src.block_windows(bidx=self._bidx)
        for idx, (block, window) in enumerate(gen):
            bounds = self._normalize_bounds(self._src.window_bounds(window))
            xmin, ymin, xmax, ymax = bounds
            yield {
                'type': 'Feature',
                'id': '{0}:{1}'.format(os.path.basename(self._src.name), idx),
                'properties': {
                    'block': json.dumps(block),
                    'window': json.dumps(window)
                },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[
                        (xmin, ymin),
                        (xmin, ymax),
                        (xmax, ymax),
                        (xmax, ymin)
                    ]]
                }
            }


@click.command()
@options.file_in_arg
@options.output_opt
@cligj.precision_opt
@cligj.indent_opt
@cligj.compact_opt
@cligj.projection_geographic_opt
@cligj.projection_projected_opt
@cligj.sequence_opt
@cligj.use_rs_opt
@click.option(
    '--bidx', type=click.INT, default=0,
    help="Index of the band that is the source of shapes.")
@click.pass_context
def blocks(
        ctx, input, output, precision, indent, compact, projection, sequence,
        use_rs, bidx):

    """Write dataset blocks as GeoJSON features.

    This command writes features describing a rasters internal tiling scheme,
    which are often used to visually get a feel for how a windowed operation
    might work.  Rasters that are not tiled internally can still have internal
    blocks that are not square, and this command does not differentiate between
    the two.

    Output features have two JSON encoded properties: block and window.  Block
    is a two element array like `[0, 0]` describing the window's position
    in the input band's window layout.  Window is a two element array
    containing two more two element arrays like `[[0, 256], [0, 256]]` and
    describes the range of pixels the window covers in the input band.  Values
    are JSON encoded for better interoperability.

    Block windows are extracted from the dataset (all bands must have matching
    block windows) by default, or from the band specified using the `--bidx`
    option:
    \b

        $ rio shapes --bidx 3 tests/data/RGB.byte.tif

    By default a GeoJSON `FeatureCollection` is written, but the `--sequence`
    option produces a GeoJSON feature stream instead.
    \b

        $ rio shapes tests/data/RGB.byte.tif --sequence

    Output features are reprojected to `WGS84` unless the `--projected` flag is
    provided, which causes the outupt to be kept in the input datasource's
    coordinate reference system.

    For more information on exactly what blocks and windows represent, see
    `src.block_windows()`.
    """

    verbosity = ctx.obj['verbosity'] if ctx.obj else 1

    dump_kwds = {'sort_keys': True}

    if indent:
        dump_kwds['indent'] = indent
    if compact:
        dump_kwds['separators'] = (',', ':')

    stdout = click.open_file(
        output, 'w') if output else click.get_text_stream('stdout')

    try:
        with rasterio.Env(CPL_DEBUG=verbosity > 2):
            with rasterio.open(input) as src:

                collection = _Collection(
                    src=src,
                    bidx=bidx,
                    precision=precision,
                    geographic=projection == 'geographic')

                write_features(
                    stdout, collection,
                    sequence=sequence,
                    geojson_type='feature' if sequence else 'collection',
                    use_rs=use_rs,
                    **dump_kwds)
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
