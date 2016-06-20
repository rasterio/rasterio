# distutils: language = c++
"""Raster and vector warping and reprojection."""

from enum import IntEnum
import logging

import numpy as np
cimport numpy as np

from rasterio cimport _base, _gdal, _ogr, _io, _features
from rasterio import dtypes
from rasterio._err import CPLErrors, GDALError, CPLE_NotSupported, CPLE_AppDefined
from rasterio._io cimport InMemoryRaster
from rasterio.enums import Resampling
from rasterio.errors import DriverRegistrationError, CRSError
from rasterio.transform import Affine, from_bounds


cdef extern from "gdalwarper.h" nogil:

    ctypedef struct GDALWarpOptions

    cdef cppclass GDALWarpOperation:
        GDALWarpOperation() except +
        int Initialize(const GDALWarpOptions *psNewOptions)
        const GDALWarpOptions *GetOptions()
        int ChunkAndWarpImage(
            int nDstXOff, int nDstYOff, int nDstXSize, int nDstYSize )
        int ChunkAndWarpMulti(
            int nDstXOff, int nDstYOff, int nDstXSize, int nDstYSize )
        int WarpRegion( int nDstXOff, int nDstYOff,
                        int nDstXSize, int nDstYSize,
                        int nSrcXOff=0, int nSrcYOff=0,
                        int nSrcXSize=0, int nSrcYSize=0,
                        double dfProgressBase=0.0, double dfProgressScale=1.0)
        int WarpRegionToBuffer( int nDstXOff, int nDstYOff,
                                int nDstXSize, int nDstYSize,
                                void *pDataBuf,
                                int eBufDataType,
                                int nSrcXOff=0, int nSrcYOff=0,
                                int nSrcXSize=0, int nSrcYSize=0,
                                double dfProgressBase=0.0,
                                double dfProgressScale=1.0)




cdef extern from "ogr_geometry.h" nogil:

    cdef cppclass OGRGeometry:
        pass

    cdef cppclass OGRGeometryFactory:
        void * transformWithOptions(void *geom, void *ct, char **options)


cdef extern from "ogr_spatialref.h":

    cdef cppclass OGRCoordinateTransformation:
        pass


log = logging.getLogger(__name__)


def tastes_like_gdal(t):
    return t[2] == t[4] == 0.0 and t[1] > 0 and t[5] < 0


