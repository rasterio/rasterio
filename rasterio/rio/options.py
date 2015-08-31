"""
Registry of common rio CLI options.  See cligj for more options.

-a, --all: Use all pixels touched by features.  In rio-mask, rio-rasterize
--as-mask/--not-as-mask: interpret band as mask or not.  In rio-shapes
--band/--mask: use band or mask.  In rio-shapes
--bbox:
-b, --bidx: band index(es) (singular or multiple value versions).
    In rio-info, rio-sample, rio-shapes, rio-stack (different usages)
--bounds: bounds in world coordinates.
    In rio-info, rio-rasterize (different usages)
--count: count of bands.  In rio-info
--crop: Crop raster to extent of features.  In rio-mask
--crs: CRS of input raster.  In rio-info
--default-value: default for rasterized pixels.  In rio-rasterize
--dimensions: Output width, height.  In rio-rasterize
--dst-crs: destination CRS.  In rio-transform
--fill: fill value for pixels not covered by features.  In rio-rasterize
--formats: list available formats.  In rio-info
--height: height of raster.  In rio-info
-i, --invert: Invert mask created from features: In rio-mask
-j, --geojson-mask: GeoJSON for masking raster.  In rio-mask
--lnglat: geograhpic coordinates of center of raster.  In rio-info
--masked/--not-masked: read masked data from source file.
    In rio-calc, rio-info
-m, --mode: output file mode (r, r+).  In rio-insp
--name: input file name alias.  In rio-calc
--nodata: nodata value.  In rio-info, rio-merge (different usages)
--photometric: photometric interpretation.  In rio-stack
--property: GeoJSON property to use as values for rasterize.  In rio-rasterize
-r, --res: output resolution.
    In rio-info, rio-rasterize (different usages.  TODO: try to combine
    usages, prefer rio-rasterize version)
--sampling: Inverse of sampling fraction.  In rio-shapes
--shape: shape (width, height) of band.  In rio-info
--src-crs: source CRS.
    In rio-insp, rio-rasterize (different usages.  TODO: consolidate usages)
--stats: print raster stats.  In rio-inf
-t, --dtype: data type.  In rio-calc, rio-info (different usages)
--width: width of raster.  In rio-info
--with-nodata/--without-nodata: include nodata regions or not.  In rio-shapes.
-v, --tell-me-more, --verbose
--vfs: virtual file system.
"""


# TODO: move file_in_arg and file_out_arg to cligj


import click


def _cb_key_val(ctx, param, value):

    """
    click callback to validate `--opt KEY1=VAL1 --opt KEY2=VAL2` and collect
    in a dictionary like the one below, which is what the CLI function receives.
    If no value or `None` is received then an empty dictionary is returned.

        {
            'KEY1': 'VAL1',
            'KEY2': 'VAL2'
        }

    Note: `==VAL` breaks this as `str.split('=', 1)` is used.
    """

    if not value:
        return {}
    else:
        out = {}
        for pair in value:
            if '=' not in pair:
                raise click.BadParameter("Invalid syntax for KEY=VAL arg: {}".format(pair))
            else:
                k, v = pair.split('=', 1)
                out[k] = v

        return out


# Singular input file
file_in_arg = click.argument(
    'INPUT',
    type=click.Path(exists=True, resolve_path=True))

# Singular output file
file_out_arg = click.argument(
    'OUTPUT',
    type=click.Path(resolve_path=True))

bidx_opt = click.option(
    '-b', '--bidx',
    type=int,
    default=1,
    help="Input file band index (default: 1)")

bidx_mult_opt = click.option(
    '-b', '--bidx',
    multiple=True,
    help="Indexes of input file bands.")

# TODO: may be better suited to cligj
bounds_opt = click.option(
    '--bounds',
    nargs=4, type=float, default=None,
    help='Output bounds: left bottom right top.')

dimensions_opt = click.option(
    '--dimensions',
    nargs=2, type=int, default=None,
    help='Output dataset width, height in number of pixels.')

dtype_opt = click.option(
    '-t', '--dtype',
    type=click.Choice([
        'ubyte', 'uint8', 'uint16', 'int16', 'uint32', 'int32',
        'float32', 'float64']),
    default=None,
    help="Output data type.")

like_file_opt = click.option(
    '--like',
    type=click.Path(exists=True),
    help='Raster dataset to use as a template for obtaining affine '
         'transform (bounds and resolution), crs, data type, and driver '
         'used to create the output.')

masked_opt = click.option(
    '--masked/--not-masked',
    default=True,
    help="Evaluate expressions using masked arrays (the default) or ordinary "
         "numpy arrays.")

output_opt = click.option(
    '-o', '--output',
    default=None,
    type=click.Path(resolve_path=True),
    help="Path to output file (optional alternative to a positional arg "
         "for some commands).")

resolution_opt = click.option(
    '-r', '--res',
    multiple=True, type=float, default=None,
    help='Output dataset resolution in units of coordinate '
         'reference system. Pixels assumed to be square if this option '
         'is used once, otherwise use: '
         '--res pixel_width --res pixel_height')

creation_options = click.option(
    '--co', 'creation_options',
    metavar='NAME=VALUE',
    multiple=True,
    callback=_cb_key_val,
    help="Driver specific creation options."
         "See the documentation for the selected output driver for "
         "more information.")

rgb_opt = click.option(
    '--rgb', 'photometric', 
    flag_value='rgb',
    default=False,
    help="Set RGB photometric interpretation.")


vfs_opt = click.option(
    '--vfs', 'vfs',
    default=None,
    help="Use a zip:// or tar:// archive as a virtual file system "
         "('r' mode only).")
