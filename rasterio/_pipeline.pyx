"""GDAL 3.12+ pipeline execution and virtual dataset reader."""

include "gdal.pxi"

from collections.abc import Sequence
from contextlib import ExitStack
import logging
import os
import shlex

from libc.stdlib cimport malloc, free

from rasterio._base cimport DatasetBase
from rasterio._err import CPLE_BaseError
from rasterio._err cimport exc_wrap_int, exc_wrap_pointer
from rasterio._path import _parse_path
from rasterio.errors import GDALVersionError, RasterioIOError

log = logging.getLogger(__name__)


# Options of the raster and vector 'write' steps that consume the next token.
_WRITE_VALUE_OPTS = {
    "-f", "--of", "--format", "--output-format",
    "--co", "--creation-option",
    "--lco", "--layer-creation-option",
    "-l", "--output-layer",
    "--output-oo", "--output-open-option",
}


def _ends_with_write_step(tokens):
    """Return True if the last step of a tokenized pipeline is 'write'.

    Raises ValueError if that 'write' step names its own output, since
    the caller is about to bind one through the 'output' argument and
    GDAL reports that conflict with a misleading message.
    """
    last_sep = max((i for i, t in enumerate(tokens) if t == "!"), default=-1)
    step = tokens[last_sep + 1:]
    if not step or step[0] != "write":
        return False

    args = iter(step[1:])
    for tok in args:
        name = tok.split("=", 1)[0]
        if name in ("-o", "--output") or not tok.startswith("-"):
            raise ValueError(
                "output was given both as the output argument and in the "
                "pipeline's 'write' step; pass it in only one place."
            )
        if name in _WRITE_VALUE_OPTS and "=" not in tok:
            next(args, None)
    return True


IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 12):

    cdef GDALAlgorithmH _instantiate_pipeline_alg() except NULL:
        """Instantiate the top-level GDAL 'pipeline' algorithm."""
        cdef GDALAlgorithmRegistryH hReg = NULL
        cdef GDALAlgorithmH hAlg = NULL

        with nogil:
            hReg = GDALGetGlobalAlgorithmRegistry()
        if hReg == NULL:
            raise RasterioIOError("Failed to obtain GDAL global algorithm registry.")

        try:
            with nogil:
                hAlg = GDALAlgorithmRegistryInstantiateAlg(hReg, b"pipeline")
            hAlg = <GDALAlgorithmH>exc_wrap_pointer(hAlg)
        finally:
            with nogil:
                GDALAlgorithmRegistryRelease(hReg)

        return hAlg

    cdef void _set_alg_string_arg(
        GDALAlgorithmH hAlg, const char *arg_name, const char *val
    ) except *:
        """Set a string argument on a GDALAlgorithmH."""
        cdef GDALAlgorithmArgH hArg = NULL
        cdef int ok = 0

        with nogil:
            hArg = GDALAlgorithmGetArgNonConst(hAlg, arg_name)
        if hArg == NULL:
            raise RasterioIOError(
                f"GDAL pipeline algorithm argument '{arg_name.decode('utf-8')}' not found."
            )
        try:
            with nogil:
                ok = GDALAlgorithmArgSetAsString(hArg, val)
            exc_wrap_int(not ok)
        finally:
            with nogil:
                GDALAlgorithmArgRelease(hArg)

    cdef void _set_alg_input_arg(GDALAlgorithmH hAlg, object input_obj) except *:
        """Bind input dataset(s) or path(s) to the 'input' argument of a pipeline."""
        if input_obj is None:
            return

        cdef GDALAlgorithmArgH hArg = NULL
        cdef GDALDatasetH hds = NULL
        cdef GDALDatasetH *pahDS = NULL
        cdef char **papszNames = NULL
        cdef const char *c_path = NULL
        cdef size_t n_inputs = 0
        cdef size_t i = 0
        cdef int ok = 0

        with nogil:
            hArg = GDALAlgorithmGetArgNonConst(hAlg, b"input")
        if hArg == NULL:
            raise RasterioIOError("GDAL pipeline algorithm argument 'input' not found.")

        try:
            # Case 1: Single open DatasetBase
            if isinstance(input_obj, DatasetBase):
                hds = (<DatasetBase>input_obj).handle()
                with nogil:
                    ok = GDALAlgorithmArgSetDatasets(hArg, 1, &hds)
                exc_wrap_int(not ok)

            # Case 2: Single path / PathLike
            elif isinstance(input_obj, (str, os.PathLike)):
                vsi_path = _parse_path(input_obj).as_vsi()
                b_path = vsi_path.encode("utf-8")
                c_path = b_path
                try:
                    papszNames = CSLAddString(papszNames, c_path)
                    with nogil:
                        ok = GDALAlgorithmArgSetDatasetNames(hArg, papszNames)
                    exc_wrap_int(not ok)
                finally:
                    if papszNames != NULL:
                        CSLDestroy(papszNames)
                        papszNames = NULL

            # Case 3: Sequence of datasets or paths (e.g. for mosaic, stack, calc)
            elif isinstance(input_obj, Sequence):
                if len(input_obj) == 0:
                    raise ValueError("input sequence cannot be empty.")

                if all(isinstance(item, DatasetBase) for item in input_obj):
                    n_inputs = len(input_obj)
                    pahDS = <GDALDatasetH *>malloc(n_inputs * sizeof(GDALDatasetH))
                    if pahDS == NULL:
                        raise MemoryError("Could not allocate GDALDatasetH array.")
                    try:
                        for i in range(n_inputs):
                            pahDS[i] = (<DatasetBase>input_obj[i]).handle()
                        with nogil:
                            ok = GDALAlgorithmArgSetDatasets(hArg, n_inputs, pahDS)
                        exc_wrap_int(not ok)
                    finally:
                        free(pahDS)

                elif all(isinstance(item, (str, os.PathLike)) for item in input_obj):
                    try:
                        for item in input_obj:
                            vsi_path = _parse_path(item).as_vsi()
                            b_path = vsi_path.encode("utf-8")
                            c_path = b_path
                            papszNames = CSLAddString(papszNames, c_path)
                        with nogil:
                            ok = GDALAlgorithmArgSetDatasetNames(
                                hArg, papszNames
                            )
                        exc_wrap_int(not ok)
                    finally:
                        if papszNames != NULL:
                            CSLDestroy(papszNames)
                else:
                    raise TypeError(
                        "input sequence must contain all DatasetReader objects or all path strings/PathLikes."
                    )
            else:
                raise TypeError(
                    "input must be a DatasetReader, str, PathLike, or a sequence thereof."
                )
        finally:
            with nogil:
                GDALAlgorithmArgRelease(hArg)

    cdef void _configure_pipeline_steps(
        GDALAlgorithmH hAlg, object pipeline, bint ensure_write_step=False
    ) except *:
        """Configure the pipeline steps from a string or sequence of CLI tokens."""
        cdef char **papszArgs = NULL
        cdef const char *c_str = NULL
        cdef int ok = 0

        if isinstance(pipeline, str):
            pipe_str = pipeline.strip()
            if not pipe_str:
                raise ValueError("pipeline string cannot be empty.")
            if ensure_write_step:
                # Tokenize so that a quoted "!" is not taken as a step separator.
                try:
                    pipe_tokens = shlex.split(pipe_str)
                except ValueError:
                    pipe_tokens = pipe_str.split()
                if not _ends_with_write_step(pipe_tokens):
                    pipe_str = f"{pipe_str} ! write"
            b_pipe = pipe_str.encode("utf-8")
            c_str = b_pipe
            _set_alg_string_arg(hAlg, b"pipeline", c_str)

        elif isinstance(pipeline, Sequence):
            tokens = [str(t) for t in pipeline]
            if not tokens:
                raise ValueError("pipeline token sequence cannot be empty.")
            if ensure_write_step and not _ends_with_write_step(tokens):
                tokens = list(tokens) + ["!", "write"]
            try:
                for token in tokens:
                    b_tok = token.encode("utf-8")
                    c_str = b_tok
                    papszArgs = CSLAddString(papszArgs, c_str)
                with nogil:
                    ok = GDALAlgorithmParseCommandLineArguments(
                        hAlg, papszArgs
                    )
                try:
                    exc_wrap_int(not ok)
                except CPLE_BaseError as err:
                    raise RasterioIOError(str(err)) from err
            finally:
                if papszArgs != NULL:
                    CSLDestroy(papszArgs)
        else:
            raise TypeError(
                "pipeline must be a pipeline string or a sequence of string arguments."
            )