def _transform_geom(
        src_crs, dst_crs, geom, antimeridian_cutting, antimeridian_offset,
        precision):
    """Return a transformed geometry."""
    cdef char *proj_c = NULL
    cdef char *key_c = NULL
    cdef char *val_c = NULL
    cdef char **options = NULL
    cdef void *src = NULL
    cdef void *dst = NULL
    cdef void *transform = NULL
    cdef OGRGeometryFactory *factory = NULL
    cdef void *src_ogr_geom = NULL
    cdef void *dst_ogr_geom = NULL
    cdef int i

    src = _base._osr_from_crs(src_crs)
    dst = _base._osr_from_crs(dst_crs)

    try:
        with CPLErrors() as cple:
            transform = _gdal.OCTNewCoordinateTransformation(src, dst)
    except:
        _gdal.OSRDestroySpatialReference(src)
        _gdal.OSRDestroySpatialReference(dst)
        raise

    # Transform options.
    val_b = str(antimeridian_offset).encode('utf-8')
    val_c = val_b
    options = _gdal.CSLSetNameValue(
                options, "DATELINEOFFSET", val_c)
    if antimeridian_cutting:
        options = _gdal.CSLSetNameValue(options, "WRAPDATELINE", "YES")

    try:
        factory = new OGRGeometryFactory()
        src_ogr_geom = _features.OGRGeomBuilder().build(geom)
        with CPLErrors() as cple:
            dst_ogr_geom = factory.transformWithOptions(
                    <const OGRGeometry *>src_ogr_geom,
                    <OGRCoordinateTransformation *>transform,
                    options)
            cple.check()
        g = _features.GeomBuilder().build(dst_ogr_geom)
    finally:
        del factory
        _ogr.OGR_G_DestroyGeometry(dst_ogr_geom)
        _ogr.OGR_G_DestroyGeometry(src_ogr_geom)
        _gdal.OCTDestroyCoordinateTransformation(transform)
        if options != NULL:
            _gdal.CSLDestroy(options)
        _gdal.OSRDestroySpatialReference(src)
        _gdal.OSRDestroySpatialReference(dst)

    if precision >= 0:
        if g['type'] == 'Point':
            x, y = g['coordinates']
            x = round(x, precision)
            y = round(y, precision)
            new_coords = [x, y]
        elif g['type'] in ['LineString', 'MultiPoint']:
            xp, yp = zip(*g['coordinates'])
            xp = [round(v, precision) for v in xp]
            yp = [round(v, precision) for v in yp]
            new_coords = list(zip(xp, yp))
        elif g['type'] in ['Polygon', 'MultiLineString']:
            new_coords = []
            for piece in g['coordinates']:
                xp, yp = zip(*piece)
                xp = [round(v, precision) for v in xp]
                yp = [round(v, precision) for v in yp]
                new_coords.append(list(zip(xp, yp)))
        elif g['type'] == 'MultiPolygon':
            parts = g['coordinates']
            new_coords = []
            for part in parts:
                inner_coords = []
                for ring in part:
                    xp, yp = zip(*ring)
                    xp = [round(v, precision) for v in xp]
                    yp = [round(v, precision) for v in yp]
                    inner_coords.append(list(zip(xp, yp)))
                new_coords.append(inner_coords)
        g['coordinates'] = new_coords

    return g


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

    cdef int retval=0, rows, cols, src_count
    cdef void *hdsin = NULL
    cdef void *hdsout = NULL
    cdef void *hbandin = NULL
    cdef void *hbandout = NULL
    cdef _io.RasterReader rdr
    cdef _io.RasterUpdater udr
    cdef _io.GDALAccess GA
    cdef const char *proj_c = NULL
    cdef void *osr = NULL
    cdef char **warp_extras = NULL
    cdef char *key_c = NULL
    cdef char *val_c = NULL
    cdef const char* pszWarpThread = NULL

    # If the source is an ndarray, we copy to a MEM dataset.
    # We need a src_transform and src_dst in this case. These will
    # be copied to the MEM dataset.
    if dtypes.is_ndarray(source):
        if len(source.shape) == 2:
            source = source.reshape(1, *source.shape)
        src_count = source.shape[0]
        hdsin = _create_MEM_dataset(source, src_transform, src_crs, 'source')
        if src_nodata is None and hasattr(source, 'fill_value'):
            # source is a masked array
            src_nodata = source.fill_value
    elif isinstance(source, tuple):
        rdr = source.ds
        hdsin = rdr._hds
        src_count = 1
        if src_nodata is None:
            src_nodata = rdr.nodata
    else:
        raise ValueError("Invalid source")

    # Next, do the same for the destination raster.
    if dtypes.is_ndarray(destination):
        if len(destination.shape) == 2:
            destination = destination.reshape(1, *destination.shape)
        hdsout = _create_MEM_dataset(destination, dst_transform, dst_crs, 'destination', src_count=src_count)
    elif isinstance(destination, tuple):
        udr = destination.ds
        hdsout = udr._hds
        if dst_nodata is None:
            dst_nodata = udr.nodata
    else:
        raise ValueError("Invalid destination")

    cdef void *hTransformArg = NULL
    cdef _gdal.GDALWarpOptions *psWOptions = NULL

    try:
        with CPLErrors() as cple:
            hTransformArg = _gdal.GDALCreateGenImgProjTransformer(
                                hdsin, NULL, hdsout, NULL,
                                1, 1000.0, 0)
            cple.check()
            psWOptions = _gdal.GDALCreateWarpOptions()
            cple.check()
        log.debug("Created transformer and options.")
    except:
        _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)
        _gdal.GDALDestroyWarpOptions(psWOptions)
        raise

    # Note: warp_extras is pointed to different memory locations on every
    # call to CSLSetNameValue call below, but needs to be set here to
    # get the defaults.
    warp_extras = psWOptions.papszWarpOptions

    val_b = str(num_threads).encode('utf-8')
    warp_extras = _gdal.CSLSetNameValue(warp_extras, "NUM_THREADS", val_b)
    log.debug("Setting NUM_THREADS option: %s", val_b)

    for k, v in kwargs.items():
        k, v = k.upper(), str(v).upper()
        key_b = k.encode('utf-8')
        val_b = v.encode('utf-8')
        key_c = key_b
        val_c = val_b
        warp_extras = _gdal.CSLSetNameValue(warp_extras, key_c, val_c)
        log.debug("Setting warp option  %s: %s" % (k, v))

    log.debug("Created warp options")

    psWOptions.eResampleAlg = <_gdal.GDALResampleAlg>resampling

    # Set src_nodata and dst_nodata
    if src_nodata is None and dst_nodata is not None:
        psWOptions.papszWarpOptions = warp_extras
        _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)
        _gdal.GDALDestroyWarpOptions(psWOptions)
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
        if not _io.in_dtype_range(src_nodata, source.dtype):
            psWOptions.papszWarpOptions = warp_extras
            _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)
            _gdal.GDALDestroyWarpOptions(psWOptions)
            raise ValueError("src_nodata must be in valid range for "
                            "source dtype")

        psWOptions.padfSrcNoDataReal = <double*>_gdal.CPLMalloc(
            src_count * sizeof(double))
        psWOptions.padfSrcNoDataImag = <double*>_gdal.CPLMalloc(
            src_count * sizeof(double))
        for i in range(src_count):
            psWOptions.padfSrcNoDataReal[i] = src_nodata
            psWOptions.padfSrcNoDataImag[i] = 0.0
        warp_extras = _gdal.CSLSetNameValue(
            warp_extras, "UNIFIED_SRC_NODATA", "YES")


    if dst_nodata is not None and not _io.in_dtype_range(
            dst_nodata, destination.dtype):
        psWOptions.papszWarpOptions = warp_extras
        _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)
        _gdal.GDALDestroyWarpOptions(psWOptions)
        raise ValueError("dst_nodata must be in valid range for "
                         "destination dtype")

    psWOptions.padfDstNoDataReal = <double*>_gdal.CPLMalloc(src_count * sizeof(double))
    psWOptions.padfDstNoDataImag = <double*>_gdal.CPLMalloc(src_count * sizeof(double))
    for i in range(src_count):
        psWOptions.padfDstNoDataReal[i] = dst_nodata
        psWOptions.padfDstNoDataImag[i] = 0.0
    warp_extras = _gdal.CSLSetNameValue(warp_extras, "INIT_DEST", "NO_DATA")

    # Important: set back into struct or values set above are lost
    # This is because CSLSetNameValue returns a new list each time
    psWOptions.papszWarpOptions = warp_extras

    psWOptions.pfnTransformer = _gdal.GDALGenImgProjTransform
    psWOptions.pTransformerArg = hTransformArg
    psWOptions.hSrcDS = hdsin
    psWOptions.hDstDS = hdsout
    psWOptions.nBandCount = src_count
    psWOptions.panSrcBands = <int *>_gdal.CPLMalloc(src_count*sizeof(int))
    psWOptions.panDstBands = <int *>_gdal.CPLMalloc(src_count*sizeof(int))
    if isinstance(source, tuple):
        psWOptions.panSrcBands[0] = source.bidx
    else:
        for i in range(src_count):
            psWOptions.panSrcBands[i] = i+1
    if isinstance(destination, tuple):
        psWOptions.panDstBands[0] = destination.bidx
    else:
        for i in range(src_count):
            psWOptions.panDstBands[i] = i+1
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
                log.debug("Executing multi warp with num_threads: %d", num_threads)
                oWarper.ChunkAndWarpMulti(0, 0, cols, rows)
            else:
                oWarper.ChunkAndWarpImage(0, 0, cols, rows)
            cple.check()

        if dtypes.is_ndarray(destination):
            retval = _io.io_auto(destination, hdsout, 0)
            # TODO: handle errors (by retval).

            if hdsout != NULL:
                _gdal.GDALClose(hdsout)

    # Clean up transformer, warp options, and dataset handles.
    finally:
        _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)
        _gdal.GDALDestroyWarpOptions(psWOptions)
        if dtypes.is_ndarray(source):
            if hdsin != NULL:
                _gdal.GDALClose(hdsin)


