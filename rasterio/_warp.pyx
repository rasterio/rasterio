# distutils: language = c++
"""Raster and vector warping and reprojection."""

include "gdal.pxi"

import logging
import uuid
import warnings

from affine import identity
import numpy as np

from rasterio._err import (
    CPLE_IllegalArgError, CPLE_NotSupportedError,
    CPLE_AppDefinedError, CPLE_OpenFailedError)
from rasterio import dtypes
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.errors import DriverRegistrationError, CRSError, RasterioIOError, RasterioDeprecationWarning
from rasterio.transform import Affine, from_bounds, guard_transform, tastes_like_gdal

cimport numpy as np

from rasterio._base cimport _osr_from_crs, get_driver_name, _safe_osr_release
from rasterio._err cimport exc_wrap_pointer, exc_wrap_int
from rasterio._io cimport (
    DatasetReaderBase, InMemoryRaster, in_dtype_range, io_auto)
from rasterio._features cimport GeomBuilder, OGRGeomBuilder


log = logging.getLogger(__name__)


def recursive_round(val, precision):
    """Recursively round coordinates."""
    if isinstance(val, (int, float)):
        return round(val, precision)
    else:
        return [recursive_round(part, precision) for part in val]


def _transform_geom(
        src_crs, dst_crs, geom, antimeridian_cutting, antimeridian_offset,
        precision):
    """Return a transformed geometry."""
    cdef char **options = NULL
    cdef OGRSpatialReferenceH src = NULL
    cdef OGRSpatialReferenceH dst = NULL
    cdef OGRCoordinateTransformationH transform = NULL
    cdef OGRGeometryFactory *factory = NULL
    cdef OGRGeometryH src_geom = NULL
    cdef OGRGeometryH dst_geom = NULL
    cdef int i

    src = _osr_from_crs(src_crs)
    dst = _osr_from_crs(dst_crs)

    try:
        transform = exc_wrap_pointer(OCTNewCoordinateTransformation(src, dst))
    except:
        _safe_osr_release(src)
        _safe_osr_release(dst)
        raise

    # Transform options.
    valb = str(antimeridian_offset).encode('utf-8')
    options = CSLSetNameValue(options, "DATELINEOFFSET", <const char *>valb)
    if antimeridian_cutting:
        options = CSLSetNameValue(options, "WRAPDATELINE", "YES")

    try:
        factory = new OGRGeometryFactory()
        src_geom = OGRGeomBuilder().build(geom)
        dst_geom = exc_wrap_pointer(
            factory.transformWithOptions(
                <const OGRGeometry *>src_geom,
                <OGRCoordinateTransformation *>transform,
                options))

        result = GeomBuilder().build(dst_geom)

        if precision >= 0:
            # TODO: Geometry collections.
            result['coordinates'] = recursive_round(result['coordinates'],
                                                    precision)

        return result

    finally:
        del factory
        OGR_G_DestroyGeometry(dst_geom)
        OGR_G_DestroyGeometry(src_geom)
        OCTDestroyCoordinateTransformation(transform)
        if options != NULL:
            CSLDestroy(options)
        _safe_osr_release(src)
        _safe_osr_release(dst)