cdef class PipelineVRTReaderBase(DatasetReaderBase):
    """Base class for a virtual streamed GDAL pipeline dataset."""

    def __init__(self, pipeline, input=None):
        """Initialize a streamed virtual dataset from a GDAL pipeline.

        Parameters
        ----------
        pipeline : str or Sequence[str]
            GDAL pipeline specification (e.g.
            ``"read ! reproject --dst-crs=EPSG:4326 ! scale"`` or
            ``"! read in.tif ! select --band 1"``).
        input : DatasetReader, str, PathLike, or Sequence, optional
            Input dataset(s) or path(s) to bind to the pipeline's ``input``
            argument.
        """
        IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 12):
            self.mode = "r"
            self.options = {}
            self._count = 0
            self._dtypes = []
            self._block_shapes = None
            self._nodatavals = []
            self._units = ()
            self._descriptions = ()
            self._scales = ()
            self._offsets = ()
            self._crs = None
            self._gcps = None
            self._rpcs = None
            self._read = False
            self._hds = NULL

            # Keep reference to input dataset(s) so they stay alive as long as
            # the streamed pipeline dataset is open.
            self.src_dataset = input
            if isinstance(pipeline, str):
                self.name = f"PipelineVRT({pipeline.strip()})"
            else:
                self.name = f"PipelineVRT({' '.join(str(t) for t in pipeline)})"

            cdef GDALAlgorithmH hAlg = NULL
            cdef GDALAlgorithmArgH hOutArg = NULL
            cdef GDALArgDatasetValueH hVal = NULL
            cdef GDALDatasetH hds_out = NULL
            cdef int ok = 0

            hAlg = _instantiate_pipeline_alg()
            try:
                _set_alg_input_arg(hAlg, input)
                _set_alg_string_arg(hAlg, b"output-format", b"stream")
                _configure_pipeline_steps(hAlg, pipeline, ensure_write_step=False)

                try:
                    with nogil:
                        ok = GDALAlgorithmRun(hAlg, NULL, NULL)
                    exc_wrap_int(not ok)
                except CPLE_BaseError as err:
                    raise RasterioIOError(str(err)) from err

                with nogil:
                    hOutArg = GDALAlgorithmGetArg(hAlg, b"output")
                if hOutArg == NULL:
                    raise RasterioIOError(
                        "GDAL pipeline algorithm did not produce an 'output' argument."
                    )
                try:
                    with nogil:
                        hVal = GDALAlgorithmArgGetAsDatasetValue(hOutArg)
                    if hVal == NULL:
                        raise RasterioIOError(
                            "GDAL pipeline did not produce an output dataset."
                        )
                    try:
                        with nogil:
                            hds_out = GDALArgDatasetValueGetDatasetIncreaseRefCount(
                                hVal
                            )
                        hds_out = <GDALDatasetH>exc_wrap_pointer(hds_out)
                    finally:
                        with nogil:
                            GDALArgDatasetValueRelease(hVal)
                finally:
                    with nogil:
                        GDALAlgorithmArgRelease(hOutArg)

                try:
                    with nogil:
                        ok = GDALAlgorithmFinalize(hAlg)
                    exc_wrap_int(not ok)
                except CPLE_BaseError as err:
                    raise RasterioIOError(str(err)) from err

            except Exception:
                # Drop the reference taken on the output dataset above.
                if hds_out != NULL:
                    with nogil:
                        if GDALDereferenceDataset(hds_out) == 0:
                            GDALClose(hds_out)
                raise
            finally:
                with nogil:
                    GDALAlgorithmRelease(hAlg)

            if GDALGetRasterCount(hds_out) == 0:
                with nogil:
                    if GDALDereferenceDataset(hds_out) == 0:
                        GDALClose(hds_out)
                raise RasterioIOError(
                    "Pipeline output does not contain any raster bands (it may be a "
                    "vector dataset). Use rasterio.pipeline.run() with a 'write' step "
                    "for vector outputs."
                )

            self._hds = hds_out
            self._set_attrs_from_dataset_handle()
            self._env = ExitStack()
        ELSE:
            raise GDALVersionError("GDAL >= 3.12 is required for rasterio.pipeline.")


