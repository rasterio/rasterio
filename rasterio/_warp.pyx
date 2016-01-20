# distutils: language = c++

from enum import IntEnum

import logging

import numpy as np
cimport numpy as np

from rasterio cimport _base, _gdal, _ogr, _io, _features
from rasterio import dtypes
from rasterio.errors import RasterioDriverRegistrationError
from rasterio._err import cpl_errs


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


class Resampling(IntEnum):
    nearest=0
    bilinear=1
    cubic=2
    cubic_spline=3
    lanczos=4
    average=5
    mode=6
    max=8
    min=9
    med=10
    q1=11
    q3=12


cdef extern from "ogr_geometry.h" nogil:

    cdef cppclass OGRGeometry:
        pass

    cdef cppclass OGRGeometryFactory:
        void * transformWithOptions(void *geom, void *ct, char **options)


cdef extern from "ogr_spatialref.h":

    cdef cppclass OGRCoordinateTransformation:
        pass


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


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
    transform = _gdal.OCTNewCoordinateTransformation(src, dst)

    # Transform options.
    val_b = str(antimeridian_offset).encode('utf-8')
    val_c = val_b
    options = _gdal.CSLSetNameValue(
                options, "DATELINEOFFSET", val_c)
    if antimeridian_cutting:
        options = _gdal.CSLSetNameValue(options, "WRAPDATELINE", "YES")

    factory = new OGRGeometryFactory()
    src_ogr_geom = _features.OGRGeomBuilder().build(geom)
    dst_ogr_geom = factory.transformWithOptions(
                    <const OGRGeometry *>src_ogr_geom,
                    <OGRCoordinateTransformation *>transform,
                    options)
    g = _features.GeomBuilder().build(dst_ogr_geom)

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
    kwargs:  dict, optional
        Additional arguments passed to transformation function.

    Returns
    ---------
    out: None
        Output is written to destination.
    """

    cdef int retval=0, rows, cols, src_count
    cdef void *hrdriver = NULL
    cdef void *hdsin = NULL
    cdef void *hdsout = NULL
    cdef void *hbandin = NULL
    cdef void *hbandout = NULL
    cdef _io.RasterReader rdr
    cdef _io.RasterUpdater udr
    cdef _io.GDALAccess GA
    cdef double gt[6]
    cdef char *srcwkt = NULL
    cdef char *dstwkt= NULL
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
        # Convert 2D single-band arrays to 3D multi-band.
        if len(source.shape) == 2:
            source = source.reshape(1, *source.shape)
        src_count = source.shape[0]
        rows = source.shape[1]
        cols = source.shape[2]
        dtype = np.dtype(source.dtype).name
        if src_nodata is None and hasattr(source, 'fill_value'):
            # source is a masked array
            src_nodata = source.fill_value

        hrdriver = _gdal.GDALGetDriverByName("MEM")
        if hrdriver == NULL:
            raise RasterioDriverRegistrationError(
                "'MEM' driver not found. Check that this call is contained "
                "in a `with rasterio.drivers()` or `with rasterio.open()` "
                "block.")

        hdsin = _gdal.GDALCreate(
                    hrdriver, "input", cols, rows, 
                    src_count, dtypes.dtype_rev[dtype], NULL)
        if hdsin == NULL:
            raise ValueError("NULL input datasource")
        _gdal.GDALSetDescription(
            hdsin, "Temporary source dataset for _reproject()")
        log.debug("Created temp source dataset")
        for i in range(6):
            gt[i] = src_transform[i]
        retval = _gdal.GDALSetGeoTransform(hdsin, gt)
        log.debug("Set transform on temp source dataset: %d", retval)
        osr = _base._osr_from_crs(src_crs)
        _gdal.OSRExportToWkt(osr, &srcwkt)
        _gdal.GDALSetProjection(hdsin, srcwkt)
        _gdal.CPLFree(srcwkt)
        _gdal.OSRDestroySpatialReference(osr)
        log.debug("Set CRS on temp source dataset: %s", srcwkt)
        
        # Copy arrays to the dataset.
        retval = _io.io_auto(source, hdsin, 1)
        # TODO: handle errors (by retval).
        log.debug("Wrote array to temp source dataset")
    
    # If the source is a rasterio Band, no copy necessary.
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
        if destination.shape[0] != src_count:
            raise ValueError("Destination's shape is invalid")

        hrdriver = _gdal.GDALGetDriverByName("MEM")
        if hrdriver == NULL:
            raise RasterioDriverRegistrationError(
                "'MEM' driver not found. Check that this call is contained "
                "in a `with rasterio.drivers()` or `with rasterio.open()` "
                "block.")

        _, rows, cols = destination.shape
        hdsout = _gdal.GDALCreate(
                        hrdriver, "output", cols, rows, src_count, 
                        dtypes.dtype_rev[np.dtype(destination.dtype).name], NULL)
        if hdsout == NULL:
            raise ValueError("NULL output datasource")
        _gdal.GDALSetDescription(
            hdsout, "Temporary destination dataset for _reproject()")
        log.debug("Created temp destination dataset")
        for i in range(6):
            gt[i] = dst_transform[i]
        retval = _gdal.GDALSetGeoTransform(hdsout, gt)
        log.debug("Set transform on temp destination dataset: %d", retval)
        osr = _base._osr_from_crs(dst_crs)
        _gdal.OSRExportToWkt(osr, &dstwkt)
        retval = _gdal.GDALSetProjection(hdsout, dstwkt)
        log.debug("Setting Projection: %d", retval)
        _gdal.CPLFree(dstwkt)
        _gdal.OSRDestroySpatialReference(osr)
        log.debug("Set CRS on temp destination dataset: %s", dstwkt)
        if dst_nodata is None and hasattr(destination, "fill_value"):
            # destination is a masked array
            dst_nodata = destination.fill_value

    elif isinstance(destination, tuple):
        udr = destination.ds
        hdsout = udr._hds
        if dst_nodata is None:
            dst_nodata = udr.nodata
    else:
        raise ValueError("Invalid destination")
    
    cdef void *hTransformArg = NULL
    cdef _gdal.GDALWarpOptions *psWOptions = NULL
    cdef GDALWarpOperation *oWarper = new GDALWarpOperation()
    cdef int num_threads = int(kwargs.get('num_threads', 1))
    reprojected = False

    hTransformArg = _gdal.GDALCreateGenImgProjTransformer(
                                        hdsin, NULL, hdsout, NULL, 
                                        1, 1000.0, 0)
    if hTransformArg == NULL:
        raise ValueError("NULL transformer")
    log.debug("Created transformer")

    psWOptions = _gdal.GDALCreateWarpOptions()

    # Note: warp_extras is pointed to different memory locations on every
    # call to CSLSetNameValue call below, but needs to be set here to
    # get the defaults
    warp_extras = psWOptions.papszWarpOptions

    for k, v in kwargs.items():
        k, v = k.upper(), str(v).upper()
        key_b = k.encode('utf-8')
        val_b = v.encode('utf-8')
        key_c = key_b
        val_c = val_b
        warp_extras = _gdal.CSLSetNameValue(warp_extras, key_c, val_c)
        log.debug("Setting warp option  %s: %s" % (k, v))
    
    num_threads = kwargs.get('num_threads', 1)

    #pszWarpThreads = _gdal.CSLFetchNameValue(warp_extras, "NUM_THREADS")
    #if pszWarpThreads == NULL:
    #    pszWarpThreads = _gdal.CPLGetConfigOption(
    #                        "GDAL_NUM_THREADS", "1")
    #    warp_extras = _gdal.CSLSetNameValue(
    #        warp_extras, "NUM_THREADS", pszWarpThreads)

    log.debug("Created warp options")

    psWOptions.eResampleAlg = <_gdal.GDALResampleAlg>resampling

    # Set src_nodata and dst_nodata
    if src_nodata is None and dst_nodata is not None:
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
        raise ValueError("dst_nodata must be in valid range for "
                         "destination dtype")

    psWOptions.padfDstNoDataReal = <double*>_gdal.CPLMalloc(src_count * sizeof(double))
    psWOptions.padfDstNoDataImag = <double*>_gdal.CPLMalloc(src_count * sizeof(double))
    for i in range(src_count):
        psWOptions.padfDstNoDataReal[i] = dst_nodata
        psWOptions.padfDstNoDataImag[i] = 0.0
    warp_extras = _gdal.CSLSetNameValue(
        warp_extras, "INIT_DEST", "NO_DATA")

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

    if oWarper.Initialize(psWOptions):
        raise RuntimeError("Failed to initialize warper.")

    else:
        rows, cols = destination.shape[-2:]
        log.debug(
            "Chunk and warp window: %d, %d, %d, %d.",
            0, 0, cols, rows)

        if num_threads > 1:
            err_code = oWarper.ChunkAndWarpMulti(0, 0, cols, rows)
        else:
            err_code = oWarper.ChunkAndWarpImage(0, 0, cols, rows)

        log.debug("Chunked and warped: %d", err_code)

        reprojected = not(err_code)

    if hTransformArg != NULL:
        _gdal.GDALDestroyGenImgProjTransformer(hTransformArg)
    if psWOptions != NULL:
        _gdal.GDALDestroyWarpOptions(psWOptions)
    if dtypes.is_ndarray(source):
        if hdsin != NULL:
            _gdal.GDALClose(hdsin)

    if reprojected and dtypes.is_ndarray(destination):
        retval = _io.io_auto(destination, hdsout, 0)
        # TODO: handle errors (by retval).

        if hdsout != NULL:
            _gdal.GDALClose(hdsout)
