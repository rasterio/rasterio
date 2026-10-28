"""Execute a GDAL 3.12+ pipeline from the rio CLI."""

import click

from rasterio.errors import RasterioIOError
from rasterio.pipeline import run as run_pipeline
from rasterio.rio import options


# Everything after the first PIPELINE token belongs to GDAL, so stop
# option parsing there; otherwise click rejects step options such as
# --dst-crs, or steals ones that clash with ours (e.g. write -f).
@click.command(
    short_help="Run a GDAL 3.12+ pipeline.",
    context_settings=dict(allow_interspersed_args=False),
)
@click.argument(
    "pipeline", nargs=-1, required=True, type=click.UNPROCESSED, metavar="PIPELINE"
)
@click.option(
    "-i",
    "--input",
    "inputs",
    multiple=True,
    help="Input dataset path(s) to bind to the pipeline.",
)
@options.output_opt
@options.format_opt
@click.pass_context
def pipeline(ctx, pipeline, inputs, output, driver):
    """Execute a GDAL 3.12+ pipeline.

    PIPELINE may be passed as a single quoted pipeline specification string
    (with steps separated by ``!``) or as multiple command-line tokens.
    Options of this command must come before PIPELINE.

    Examples:

    \b
      $ rio pipeline "! read in.tif ! reproject --dst-crs=EPSG:4326 ! write out.tif --overwrite"

    \b
      $ rio pipeline -i in.tif -o out.tif "read ! reproject --dst-crs=EPSG:4326"

    \b
      $ rio pipeline -i in.tif -o out.tif read ! reproject --dst-crs=EPSG:4326
    """
    with ctx.obj["env"]:
        if len(pipeline) == 1:
            pipe_arg = pipeline[0]
        else:
            pipe_arg = list(pipeline)

        if not inputs:
            input_arg = None
        elif len(inputs) == 1:
            input_arg = inputs[0]
        else:
            input_arg = list(inputs)

        try:
            result = run_pipeline(
                pipe_arg,
                input=input_arg,
                output=output,
                output_format=driver,
            )
        except (RasterioIOError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        if result:
            click.echo(result, nl=False)
