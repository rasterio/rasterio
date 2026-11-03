"""rasterio.pipeline: GDAL 3.12+ pipeline execution and virtual streamed datasets."""

from rasterio._pipeline import PipelineVRTReaderBase, _run_pipeline
from rasterio.env import ensure_env_with_credentials, require_gdal_version
from rasterio.transform import TransformMethodsMixin
from rasterio.windows import WindowMethodsMixin

__all__ = ["PipelineVRT", "run"]


class PipelineVRT(PipelineVRTReaderBase, WindowMethodsMixin, TransformMethodsMixin):
    """A virtual streamed dataset backed by a GDAL 3.12+ pipeline.

    Executes a GDAL pipeline with ``output-format="stream"`` so that
    multi-step raster processing (e.g. ``read``, ``reproject``, ``clip``,
    ``scale``, ``select``, ``sieve``, ``calc``, ``mosaic``, ``stack``) is
    evaluated lazily on-the-fly when pixels are read, without writing
    intermediate files to disk.

    Parameters
    ----------
    pipeline : str or Sequence[str]
        A GDAL pipeline specification string (e.g.,
        ``"read ! reproject --dst-crs=EPSG:4326 ! scale"`` or
        ``"! read tests/data/RGB.byte.tif ! select --band 1,2"``) or a
        sequence of command-line tokens.
    input : DatasetReader, str, PathLike, or Sequence, optional
        Input dataset(s) or path(s) to bind to the pipeline's ``input``
        argument. Passing an already-open Rasterio dataset allows
        processing in-memory or virtual datasets without re-opening them.
        For multi-input steps (such as ``mosaic``, ``stack``, or ``calc``),
        pass a sequence of datasets or paths.

    Examples
    --------
    >>> import rasterio
    >>> from rasterio.pipeline import PipelineVRT
    >>> with rasterio.open("tests/data/RGB.byte.tif") as src:
    ...     with PipelineVRT(
    ...         "read ! reproject --dst-crs=EPSG:4326 ! select --band 1",
    ...         input=src,
    ...     ) as vrt:
    ...         data = vrt.read()
    """

    @require_gdal_version("3.12")
    @ensure_env_with_credentials
    def __init__(self, pipeline, input=None):
        super().__init__(pipeline, input=input)

    def __repr__(self):
        return "<{} PipelineVRT name='{}' mode='{}'>".format(
            self.closed and "closed" or "open", self.name, self.mode
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def __del__(self):
        self.close()


@require_gdal_version("3.12")
@ensure_env_with_credentials
def run(pipeline, input=None, output=None, output_format=None):
    """Execute a GDAL 3.12+ pipeline to completion.

    Supports all 60 raster, vector, and hybrid steps available in
    ``gdal pipeline`` (including ``read``, ``reproject``, ``clip``,
    ``sieve``, ``polygonize``, ``contour``, ``footprint``, ``zonal-stats``,
    ``filter``, ``simplify-coverage``, ``write``, etc.).

    Parameters
    ----------
    pipeline : str or Sequence[str]
        A GDAL pipeline specification string (e.g.,
        ``"! read in.tif ! sieve --size-threshold 10 ! polygonize ! write out.gpkg --overwrite"``)
        or a sequence of command-line tokens.
    input : DatasetReader, str, PathLike, or Sequence, optional
        Input dataset(s) or path(s) to bind to the pipeline's ``input``
        argument. Can be an open Rasterio dataset (e.g. ``DatasetReader``,
        ``WarpedVRT``, or ``MemoryFile`` dataset).
    output : str or PathLike, optional
        Output dataset path to bind to the pipeline's ``output`` argument.
        If provided and the pipeline does not already end with a ``write``
        step, ``! write`` is automatically appended.
    output_format : str, optional
        Output format driver name (e.g., ``"COG"``, ``"GTiff"``, ``"GPKG"``,
        ``"GeoJSON"``, ``"GDALG"``).

    Returns
    -------
    str or None
        The ``output-string`` produced by the pipeline if any (for example,
        when the pipeline ends with an ``info`` step), otherwise ``None``.

    Examples
    --------
    >>> from rasterio.pipeline import run
    >>> run(
    ...     "! read tests/data/shade.tif "
    ...     "! sieve --size-threshold 50 "
    ...     "! polygonize "
    ...     '! filter --where "DN = 255" '
    ...     "! simplify-coverage --tolerance 100 "
    ...     "! write /vsimem/out.gpkg --overwrite --quiet"
    ... )
    """
    return _run_pipeline(
        pipeline, input=input, output=output, output_format=output_format
    )
