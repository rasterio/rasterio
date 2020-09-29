"""$ rio merge"""


import click

import rasterio
from rasterio.enums import Resampling
from rasterio.rio import options
from rasterio.rio.helpers import resolve_inout


@click.command(short_help="Merge a stack of raster datasets.")
@options.files_inout_arg
@options.output_opt
@options.format_opt
@options.bounds_opt
@options.resolution_opt
@click.option('--resampling',
              type=click.Choice([r.name for r in Resampling if r.value <= 7]),
              default='nearest', help="Resampling method.",
              show_default=True)
@options.nodata_opt
@options.bidx_mult_opt
@options.overwrite_opt
@click.option('--precision', type=int, default=10,
              help="Number of decimal places of precision in alignment of "
                   "pixels")
@options.creation_options
@click.pass_context
def merge(ctx, files, output, driver, bounds, res, resampling,
          nodata, bidx, overwrite, precision, creation_options):
    """Copy valid pixels from input files to an output file.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm. If the output file exists, its values will be
    overwritten by input values.

    Geospatial bounds and resolution of a new output file in the
    units of the input file coordinate reference system may be provided
    and are otherwise taken from the first input file.

    Note: --res changed from 2 parameters in 0.25.

    \b
      --res 0.1 0.1  => --res 0.1 (square)
      --res 0.1 0.2  => --res 0.1 --res 0.2  (rectangular)
    """
    from rasterio.merge import merge as merge_tool

    output, files = resolve_inout(
        files=files, output=output, overwrite=overwrite)

    resampling = Resampling[resampling]

    with ctx.obj["env"]:
        dest, output_transform = merge_tool(
            files,
            bounds=bounds,
            res=res,
            nodata=nodata,
            precision=precision,
            indexes=(bidx or None),
            resampling=resampling,
        )

        with rasterio.open(files[0]) as first:
            profile = first.profile
            profile["transform"] = output_transform
            profile["height"] = dest.shape[1]
            profile["width"] = dest.shape[2]
            profile["count"] = dest.shape[0]
            profile.pop("driver", None)
            if driver:
                profile["driver"] = driver
            if nodata is not None:
                profile["nodata"] = nodata

            profile.update(**creation_options)

            with rasterio.open(output, "w", **profile) as dst:
                dst.write(dest)

                # uses the colormap in the first input raster.
                try:
                    colormap = first.colormap(1)
                    dst.write_colormap(1, colormap)
                except ValueError:
                    pass