cdef GDALWarpOptions * create_warp_options(
        GDALResampleAlg resampling, object src_nodata, object dst_nodata,
        int src_count, const char **options) except NULL:
    """Return a pointer to a GDALWarpOptions composed from input params
    """

    # First, we make sure we have consistent source and destination
    # nodata values. TODO: alpha bands.

    if dst_nodata is None:
        if src_nodata is not None:
            dst_nodata = src_nodata
        else:
            dst_nodata = 0

    cdef GDALWarpOptions *psWOptions = GDALCreateWarpOptions()

    # Note: warp_extras is pointed to different memory locations on every
    # call to CSLSetNameValue call below, but needs to be set here to
    # get the defaults.
    cdef char **warp_extras = psWOptions.papszWarpOptions

    # See http://www.gdal.org/structGDALWarpOptions.html#a0ed77f9917bb96c7a9aabd73d4d06e08
    # for a list of supported options. Copying unsupported options
    # is fine.

    # Use the same default nodata logic as gdalwarp.
    warp_extras = CSLSetNameValue(
        warp_extras, "UNIFIED_SRC_NODATA", "YES")

    warp_extras = CSLMerge(warp_extras, <char **>options)

    psWOptions.eResampleAlg = <GDALResampleAlg>resampling

    # Assign nodata values.
    # We don't currently support an imaginary component.

    if src_nodata is not None:
        psWOptions.padfSrcNoDataReal = <double*>CPLMalloc(src_count * sizeof(double))
        psWOptions.padfSrcNoDataImag = <double*>CPLMalloc(src_count * sizeof(double))

        for i in range(src_count):
            psWOptions.padfSrcNoDataReal[i] = float(src_nodata)
            psWOptions.padfSrcNoDataImag[i] = 0.0


    if dst_nodata is not None:
        psWOptions.padfDstNoDataReal = <double*>CPLMalloc(src_count * sizeof(double))
        psWOptions.padfDstNoDataImag = <double*>CPLMalloc(src_count * sizeof(double))

        for i in range(src_count):
            psWOptions.padfDstNoDataReal[i] = float(dst_nodata)
            psWOptions.padfDstNoDataImag[i] = 0.0

    # Important: set back into struct or values set above are lost
    # This is because CSLSetNameValue returns a new list each time
    psWOptions.papszWarpOptions = warp_extras

    # Set up band info
    if psWOptions.nBandCount == 0:
        psWOptions.nBandCount = src_count

        psWOptions.panSrcBands = <int*>CPLMalloc(src_count * sizeof(int))
        psWOptions.panDstBands = <int*>CPLMalloc(src_count * sizeof(int))

        for i in range(src_count):
            psWOptions.panSrcBands[i] = i + 1
            psWOptions.panDstBands[i] = i + 1

    return psWOptions