def _run_pipeline(pipeline, input=None, output=None, output_format=None):
    """Execute a GDAL pipeline to completion.

    Parameters
    ----------
    pipeline : str or Sequence[str]
        GDAL pipeline specification (e.g.,
        ``"! read in.tif ! sieve --size-threshold 10 ! polygonize ! write out.gpkg --overwrite"``).
    input : DatasetReader, str, PathLike, or Sequence, optional
        Input dataset(s) or path(s) to bind to the pipeline's ``input`` argument.
    output : str or PathLike, optional
        Output dataset path to bind to the pipeline's ``output`` argument.
        If provided and the pipeline does not end with a ``write`` step,
        ``! write`` is automatically appended.
    output_format : str, optional
        Output format driver name (e.g., ``"COG"``, ``"GTiff"``, ``"GPKG"``, ``"GDALG"``).

    Returns
    -------
    str or None
        The ``output-string`` produced by the pipeline if any (e.g., when
        ending with an ``info`` step), otherwise ``None``.
    """
    IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 12):
        cdef GDALAlgorithmH hAlg = NULL
        cdef GDALAlgorithmArgH hStrArg = NULL
        cdef const char *c_out_str = NULL
        cdef const char *c_str = NULL
        cdef int ok = 0
        cdef bint ensure_write = output is not None

        hAlg = _instantiate_pipeline_alg()
        try:
            _set_alg_input_arg(hAlg, input)

            if output is not None:
                if not isinstance(output, (str, os.PathLike)):
                    raise TypeError("output must be a str or PathLike.")
                vsi_out = _parse_path(output).as_vsi()
                b_out = vsi_out.encode("utf-8")
                c_str = b_out
                _set_alg_string_arg(hAlg, b"output", c_str)

            if output_format is not None:
                b_fmt = str(output_format).encode("utf-8")
                c_str = b_fmt
                _set_alg_string_arg(hAlg, b"output-format", c_str)

            _configure_pipeline_steps(hAlg, pipeline, ensure_write_step=ensure_write)

            try:
                with nogil:
                    ok = GDALAlgorithmRun(hAlg, NULL, NULL)
                exc_wrap_int(not ok)

                with nogil:
                    ok = GDALAlgorithmFinalize(hAlg)
                exc_wrap_int(not ok)
            except CPLE_BaseError as err:
                raise RasterioIOError(str(err)) from err

            result_str = None
            with nogil:
                hStrArg = GDALAlgorithmGetArg(hAlg, b"output-string")
            if hStrArg != NULL:
                try:
                    with nogil:
                        c_out_str = GDALAlgorithmArgGetAsString(hStrArg)
                    if c_out_str != NULL and c_out_str[0] != 0:
                        result_str = c_out_str.decode("utf-8", errors="replace")
                finally:
                    with nogil:
                        GDALAlgorithmArgRelease(hStrArg)

            return result_str
        finally:
            with nogil:
                GDALAlgorithmRelease(hAlg)
    ELSE:
        raise GDALVersionError("GDAL >= 3.12 is required for rasterio.pipeline.")
