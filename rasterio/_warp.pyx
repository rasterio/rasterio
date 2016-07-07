# distutils: language = c++
"""Raster and vector warping and reprojection."""

from enum import IntEnum
import logging
import uuid

import numpy as np

from rasterio._err import (
    CPLErrors, GDALError, CPLE_NotSupportedError, CPLE_AppDefinedError)
from rasterio import dtypes
from rasterio.enums import Resampling
from rasterio.errors import DriverRegistrationError, CRSError
from rasterio.transform import Affine, from_bounds

cimport numpy as np

from rasterio._base cimport _osr_from_crs as osr_from_crs
from rasterio._gdal cimport (
    CSLSetNameValue, CSLDestroy, GDALApproxTransform,
    GDALApproxTransformerOwnsSubtransformer, GDALClose, GDALCreate,
    GDALCreateApproxTransformer, GDALCreateGenImgProjTransformer,
    GDALCreateWarpOptions, GDALDestroyApproxTransformer,
    GDALDestroyGenImgProjTransformer, GDALDestroyWarpOptions,
    GDALGenImgProjTransform, GDALGetDriverByName, GDALResampleAlg,
    GDALSetDescription, GDALSetGeoTransform, GDALSetProjection,
    GDALSuggestedWarpOutput2, OCTDestroyCoordinateTransformation,
    OCTNewCoordinateTransformation, OSRDestroySpatialReference,
    OSRExportToWkt)
from rasterio._io cimport (
    DatasetReaderBase, InMemoryRaster, in_dtype_range, io_auto)
from rasterio._features cimport GeomBuilder, OGRGeomBuilder
from rasterio._ogr cimport OGR_G_DestroyGeometry

include "gdal.pxi"


log = logging.getLogger(__name__)


def tastes_like_gdal(t):
    return t[2] == t[4] == 0.0 and t[1] > 0 and t[5] < 0


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

    src = osr_from_crs(src_crs)
    dst = osr_from_crs(dst_crs)

    try:
        with CPLErrors() as cple:
            transform = OCTNewCoordinateTransformation(src, dst)
    except:
        OSRDestroySpatialReference(src)
        OSRDestroySpatialReference(dst)
        raise

    # Transform options.
    valb = str(antimeridian_offset).encode('utf-8')
    options = CSLSetNameValue(options, "DATELINEOFFSET", <const char *>valb)
    if antimeridian_cutting:
        options = CSLSetNameValue(options, "WRAPDATELINE", "YES")

    try:
        factory = new OGRGeometryFactory()
        src_geom = OGRGeomBuilder().build(geom)
        with CPLErrors() as cple:
            dst_geom = factory.transformWithOptions(
                    <const OGRGeometry *>src_geom,
                    <OGRCoordinateTransformation *>transform,
                    options)
            cple.check()

        result = GeomBuilder().build(dst_geom)

        if precision >= 0:
            if result['type'] == 'Point':
                x, y = result['coordinates']
                x = round(x, precision)
                y = round(y, precision)
                new_coords = [x, y]
            elif result['type'] in ['LineString', 'MultiPoint']:
                xp, yp = zip(*result['coordinates'])
                xp = [round(v, precision) for v in xp]
                yp = [round(v, precision) for v in yp]
                new_coords = list(zip(xp, yp))
            elif result['type'] in ['Polygon', 'MultiLineString']:
                new_coords = []
                for piece in result['coordinates']:
                    xp, yp = zip(*piece)
                    xp = [round(v, precision) for v in xp]
                    yp = [round(v, precision) for v in yp]
                    new_coords.append(list(zip(xp, yp)))
            elif result['type'] == 'MultiPolygon':
                parts = result['coordinates']
                new_coords = []
                for part in parts:
                    inner_coords = []
                    for ring in part:
                        xp, yp = zip(*ring)
                        xp = [round(v, precision) for v in xp]
                        yp = [round(v, precision) for v in yp]
                        inner_coords.append(list(zip(xp, yp)))
                    new_coords.append(inner_coords)
            result['coordinates'] = new_coords

        return result

    finally:
        del factory
        OGR_G_DestroyGeometry(dst_geom)
        OGR_G_DestroyGeometry(src_geom)
        OCTDestroyCoordinateTransformation(transform)
        if options != NULL:
            CSLDestroy(options)
        OSRDestroySpatialReference(src)
        OSRDestroySpatialReference(dst)