def _reproject(
        source, destination,
        src_transform=None,
        gcps=None,
        src_crs=None,
        src_nodata=None,
        dst_transform=None,
        dst_crs=None,
        dst_nodata=None,
        resampling=Resampling.nearest,
        init_dest_nodata=True,
        num_threads=1,
        **kwargs):
    """
    Reproject a source raster to a destination raster.

    If the source and destination are ndarrays, coordinate reference
    system definitions and affine transformation parameters are required
    for reprojection.

    If the source and destination are rasterio Bands, shorthand for
    bands of datasets on disk, the coordinate reference systems and
    transforms will be read from the appropriate datasets.

    Parameters
    ------------
    source: ndarray or rasterio Band
        Source raster.
    destination: ndarray or rasterio Band
        Target raster.
    src_transform: affine.Affine(), optional
        Source affine transformation.  Required if source and destination
        are ndarrays.  Will be derived from source if it is a rasterio Band.
    gcps: sequence of `GroundControlPoint` instances, optional
        Ground control points for the source. May be used in place of
        src_transform.
    src_crs: dict, optional
        Source coordinate reference system, in rasterio dict format.
        Required if source and destination are ndarrays.
        Will be derived from source if it is a rasterio Band.
        Example: {'init': 'EPSG:4326'}
    src_nodata: int or float, optional
        The source nodata value.  Pixels with this value will not be used
        for interpolation.  If not set, it will be default to the
        nodata value of the source image if a masked ndarray or rasterio band,
        if available.
    dst_transform: affine.Affine(), optional
        Target affine transformation.  Required if source and destination
        are ndarrays.  Will be derived from target if it is a rasterio Band.
    dst_crs: dict, optional
        Target coordinate reference system.  Required if source and destination
        are ndarrays.  Will be derived from target if it is a rasterio Band.
    dst_nodata: int or float, optional
        The nodata value used to initialize the destination; it will remain
        in all areas not covered by the reprojected source.  Defaults to the
        nodata value of the destination image (if set), the value of
        src_nodata, or 0 (gdal default).
    resampling: int
        Resampling method to use.  One of the following:
            Resampling.nearest,
            Resampling.bilinear,
            Resampling.cubic,
            Resampling.cubic_spline,
            Resampling.lanczos,
            Resampling.average,
            Resampling.mode
    init_dest_nodata: bool
        Flag to specify initialization of nodata in destination;
        prevents overwrite of previous warps. Defaults to True.
    num_threads: int
        Number of worker threads.
    kwargs:  dict, optional
        Additional arguments passed to both the image to image
        transformer GDALCreateGenImgProjTransformer2() (for example,
        MAX_GCP_ORDER=2) and to the Warper (for example,
        INIT_DEST=NO_DATA).

    Returns
    ---------
    out: None
        Output is written to destination.
    """
    cdef int retval
    cdef int rows
    cdef int cols
    cdef int src_count
    cdef GDALDriverH driver = NULL
    cdef GDALDatasetH src_dataset = NULL
    cdef GDALDatasetH dst_dataset = NULL
    cdef GDALAccess GA
    cdef double gt[6]
    cdef char *srcwkt = NULL
    cdef char *dstwkt= NULL
    cdef OGRSpatialReferenceH osr = NULL
    cdef char **warp_extras = NULL
    cdef const char* pszWarpThread = NULL
    cdef int i
    cdef double tolerance = 0.125
    cdef GDAL_GCP *gcplist = NULL
    cdef void *hTransformArg = NULL
    cdef GDALTransformerFunc pfnTransformer = NULL
    cdef GDALWarpOptions *psWOptions = NULL

    # If working with identity transform, assume it is crs-less data
    # and that translating the matrix very slightly will avoid #674
    eps = 1e-100

    if src_transform:

        src_transform = guard_transform(src_transform)
        # if src_transform is like `identity` with positive or negative `e`,
        # translate matrix very slightly to avoid #674 and #1272.
        if src_transform.almost_equals(identity) or src_transform.almost_equals(Affine(1, 0, 0, 0, -1, 0)):
            src_transform = src_transform.translation(eps, eps)
        src_transform = src_transform.to_gdal()

    if dst_transform:

        dst_transform = guard_transform(dst_transform)
        if dst_transform.almost_equals(identity) or dst_transform.almost_equals(Affine(1, 0, 0, 0, -1, 0)):
            dst_transform = dst_transform.translation(eps, eps)
        dst_transform = dst_transform.to_gdal()

    # Validate nodata values immediately.
    if src_nodata is not None:
        if not in_dtype_range(src_nodata, source.dtype):
            raise ValueError("src_nodata must be in valid range for "
                             "source dtype")

    if dst_nodata is not None:
        if not in_dtype_range(dst_nodata, destination.dtype):
            raise ValueError("dst_nodata must be in valid range for "
                             "destination dtype")

    # If the source is an ndarray, we copy to a MEM dataset.
    # We need a src_transform and src_dst in this case. These will
    # be copied to the MEM dataset.
    if dtypes.is_ndarray(source):
        # Convert 2D single-band arrays to 3D multi-band.
        if len(source.shape) == 2:
            source = source.reshape(1, *source.shape)
        src_count = source.shape[0]
        src_bidx = range(1, src_count + 1)
        rows = source.shape[1]
        cols = source.shape[2]
        dtype = np.dtype(source.dtype).name

        if src_nodata is None and hasattr(source, 'fill_value'):
            # source is a masked array
            src_nodata = source.fill_value

        try:
            driver = exc_wrap_pointer(GDALGetDriverByName("MEM"))
        except:
            raise DriverRegistrationError(
                "'MEM' driver not found. Check that this call is contained "
                "in a `with rasterio.Env()` or `with rasterio.open()` "
                "block.")

        datasetname = str(uuid.uuid4()).encode('utf-8')
        src_dataset = exc_wrap_pointer(
            GDALCreate(driver, <const char *>datasetname, cols, rows,
                       src_count, dtypes.dtype_rev[dtype], NULL))

        GDALSetDescription(
            src_dataset, "Temporary source dataset for _reproject()")

        log.debug("Created temp source dataset")

        try:
            src_osr = _osr_from_crs(src_crs)
            OSRExportToWkt(src_osr, &srcwkt)

            if src_transform:
                for i in range(6):
                    gt[i] = src_transform[i]

                exc_wrap_int(GDALSetGeoTransform(src_dataset, gt))

                exc_wrap_int(GDALSetProjection(src_dataset, srcwkt))

                log.debug("Set CRS on temp source dataset: %s", srcwkt)

            elif gcps:
                gcplist = <GDAL_GCP *>CPLMalloc(len(gcps) * sizeof(GDAL_GCP))
                try:
                    for i, obj in enumerate(gcps):
                        ident = str(i).encode('utf-8')
                        info = "".encode('utf-8')
                        gcplist[i].pszId = ident
                        gcplist[i].pszInfo = info
                        gcplist[i].dfGCPPixel = obj.col
                        gcplist[i].dfGCPLine = obj.row
                        gcplist[i].dfGCPX = obj.x
                        gcplist[i].dfGCPY = obj.y
                        gcplist[i].dfGCPZ = obj.z or 0.0

                    exc_wrap_int(GDALSetGCPs(src_dataset, len(gcps), gcplist, srcwkt))
                finally:
                    CPLFree(gcplist)

        finally:
            CPLFree(srcwkt)
            _safe_osr_release(src_osr)

        # Copy arrays to the dataset.
        exc_wrap_int(io_auto(source, src_dataset, 1))

        log.debug("Wrote array to temp source dataset")

    # If the source is a rasterio MultiBand, no copy necessary.
    # A MultiBand is a tuple: (dataset, bidx, dtype, shape(2d)).
    elif isinstance(source, tuple):
        rdr, src_bidx, dtype, shape = source
        if isinstance(src_bidx, int):
            src_bidx = [src_bidx]
        src_count = len(src_bidx)
        rows, cols = shape
        src_dataset = (<DatasetReaderBase?>rdr).handle()
        if src_nodata is None:
            src_nodata = rdr.nodata
    else:
        raise ValueError("Invalid source")

    # Next, do the same for the destination raster.
    if dtypes.is_ndarray(destination):
        if len(destination.shape) == 2:
            destination = destination.reshape(1, *destination.shape)
            dst_bidx = [1]
        else:
            dst_bidx = src_bidx

        if destination.shape[0] != src_count:
            raise ValueError("Destination's shape is invalid")

        try:
            driver = exc_wrap_pointer(GDALGetDriverByName("MEM"))
        except:
            raise DriverRegistrationError(
                "'MEM' driver not found. Check that this call is contained "
                "in a `with rasterio.Env()` or `with rasterio.open()` "
                "block.")

        _, rows, cols = destination.shape

        datasetname = str(uuid.uuid4()).encode('utf-8')
        dst_dataset = exc_wrap_pointer(
            GDALCreate(driver, <const char *>datasetname, cols, rows,
                src_count,
                dtypes.dtype_rev[np.dtype(destination.dtype).name], NULL))

        GDALSetDescription(
            dst_dataset, "Temporary destination dataset for _reproject()")

        log.debug("Created temp destination dataset.")

        for i in range(6):
            gt[i] = dst_transform[i]

        exc_wrap_int(GDALSetGeoTransform(dst_dataset, gt))

        try:
            dst_osr = _osr_from_crs(dst_crs)
            OSRExportToWkt(dst_osr, &dstwkt)

            log.debug("CRS for temp destination dataset: %s.", dstwkt)

            exc_wrap_int(GDALSetProjection(dst_dataset, dstwkt))
        finally:
            CPLFree(dstwkt)
            _safe_osr_release(dst_osr)

        exc_wrap_int(io_auto(destination, dst_dataset, 1))

        log.debug("Wrote array to temp output dataset")

        if dst_nodata is None and hasattr(destination, "fill_value"):
            # destination is a masked array
            dst_nodata = destination.fill_value

    elif isinstance(destination, tuple):
        udr, dst_bidx, _, _ = destination
        if isinstance(dst_bidx, int):
            dst_bidx = [dst_bidx]
        udr = destination.ds
        dst_dataset = (<DatasetReaderBase?>udr).handle()
        if dst_nodata is None:
            dst_nodata = udr.nodata
    else:
        raise ValueError("Invalid destination")

    # Set up GDALCreateGenImgProjTransformer2 keyword arguments.
    cdef char **imgProjOptions = NULL
    CSLSetNameValue(imgProjOptions, "GCPS_OK", "TRUE")

    # See http://www.gdal.org/gdal__alg_8h.html#a94cd172f78dbc41d6f407d662914f2e3
    # for a list of supported options. I (Sean) don't see harm in
    # copying all the function's keyword arguments to the image to
    # image transformer options mapping; unsupported options should be
    # okay.
    for key, val in kwargs.items():
        key = key.upper().encode('utf-8')
        val = str(val).upper().encode('utf-8')
        imgProjOptions = CSLSetNameValue(
            imgProjOptions, <const char *>key, <const char *>val)

    try:
        hTransformArg = exc_wrap_pointer(
            GDALCreateGenImgProjTransformer2(
                src_dataset, dst_dataset, imgProjOptions))
        hTransformArg = exc_wrap_pointer(
            GDALCreateApproxTransformer(
                GDALGenImgProjTransform, hTransformArg, tolerance))
        pfnTransformer = GDALApproxTransform
        GDALApproxTransformerOwnsSubtransformer(hTransformArg, 1)

        log.debug("Created transformer and options.")

    except:
        GDALDestroyApproxTransformer(hTransformArg)
        CPLFree(imgProjOptions)
        raise

    # Note: warp_extras is pointed to different memory locations on every
    # call to CSLSetNameValue call below, but needs to be set here to
    # get the defaults.
    # warp_extras = psWOptions.papszWarpOptions

    valb = str(num_threads).encode('utf-8')
    warp_extras = CSLSetNameValue(warp_extras, "NUM_THREADS", <const char *>valb)

    log.debug("Setting NUM_THREADS option: %d", num_threads)

    if init_dest_nodata:
        warp_extras = CSLSetNameValue(warp_extras, "INIT_DEST", "NO_DATA")

    # See http://www.gdal.org/structGDALWarpOptions.html#a0ed77f9917bb96c7a9aabd73d4d06e08
    # for a list of supported options. Copying unsupported options
    # is fine.
    for key, val in kwargs.items():
        key = key.upper().encode('utf-8')
        val = str(val).upper().encode('utf-8')
        warp_extras = CSLSetNameValue(
            warp_extras, <const char *>key, <const char *>val)

    psWOptions = create_warp_options(
        <GDALResampleAlg>resampling, src_nodata,
        dst_nodata, src_count, <const char **>warp_extras)

    psWOptions.pfnTransformer = pfnTransformer
    psWOptions.pTransformerArg = hTransformArg
    psWOptions.hSrcDS = src_dataset
    psWOptions.hDstDS = dst_dataset
    psWOptions.nBandCount = src_count
    psWOptions.panSrcBands = <int *>CPLMalloc(src_count*sizeof(int))
    psWOptions.panDstBands = <int *>CPLMalloc(src_count*sizeof(int))

    for i in range(src_count):
        psWOptions.panSrcBands[i] = src_bidx[i]
        psWOptions.panDstBands[i] = dst_bidx[i]

    log.debug("Set transformer options")

    # Now that the transformer and warp options are set up, we init
    # and run the warper.
    cdef GDALWarpOperation oWarper
    try:
        exc_wrap_int(oWarper.Initialize(psWOptions))
        rows, cols = destination.shape[-2:]

        log.debug(
            "Chunk and warp window: %d, %d, %d, %d.",
            0, 0, cols, rows)

        if num_threads > 1:
            with nogil:
                oWarper.ChunkAndWarpMulti(0, 0, cols, rows)
        else:
            with nogil:
                oWarper.ChunkAndWarpImage(0, 0, cols, rows)

        if dtypes.is_ndarray(destination):
            exc_wrap_int(io_auto(destination, dst_dataset, 0))

            if dst_dataset != NULL:
                GDALClose(dst_dataset)

    # Clean up transformer, warp options, and dataset handles.
    finally:
        GDALDestroyApproxTransformer(hTransformArg)
        GDALDestroyWarpOptions(psWOptions)
        CPLFree(imgProjOptions)
        if dtypes.is_ndarray(source):
            if src_dataset != NULL:
                GDALClose(src_dataset)


