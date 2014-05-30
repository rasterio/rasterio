# distutils: language = c++
# cython: profile=True
#

from collections import namedtuple
import logging

import numpy as np
cimport numpy as np

from rasterio cimport _gdal, _ogr
from rasterio cimport _io
from rasterio import dtypes


cdef extern from "gdalwarper.h":

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


RESAMPLING = namedtuple('RESAMPLING', [
                'nearest', 
                'bilinear', 
                'cubic', 
                'cubic_spline', 
                'lanczos', 
                'average', 
                'mode'] )(*list(range(7)))

log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


def tastes_like_gdal(t):
    return t[2] == t[4] == 0.0 and t[1] > 0 and t[5] < 0


def _reproject(
        source, destination,
        src_transform=None, src_crs=None, 
        dst_transform=None, dst_crs=None,
        resampling=RESAMPLING.nearest, 
        **kwargs):
    """Reproject a source raster to a destination.

    If the source and destination are ndarrays, coordinate reference
    system definitions and affine transformation parameters are required
    for reprojection.

    If the source and destination are rasterio Bands, shorthand for
    bands of datasets on disk, the coordinate reference systems and
    transforms will be read from the appropriate datasets.
    """
    cdef int retval, rows, cols
    cdef void *hrdriver
    cdef void *hdsin
    cdef void *hdsout
    cdef void *hbandin
    cdef void *hbandout
    cdef _io.RasterReader rdr
    cdef _io.RasterUpdater udr
    cdef _io.GDALAccess GA
    cdef double gt[6]
    cdef char *srcwkt = NULL
    cdef char *dstwkt= NULL
    cdef const char *proj_c
    cdef void *osr
    cdef char **warp_extras
    cdef char *key_c
    cdef char *val_c
    cdef const char* pszWarpThreads

    # If the source is an ndarray, we copy to a MEM dataset.
    # We need a src_transform and src_dst in this case. These will
    # be copied to the MEM dataset.
    if isinstance(source, np.ndarray):
        hrdriver = _gdal.GDALGetDriverByName("MEM")
        if hrdriver == NULL:
            raise ValueError("NULL driver for 'MEM'")
        rows = source.shape[0]
        cols = source.shape[1]
        dtype = source.dtype.type
        hdsin = _gdal.GDALCreate(
                    hrdriver, "input", cols, rows, 
                    1, dtypes.dtype_rev[dtype], NULL)
        if hdsin == NULL:
            raise ValueError("NULL input datasource")
        _gdal.GDALSetDescription(hdsin, "Temporary source dataset for _reproject()")
        log.debug("Created temp source dataset")
        for i in range(6):
            gt[i] = src_transform[i]
        retval = _gdal.GDALSetGeoTransform(hdsin, gt)
        log.debug("Set transform on temp source dataset: %d", retval)
        osr = _gdal.OSRNewSpatialReference(NULL)
        if osr == NULL:
            raise ValueError("Null spatial reference")
        params = []
        for k, v in src_crs.items():
            if v is True or (k == 'no_defs' and v):
                params.append("+%s" % k)
            else:
                params.append("+%s=%s" % (k, v))
        proj = " ".join(params)
        proj_b = proj.encode()
        proj_c = proj_b
        _gdal.OSRImportFromProj4(osr, proj_c)
        _gdal.OSRExportToWkt(osr, &srcwkt)
        _gdal.GDALSetProjection(hdsin, srcwkt)
        _gdal.CPLFree(srcwkt)
        _gdal.OSRDestroySpatialReference(osr)
        log.debug("Set CRS on temp source dataset: %s", srcwkt)
        
        # Copy ndarry to the MEM dataset's first band.
        hbandin = _gdal.GDALGetRasterBand(hdsin, 1)
        if hbandin == NULL:
            raise ValueError("NULL input band")
        log.debug("Got temp source band")
        if dtype == dtypes.ubyte:
            retval = _io.io_ubyte(
                hbandin, 1, 0, 0, cols, rows, source)
        elif dtype == dtypes.uint16:
            retval = _io.io_uint16(
                hbandin, 1, 0, 0, cols, rows, source)
        elif dtype == dtypes.int16:
            retval = _io.io_int16(
                hbandin, 1, 0, 0, cols, rows, source)
        elif dtype == dtypes.uint32:
            retval = _io.io_uint32(
                hbandin, 1, 0, 0, cols, rows, source)
        elif dtype == dtypes.int32:
            retval = _io.io_int32(
                hbandin, 1, 0, 0, cols, rows, source)
        elif dtype == dtypes.float32:
            retval = _io.io_float32(
                hbandin, 1, 0, 0, cols, rows, source)
        elif dtype == dtypes.float64:
            retval = _io.io_float64(
                hbandin, 1, 0, 0, cols, rows, source)
        else:
            raise ValueError("Invalid dtype")
        # TODO: handle errors (by retval).
        log.debug("Wrote array to temp source dataset")
    
    # If the source is a rasterio Band, no copy necessary.
    elif isinstance(source, tuple):
        rdr = source.ds
        hdsin = rdr._hds
    else:
        raise ValueError("Invalid source")
    
    # Next, do the same for the destination raster.
    if isinstance(destination, np.ndarray):
        hrdriver = _gdal.GDALGetDriverByName("MEM")
        if hrdriver == NULL:
            raise ValueError("NULL driver for 'MEM'")
        rows, cols = destination.shape
        hdsout = _gdal.GDALCreate(
                        hrdriver, "output", cols, rows, 1, 
                        dtypes.dtype_rev[destination.dtype.type], NULL)
        if hdsout == NULL:
            raise ValueError("NULL output datasource")
        _gdal.GDALSetDescription(hdsout, "Temporary destination dataset for _reproject()")
        log.debug("Created temp destination dataset")
        for i in range(6):
            gt[i] = dst_transform[i]
        retval = _gdal.GDALSetGeoTransform(hdsout, gt)
        log.debug("Set transform on temp destination dataset: %d", retval)
        osr = _gdal.OSRNewSpatialReference(NULL)
        if osr == NULL:
            raise ValueError("Null spatial reference")
        params = []
        for k, v in dst_crs.items():
            if v is True or (k == 'no_defs' and v):
                params.append("+%s" % k)
            else:
                params.append("+%s=%s" % (k, v))
        proj = " ".join(params)
        log.debug("Proj4 string: %s", proj)
        proj_b = proj.encode()
        proj_c = proj_b
        _gdal.OSRImportFromProj4(osr, proj_c)
        _gdal.OSRExportToWkt(osr, &dstwkt)
        retval = _gdal.GDALSetProjection(hdsout, dstwkt)
        log.debug("Setting Projection: %d", retval)
        _gdal.CPLFree(dstwkt)
        _gdal.OSRDestroySpatialReference(osr)
        log.debug("Set CRS on temp destination dataset: %s", dstwkt)

    elif isinstance(destination, tuple):
        udr = destination.ds
        hdsout = udr._hds
    else:
        raise ValueError("Invalid destination")
    
    cdef void *hTransformArg
    cdef _gdal.GDALWarpOptions *psWOptions
    cdef GDALWarpOperation *oWarper = new GDALWarpOperation()
    reprojected = False

    try:
        hTransformArg = _gdal.GDALCreateGenImgProjTransformer(
                                            hdsin, NULL, hdsout, NULL, 
                                            1, 1000.0, 0)
        if hTransformArg == NULL:
            raise ValueError("NULL transformer")
        log.debug("Created transformer")

        psWOptions = _gdal.GDALCreateWarpOptions()
        
        warp_extras = psWOptions.papszWarpOptions
        for k, v in kwargs.items():
            k, v = k.upper(), str(v).upper()
            key_b = k.encode('utf-8')
            val_b = v.encode('utf-8')
            key_c = key_b
            val_c = val_b
            warp_extras = _gdal.CSLSetNameValue(warp_extras, key_c, val_c)
        
        pszWarpThreads = _gdal.CSLFetchNameValue(warp_extras, "NUM_THREADS")
        if pszWarpThreads == NULL:
            pszWarpThreads = _gdal.CPLGetConfigOption(
                                "GDAL_NUM_THREADS", "1")
            warp_extras = _gdal.CSLSetNameValue(
                warp_extras, "NUM_THREADS", pszWarpThreads)

        log.debug("Created warp options")
    
        psWOptions.eResampleAlg = <_gdal.GDALResampleAlg>resampling
        # TODO: Approximate transformations.
        #if maxerror > 0.0:
        #    psWOptions.pTransformerArg = _gdal.GDALCreateApproxTransformer(
        #                                    _gdal.GDALGenImgProjTransform, 
        #                                    hTransformArg, 
        #                                    maxerror )
        #    psWOptions.pfnTransformer = _gdal.GDALApproxTransform
        #else:
        psWOptions.pfnTransformer = _gdal.GDALGenImgProjTransform
        psWOptions.pTransformerArg = hTransformArg
        psWOptions.hSrcDS = hdsin
        psWOptions.hDstDS = hdsout
        psWOptions.nBandCount = 1
        psWOptions.panSrcBands = <int *>_gdal.CPLMalloc(sizeof(int))
        psWOptions.panDstBands = <int *>_gdal.CPLMalloc(sizeof(int))
        if isinstance(source, tuple):
            psWOptions.panSrcBands[0] = source.bidx
        else:
            psWOptions.panSrcBands[0] = 1
        if isinstance(destination, tuple):
            psWOptions.panDstBands[0] = destination.bidx
        else:
            psWOptions.panDstBands[0] = 1
        log.debug("Set transformer options")

        # TODO: Src nodata and alpha band.

        eErr = oWarper.Initialize(psWOptions)
        if eErr == 0:
            rows, cols = destination.shape
            log.debug(
                "Chunk and warp window: %d, %d, %d, %d",
                0, 0, cols, rows)
            eErr = oWarper.ChunkAndWarpMulti(0, 0, cols, rows)
            log.debug("Chunked and warped: %d", retval)
    
    except Exception, e:
        log.exception(
            "Caught exception in warping. Source not reprojected.")
    
    else:
        reprojected = True

    finally:
        _gdal.GDALDestroyGenImgProjTransformer( hTransformArg );
        #if maxerror > 0.0:
        #    _gdal.GDALDestroyApproxTransformer(psWOptions.pTransformerArg)
        _gdal.GDALDestroyWarpOptions(psWOptions)
        if isinstance(source, np.ndarray):
            if hdsin != NULL:
                _gdal.GDALClose(hdsin)

    if reprojected and isinstance(destination, np.ndarray):
        try:
            dtype = destination.dtype
            rows, cols = destination.shape
            hbandout = _gdal.GDALGetRasterBand(hdsout, 1)
            if hbandout == NULL:
                raise ValueError("NULL output band")
            if dtype == dtypes.ubyte:
                retval = _io.io_ubyte(
                    hbandout, 0, 0, 0, cols, rows, destination)
                log.debug("Wrote data to destination: %d", retval)
            elif dtype == dtypes.uint16:
                retval = _io.io_uint16(
                    hbandout, 0, 0, 0, cols, rows, destination)
            elif dtype == dtypes.int16:
                retval = _io.io_int16(
                    hbandout, 0, 0, 0, cols, rows, destination)
            elif dtype == dtypes.uint32:
                retval = _io.io_uint32(
                    hbandout, 0, 0, 0, cols, rows, destination)
            elif dtype == dtypes.int32:
                retval = _io.io_int32(
                    hbandout, 0, 0, 0, cols, rows, destination)
            elif dtype == dtypes.float32:
                retval = _io.io_float32(
                    hbandout, 0, 0, 0, cols, rows, destination)
            elif dtype == dtypes.float64:
                retval = _io.io_float64(
                    hbandout, 0, 0, 0, cols, rows, destination)
            else:
                raise ValueError("Invalid dtype")
            # TODO: handle errors (by retval).
        except Exception, e:
            raise
        finally:
            if hdsout != NULL:
                _gdal.GDALClose(hdsout)