def _reproject(
        source, destination,
        src_transform=None,
        src_crs=None,
        src_nodata=None,
        dst_transform=None,
        dst_crs=None,
        dst_nodata=None,
        resampling=Resampling.nearest,
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
    src_transform: affine transform object, optional
        Source affine transformation.  Required if source and destination
        are ndarrays.  Will be derived from source if it is a rasterio Band.
    src_crs: dict, optional
        Source coordinate reference system, in rasterio dict format.
        Required if source and destination are ndarrays.
        Will be derived from source if it is a rasterio Band.
        Example: {'init': 'EPSG:4326'}
    src_nodata: int or float, optional
        The source nodata value.  Pixels with this value will not be used
        for interpolation.  If not set, it will be default to the
        nodata value of the source image if a masked ndarray or rasterio band,
        if available.  Must be provided if dst_nodata is not None.
    dst_transform: affine transform object, optional
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
    num_threads: int
        Number of worker threads.
    kwargs:  dict, optional
        Additional arguments passed to transformation function.

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
    cdef GDALDatasetH indataset = NULL
    cdef GDALDatasetH outdataset = NULL
    cdef GDALAccess GA
    cdef double gt[6]
    cdef char *srcwkt = NULL
    cdef char *dstwkt= NULL
    cdef OGRSpatialReferenceH osr = NULL
    cdef char **warp_extras = NULL
    cdef const char* pszWarpThread = NULL
    cdef int i
    cdef double tolerance = 0.125

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
            with CPLErrors() as cple:
                driver = GDALGetDriverByName("MEM")
                cple.check()
        except:
            raise DriverRegistrationError(
                "'MEM' driver not found. Check that this call is contained "
                "in a `with rasterio.Env()` or `with rasterio.open()` "
                "block.")

        try:
            with CPLErrors() as cple:
                datasetname = str(uuid.uuid4()).encode('utf-8')
                indataset = GDALCreate(
                    driver, <const char *>datasetname, cols, rows,
                    src_count, dtypes.dtype_rev[dtype], NULL)
                cple.check()
        except:
            raise
        GDALSetDescription(
            indataset, "Temporary source dataset for _reproject()")
        log.debug("Created temp source dataset")

        for i in range(6):
            gt[i] = src_transform[i]
        retval = GDALSetGeoTransform(indataset, gt)
        log.debug("Set transform on temp source dataset: %d", retval)

        try:
            osr = osr_from_crs(src_crs)
            OSRExportToWkt(osr, &srcwkt)
            GDALSetProjection(indataset, srcwkt)
            log.debug("Set CRS on temp source dataset: %s", srcwkt)
        finally:
            CPLFree(srcwkt)
            OSRDestroySpatialReference(osr)

        # Copy arrays to the dataset.
        retval = io_auto(source, indataset, 1)
        # TODO: handle errors (by retval).
        log.debug("Wrote array to temp source dataset")

    # If the source is a rasterio MultiBand, no copy necessary.
    # A MultiBand is a tuple: (dataset, bidx, dtype, shape(2d)).
    elif isinstance(source, tuple):
        rdr, src_bidx, dtype, shape = source
        if isinstance(src_bidx, int):
            src_bidx = [src_bidx]
        src_count = len(src_bidx)
        rows, cols = shape
        indataset = (<DatasetReaderBase?>rdr).handle()
        if src_nodata is None:
            src_nodata = rdr.nodata
    else:
        raise ValueError("Invalid source")

    # Next, do the same for the destination raster.
    if dtypes.is_ndarray(destination):
        if len(destination.shape) == 2:
            destination = destination.reshape(1, *destination.shape)
        if destination.shape[0] != src_count:
            raise ValueError("Destination's shape is invalid")
        dst_bidx = src_bidx

        try:
            with CPLErrors() as cple:
                driver = GDALGetDriverByName("MEM")
                cple.check()
        except:
            raise DriverRegistrationError(
                "'MEM' driver not found. Check that this call is contained "
                "in a `with rasterio.Env()` or `with rasterio.open()` "
                "block.")

        _, rows, cols = destination.shape
        try:
            with CPLErrors() as cple:
                datasetname = str(uuid.uuid4()).encode('utf-8')
                outdataset = GDALCreate(
                    driver, <const char *>datasetname, cols, rows, src_count,
                    dtypes.dtype_rev[np.dtype(destination.dtype).name], NULL)
                cple.check()
        except:
            raise
        GDALSetDescription(
            outdataset, "Temporary destination dataset for _reproject()")
        log.debug("Created temp destination dataset.")

        for i in range(6):
            gt[i] = dst_transform[i]

        if not GDALError.none == GDALSetGeoTransform(outdataset, gt):
            raise ValueError(
                "Failed to set transform on temp destination dataset.")

        try:
            osr = osr_from_crs(dst_crs)
            OSRExportToWkt(osr, &dstwkt)
            log.debug("CRS for temp destination dataset: %s.", dstwkt)
            if not GDALError.none == GDALSetProjection(
                    outdataset, dstwkt):
                raise ("Failed to set projection on temp destination dataset.")
        finally:
            OSRDestroySpatialReference(osr)
            CPLFree(dstwkt)

        if dst_nodata is None and hasattr(destination, "fill_value"):
            # destination is a masked array
            dst_nodata = destination.fill_value

    elif isinstance(destination, tuple):
        udr, dst_bidx, _, _ = destination
        if isinstance(dst_bidx, int):
            dst_bidx = [dst_bidx]
        udr = destination.ds
        outdataset = (<DatasetReaderBase?>udr).handle()
        if dst_nodata is None:
            dst_nodata = udr.nodata
    else:
        raise ValueError("Invalid destination")

    cdef void *hTransformArg = NULL
    cdef GDALTransformerFunc pfnTransformer = NULL
    cdef GDALWarpOptions *psWOptions = NULL

    try:
        with CPLErrors() as cple:
            hTransformArg = GDALCreateGenImgProjTransformer(
                indataset, NULL, outdataset, NULL, 1, 1000.0, 0)
            hTransformArg = GDALCreateApproxTransformer(
                GDALGenImgProjTransform, hTransformArg, tolerance)
            pfnTransformer = GDALApproxTransform
            GDALApproxTransformerOwnsSubtransformer(hTransformArg, 1)
            cple.check()
            psWOptions = GDALCreateWarpOptions()
            cple.check()
        log.debug("Created transformer and options.")
    except:
        GDALDestroyApproxTransformer(hTransformArg)
        GDALDestroyWarpOptions(psWOptions)
        raise

    # Note: warp_extras is pointed to different memory locations on every
    # call to CSLSetNameValue call below, but needs to be set here to
    # get the defaults.
    warp_extras = psWOptions.papszWarpOptions

    valb = str(num_threads).encode('utf-8')
    warp_extras = CSLSetNameValue(warp_extras, "NUM_THREADS", <const char *>valb)
    log.debug("Setting NUM_THREADS option: %d", num_threads)

    for k, v in kwargs.items():
        k, v = k.upper(), str(v).upper()
        keyb = k.encode('utf-8')
        valb = v.encode('utf-8')
        warp_extras = CSLSetNameValue(
            warp_extras, <const char *>keyb, <const char *>valb)
        log.debug("Setting warp option  %s: %s" % (k, v))

    log.debug("Created warp options")

    psWOptions.eResampleAlg = <GDALResampleAlg>resampling

    # Set src_nodata and dst_nodata
    if src_nodata is None and dst_nodata is not None:
        psWOptions.papszWarpOptions = warp_extras
        GDALDestroyApproxTransformer(hTransformArg)
        GDALDestroyWarpOptions(psWOptions)
        raise ValueError("src_nodata must be provided because dst_nodata "
                         "is not None")
    log.debug("src_nodata: %s" % src_nodata)

    if dst_nodata is None:
        if src_nodata is not None:
            dst_nodata = src_nodata
        else:
            dst_nodata = 0  # GDAL default
    log.debug("dst_nodata: %s" % dst_nodata)

    # Validate nodata values
    if src_nodata is not None:
        if not in_dtype_range(src_nodata, source.dtype):
            psWOptions.papszWarpOptions = warp_extras
            GDALDestroyApproxTransformer(hTransformArg)
            GDALDestroyWarpOptions(psWOptions)
            raise ValueError("src_nodata must be in valid range for "
                            "source dtype")

        psWOptions.padfSrcNoDataReal = <double*>CPLMalloc(
            src_count * sizeof(double))
        psWOptions.padfSrcNoDataImag = <double*>CPLMalloc(
            src_count * sizeof(double))
        for i in range(src_count):
            psWOptions.padfSrcNoDataReal[i] = src_nodata
            psWOptions.padfSrcNoDataImag[i] = 0.0
        warp_extras = CSLSetNameValue(
            warp_extras, "UNIFIED_SRC_NODATA", "YES")


    if dst_nodata is not None and not in_dtype_range(
            dst_nodata, destination.dtype):
        psWOptions.papszWarpOptions = warp_extras
        GDALDestroyApproxTransformer(hTransformArg)
        GDALDestroyWarpOptions(psWOptions)
        raise ValueError("dst_nodata must be in valid range for "
                         "destination dtype")

    psWOptions.padfDstNoDataReal = <double*>CPLMalloc(src_count * sizeof(double))
    psWOptions.padfDstNoDataImag = <double*>CPLMalloc(src_count * sizeof(double))
    for i in range(src_count):
        psWOptions.padfDstNoDataReal[i] = dst_nodata
        psWOptions.padfDstNoDataImag[i] = 0.0
    warp_extras = CSLSetNameValue(warp_extras, "INIT_DEST", "NO_DATA")

    # Important: set back into struct or values set above are lost
    # This is because CSLSetNameValue returns a new list each time
    psWOptions.papszWarpOptions = warp_extras

    psWOptions.pfnTransformer = pfnTransformer
    psWOptions.pTransformerArg = hTransformArg
    psWOptions.hSrcDS = indataset
    psWOptions.hDstDS = outdataset
    psWOptions.nBandCount = src_count
    psWOptions.panSrcBands = <int *>CPLMalloc(src_count*sizeof(int))
    psWOptions.panDstBands = <int *>CPLMalloc(src_count*sizeof(int))

    for i in range(src_count):
        psWOptions.panSrcBands[i] = src_bidx[i]
        psWOptions.panDstBands[i] = dst_bidx[i]

    log.debug("Set transformer options")

    # TODO: alpha band.

    # Now that the transformer and warp options are set up, we init
    # and run the warper.
    cdef GDALWarpOperation *oWarper = new GDALWarpOperation()
    try:
        with CPLErrors() as cple:
            oWarper.Initialize(psWOptions)
            cple.check()
        rows, cols = destination.shape[-2:]
        log.debug(
            "Chunk and warp window: %d, %d, %d, %d.",
            0, 0, cols, rows)

        with CPLErrors() as cple:
            if num_threads > 1:
                oWarper.ChunkAndWarpMulti(0, 0, cols, rows)
            else:
                oWarper.ChunkAndWarpImage(0, 0, cols, rows)
            cple.check()

        if dtypes.is_ndarray(destination):
            retval = io_auto(destination, outdataset, 0)
            # TODO: handle errors (by retval).

            if outdataset != NULL:
                GDALClose(outdataset)

    # Clean up transformer, warp options, and dataset handles.
    finally:
        GDALDestroyApproxTransformer(hTransformArg)
        GDALDestroyWarpOptions(psWOptions)
        if dtypes.is_ndarray(source):
            if indataset != NULL:
                GDALClose(indataset)


def _calculate_default_transform(
        src_crs, dst_crs, width, height, left, bottom, right, top, **kwargs):
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
    transform = from_bounds(left, bottom, right, top, width, height)
    img = np.empty((height, width))

    osr = osr_from_crs(dst_crs)
    OSRExportToWkt(osr, &wkt)
    OSRDestroySpatialReference(osr)

    with InMemoryRaster(
            img, transform=transform.to_gdal(), crs=src_crs) as temp:
        try:
            with CPLErrors() as cple:
                hTransformArg = GDALCreateGenImgProjTransformer(
                    temp._hds, NULL, NULL, wkt, 1, 1000.0,0)
                cple.check()
                result = GDALSuggestedWarpOutput2(
                    temp._hds, GDALGenImgProjTransform, hTransformArg,
                    geotransform, &npixels, &nlines, extent, 0)
                cple.check()
            log.debug("Created transformer and warp output.")
        except CPLE_NotSupportedError as err:
            raise CRSError(err.errmsg)
        except CPLE_AppDefinedError as err:
            if "Reprojection failed" in str(err):
                # This "exception" should be treated as a debug msg, not error
                # "Reprojection failed, err = -14, further errors will be
                # suppressed on the transform object."
                log.debug("Encountered points outside of valid dst crs region")
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