def _calculate_default_transform(src_crs, dst_crs, width, height,
                                 left=None, bottom=None, right=None, top=None,
                                 gcps=None, **kwargs):
    """Wraps GDAL's algorithm."""
    cdef void *hTransformArg = NULL
    cdef int npixels = 0
    cdef int nlines = 0
    cdef double extent[4]
    cdef double geotransform[6]
    cdef OGRSpatialReferenceH osr = NULL
    cdef char *wkt = NULL
    cdef InMemoryRaster temp = None

    extent[:] = [0.0, 0.0, 0.0, 0.0]
    geotransform[:] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    # Make an in-memory raster dataset we can pass to
    # GDALCreateGenImgProjTransformer().

    if all(x is not None for x in (left, bottom, right, top)):
        transform = from_bounds(left, bottom, right, top, width, height)
    elif any(x is not None for x in (left, bottom, right, top)):
        raise ValueError(
            "Some, but not all, bounding box parameters were provided.")
    else:
        transform = None

    osr = _osr_from_crs(dst_crs)
    OSRExportToWkt(osr, &wkt)
    _safe_osr_release(osr)

    with InMemoryRaster(width=width, height=height, transform=transform,
                        gcps=gcps, crs=src_crs) as temp:
        try:
            hTransformArg = exc_wrap_pointer(
                GDALCreateGenImgProjTransformer(
                    temp._hds, NULL, NULL, wkt, 1, 1000.0,0))
            exc_wrap_int(
                GDALSuggestedWarpOutput2(
                    temp._hds, GDALGenImgProjTransform, hTransformArg,
                    geotransform, &npixels, &nlines, extent, 0))

            log.debug("Created transformer and warp output.")

        except CPLE_NotSupportedError as err:
            raise CRSError(err.errmsg)

        except CPLE_AppDefinedError as err:
            if "Reprojection failed" in str(err):
                # This "exception" should be treated as a debug msg, not error
                # "Reprojection failed, err = -14, further errors will be
                # suppressed on the transform object."
                log.info("Encountered points outside of valid dst crs region")
                pass
            else:
                raise err
        finally:
            if wkt != NULL:
                CPLFree(wkt)
            if hTransformArg != NULL:
                GDALDestroyGenImgProjTransformer(hTransformArg)

    # Convert those modified arguments to Python values.
    dst_affine = Affine.from_gdal(*[geotransform[i] for i in range(6)])
    dst_width = npixels
    dst_height = nlines

    return dst_affine, dst_width, dst_height