def _calculate_default_transform(
        src_crs, dst_crs, width, height, left, bottom, right, top, **kwargs):
    """Wraps GDAL's algorithm."""

    cdef void *hTransformArg = NULL
    cdef int npixels = 0
    cdef int nlines = 0
    cdef double extent[4]
    cdef double geotransform[6]
    cdef void *osr = NULL
    cdef char *wkt = NULL
    cdef InMemoryRaster temp = None

    extent[:] = [0.0, 0.0, 0.0, 0.0]
    geotransform[:] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    # Make an in-memory raster dataset we can pass to
    # GDALCreateGenImgProjTransformer().
    transform = from_bounds(left, bottom, right, top, width, height)
    img = np.empty((height, width))

    osr = _base._osr_from_crs(dst_crs)
    _gdal.OSRExportToWkt(osr, &wkt)
    _gdal.OSRDestroySpatialReference(osr)

    with InMemoryRaster(
            img, transform=transform.to_gdal(), crs=src_crs) as temp:
        try:
            with CPLErrors() as cple:
                hTransformArg = _gdal.GDALCreateGenImgProjTransformer(
                                    temp.dataset, NULL, NULL, wkt,
                                    1, 1000.0,0)
                cple.check()
                result = _gdal.GDALSuggestedWarpOutput2(
                    temp.dataset, _gdal.GDALGenImgProjTransform, hTransformArg,
                    geotransform, &npixels, &nlines, extent, 0)
                cple.check()
            log.debug("Created transformer and warp output.")
        except CPLE_NotSupported as err:
            raise CRSError(err.errmsg)
        except CPLE_AppDefined as err:
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
                _gdal.CPLFree(wkt)
            if hTransformArg != NULL:
                _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)

    # Convert those modified arguments to Python values.
    dst_affine = Affine.from_gdal(*[geotransform[i] for i in range(6)])
    dst_width = npixels
    dst_height = nlines

    return dst_affine, dst_width, dst_height

cdef void *_create_MEM_dataset(data, transform, crs, desc, src_count=None) except *:
    """
    If the data is an ndarray, we copy to a MEM dataset.
    We need a transform and dst in this case. These will
    be copied to the MEM dataset.
    """
    cdef int retval=0, rows, cols
    cdef void *hrdriver = NULL
    cdef void *hds = NULL
    cdef char *wkt = NULL
    cdef double gt[6]

    desc_dict = {"source": "input",
                 "destination": "output"}
    assert desc in desc_dict.keys(), "Must use 'source' or 'destination' as description"
    if desc == 'source':
        assert src_count is None, "src_count for 'source' must be None"

    # Find MEM driver
    try:
        with CPLErrors() as cple:
            hrdriver = _gdal.GDALGetDriverByName("MEM")
            cple.check()
    except:
        raise DriverRegistrationError(
            "'MEM' driver not found. Check that this call is contained "
            "in a `with rasterio.Env()` or `with rasterio.open()` "
            "block.")

    # Convert 2D single-band arrays to 3D multi-band.


    if src_count is None:
        src_count = data.shape[0]
    elif data.shape[0] != src_count:
        raise ValueError("Destination's shape is invalid: {} vs {}".format(data.shape[0], src_count))
    else:
        pass

    _, rows, cols = data.shape

    dtype = np.dtype(data.dtype).name
    try:
        with CPLErrors() as cple:
            hds = _gdal.GDALCreate(hrdriver, desc_dict[desc], cols, rows, src_count, dtypes.dtype_rev[dtype], NULL)
            cple.check()
    except:
        raise
    _gdal.GDALSetDescription(hds, "Temporary {} dataset for _reproject()".format(desc))
    log.debug("Created temp {} dataset".format(desc))

    for i in range(6):
        gt[i] = transform[i]

    if desc == 'source':
        retval = _gdal.GDALSetGeoTransform(hds, gt)
        log.debug("Set transform on temp source dataset: %d", retval)
    else:
        if not GDALError.none == _gdal.GDALSetGeoTransform(hds, gt):
            raise ValueError("Failed to set transform on temp destination dataset.")

    try:
        osr = _base._osr_from_crs(crs)
        _gdal.OSRExportToWkt(osr, &wkt)
        if desc == 'source':
            _gdal.GDALSetProjection(hds, wkt)
            log.debug("Set CRS on temp source dataset: %s", wkt)
        else:
            log.debug("CRS on temp destination dataset: %s", wkt)
            if not GDALError.none == _gdal.GDALSetProjection(hds, wkt):
                raise ("Failed to set projection on temp destination dataset.")
    finally:
        _gdal.CPLFree(wkt)
        _gdal.OSRDestroySpatialReference(osr)
    # Copy arrays to the dataset.
    retval = _io.io_auto(data, hds, 1)
    # TODO: handle errors (by retval).
    log.debug("Wrote array to temp {} dataset".format(desc))
    return hds