cdef class WarpedVRTReaderBase(DatasetReaderBase):

    def __init__(self, src_dataset, src_crs=None, dst_crs=None,
                 resampling=Resampling.nearest, tolerance=0.125,
                 src_nodata=None, dst_nodata=None, dst_width=None,
                 dst_height=None, src_transform=None, dst_transform=None,
                 init_dest_nodata=True, **warp_extras):

        self.mode = 'r'
        self.options = {}
        self._count = 0
        self._closed = True
        self._dtypes = []
        self._block_shapes = None
        self._nodatavals = []
        self._units = ()
        self._descriptions = ()
        self._crs = None
        self._gcps = None
        self._read = False

        # kwargs become warp options.
        self.src_dataset = src_dataset
        self.src_crs = src_crs
        self.src_transform = src_transform
        self.name = "WarpedVRT({})".format(src_dataset.name)
        self.dst_crs = dst_crs
        self.resampling = resampling
        self.tolerance = tolerance

        self.src_nodata = self.src_dataset.nodata if src_nodata is None else src_nodata
        self.dst_nodata = self.src_nodata if dst_nodata is None else dst_nodata
        self.dst_width = dst_width
        self.dst_height = dst_height
        self.dst_transform = dst_transform
        self.warp_extras = warp_extras.copy()
        if init_dest_nodata is True and 'init_dest' not in warp_extras:
            self.warp_extras['init_dest'] = 'NO_DATA'

        cdef GDALDriverH driver = NULL
        cdef GDALDatasetH hds = NULL
        cdef GDALDatasetH hds_warped = NULL
        cdef const char *cypath = NULL
        cdef char *src_crs_wkt = NULL
        cdef char *dst_crs_wkt = NULL
        cdef OGRSpatialReferenceH osr = NULL
        cdef char **c_warp_extras = NULL
        cdef GDALWarpOptions *psWOptions = NULL
        cdef float c_tolerance = tolerance
        cdef GDALResampleAlg c_resampling = resampling
        cdef int c_width = dst_width or 0
        cdef int c_height = dst_height or 0
        cdef double src_gt[6]
        cdef double dst_gt[6]
        cdef void *hTransformArg = NULL

        hds = (<DatasetReaderBase?>self.src_dataset).handle()
        hds = exc_wrap_pointer(hds)

        if not self.src_transform:
            self.src_transform = self.src_dataset.transform

        if self.dst_transform:
            t = self.src_transform.to_gdal()
            for i in range(6):
                src_gt[i] = t[i]

            t = self.dst_transform.to_gdal()
            for i in range(6):
                dst_gt[i] = t[i]

        if not self.src_crs:
            self.src_crs = self.src_dataset.crs

        # Convert CRSes to C WKT strings.
        try:
            osr = _osr_from_crs(self.src_crs)
            OSRExportToWkt(osr, &src_crs_wkt)
        finally:
            if osr != NULL:
                OSRRelease(osr)
            osr = NULL

        if self.dst_crs is not None:
            try:
                osr = _osr_from_crs(self.dst_crs)
                OSRExportToWkt(osr, &dst_crs_wkt)
            finally:
                _safe_osr_release(osr)

        log.debug("Exported CRS to WKT.")

        log.debug("Warp_extras: %r", self.warp_extras)

        for key, val in self.warp_extras.items():
            key = key.upper().encode('utf-8')
            val = str(val).upper().encode('utf-8')
            c_warp_extras = CSLSetNameValue(
                c_warp_extras, <const char *>key, <const char *>val)

        psWOptions = create_warp_options(
            <GDALResampleAlg>c_resampling, self.src_nodata,
            self.dst_nodata,
            GDALGetRasterCount(hds), <const char **>c_warp_extras)

        try:
            if dst_width and dst_height and dst_transform:
                # set up transform args (otherwise handled in
                # GDALAutoCreateWarpedVRT)
                try:
                    hTransformArg = exc_wrap_pointer(
                        GDALCreateGenImgProjTransformer3(
                            src_crs_wkt, src_gt, dst_crs_wkt, dst_gt))
                    if c_tolerance > 0.0:
                        hTransformArg = exc_wrap_pointer(
                            GDALCreateApproxTransformer(
                                GDALGenImgProjTransform,
                                hTransformArg,
                                c_tolerance))

                        psWOptions.pfnTransformer = GDALApproxTransform

                        GDALApproxTransformerOwnsSubtransformer(
                            hTransformArg, 1)

                    log.debug("Created transformer and options.")
                    psWOptions.pTransformerArg = hTransformArg
                except Exception:
                    GDALDestroyApproxTransformer(hTransformArg)
                    raise

                psWOptions.hSrcDS = hds

                with nogil:
                    hds_warped = GDALCreateWarpedVRT(
                        hds, c_width, c_height, dst_gt, psWOptions)
                    GDALSetProjection(hds_warped, dst_crs_wkt)
                self._hds = exc_wrap_pointer(hds_warped)
            else:
                with nogil:
                    hds_warped = GDALAutoCreateWarpedVRT(
                        hds, NULL, dst_crs_wkt, c_resampling,
                        c_tolerance, psWOptions)
                self._hds = exc_wrap_pointer(hds_warped)
        except CPLE_OpenFailedError as err:
            raise RasterioIOError(err.errmsg)
        finally:
            CPLFree(dst_crs_wkt)
            CSLDestroy(c_warp_extras)
            GDALDestroyWarpOptions(psWOptions)

        self._set_attrs_from_dataset_handle()

        # This attribute will be used by read().
        self._nodatavals = [
            self.src_nodata for i in self.src_dataset.indexes]

    def get_crs(self):
        warnings.warn("get_crs() will be removed in 1.0", RasterioDeprecationWarning)
        return self.crs

    @property
    def crs(self):
        """The dataset's coordinate reference system"""
        return self.dst_crs

    def start(self):
        """Starts the VRT's life cycle."""
        log.debug("Dataset %r is started.", self)

    def stop(self):
        """Ends the VRT's life cycle"""
        if self._hds != NULL:
            GDALClose(self._hds)
        self._hds = NULL
