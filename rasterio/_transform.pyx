# cython: language_level=3, boundscheck=False, c_string_type=unicode, c_string_encoding=utf8

"""Transforms."""

include "gdal.pxi"

import warnings

from rasterio._err import GDALError
from rasterio._err cimport exc_wrap_pointer
from rasterio.errors import NotGeoreferencedWarning, RPCTransformWarning

def _rpc_transform(rpcs, xs, ys, zs, transform_direction=1, **kwargs):
    """
    Coordinate transformations using RPCs.
    
    Parameters
    ----------
    rpcs : rasterio.control.RPC or dict
        Dictionary of rational polynomial coefficients.
    xs : list of float
        x values in longitude or col values in pixels.
    ys : list of float
        y values in latitude or row values in pixels.
    zs : list of float
        Height values in meters relative to WGS84 ellipsoid.
    transform_direction : int
        The direction to transform coordinates. A value of 1 indicates forward (col, row)
        -> (x, y, z) while a value of 0 indicates reverse (x, y, z) -> (col, row).
    kwargs : dict
        Options to be passed to GDALCreateRPCTransformer.
    
    Returns
    -------
    new_xs : list of floats
        list of col indices
    new_ys : list of floats
        list of row indices
    """
    cdef int i
    cdef char **papszMD = NULL
    cdef char **options = NULL
    cdef GDALRPCInfo rpcinfo
    cdef int src_count
    cdef double *x = NULL
    cdef double *y = NULL
    cdef double *z = NULL
    cdef void *pTransformArg = NULL
    cdef int bReversed = 0
    cdef int bDstToSrc = transform_direction
    cdef double dfPixErrThreshold = 0.1  # GDAL default
    cdef int *panSuccess = NULL

    n = len(xs)
    x = <double *>CPLMalloc(n * sizeof(double))
    y = <double *>CPLMalloc(n * sizeof(double))
    z = <double *>CPLMalloc(n * sizeof(double))

    for i in range(n):
        x[i] = xs[i]
        y[i] = ys[i]
        z[i] = zs[i]

    panSuccess = <int *>CPLMalloc(n * sizeof(int))
    
    if hasattr(rpcs, 'to_gdal'):
        rpcs = rpcs.to_gdal()
    for key, val in rpcs.items():
        key = key.upper().encode('utf-8')
        val = str(val).encode('utf-8')
        papszMD = CSLSetNameValue(
            papszMD, <const char *>key, <const char *>val)

    for key, val in kwargs.items():
        key = key.upper().encode('utf-8')
        val = str(val).encode('utf-8')
        options = CSLSetNameValue(
            options, <const char *>key, <const char *>val)
    try:
        GDALExtractRPCInfo(papszMD, &rpcinfo)
        pTransformArg = exc_wrap_pointer(GDALCreateRPCTransformer(&rpcinfo, bReversed, dfPixErrThreshold, options))
        err = GDALRPCTransform(pTransformArg, bDstToSrc, n, x, y, z, panSuccess)
        if err == GDALError.failure:
            warnings.warn(
            "Could not transform points using RPCs.",
            RPCTransformWarning)
        res_xs = [0] * n
        res_ys = [0] * n
        res_zs = [0] * n
        checked = False
        for i in range(n):
            # GDALRPCTransformer may return a success overall despite individual points failing. Warn once.
            if not panSuccess[i] and not checked:
                warnings.warn(
                "One or more points could not be transformed using RPCs.",
                RPCTransformWarning)
                checked = True
            res_xs[i] = x[i]
            res_ys[i] = y[i]
            res_zs[i] = z[i]
    finally:
        CPLFree(x)
        CPLFree(y)
        CPLFree(z)
        CPLFree(panSuccess)
        GDALDestroyRPCTransformer(pTransformArg)
        CSLDestroy(options)
        CSLDestroy(papszMD)

    return (res_xs, res_ys)

def _transform_from_gcps(gcps):
    cdef double gt[6]

    cdef GDAL_GCP *gcplist = <GDAL_GCP *>CPLMalloc(len(gcps) * sizeof(GDAL_GCP))
    
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

        err = GDALGCPsToGeoTransform(len(gcps), gcplist, gt, 0)
        if err == GDALError.failure:
                warnings.warn(
                "Could not get geotransform set from gcps. The identity matrix may be returned.",
                NotGeoreferencedWarning)

    finally:
            CPLFree(gcplist)

    return [gt[i] for i in range(6)]

cdef class _RPCTransformer:
    cdef void *_transformer
    cdef bint _bUseApproxTransformer

    def __cinit__(self):
        self._transformer = NULL
        self._bUseApproxTransformer = False

    def __dealloc__(self):
        if self._transformer != NULL:
            if self._bUseApproxTransformer:
                GDALDestroyApproxTransformer(self._transformer)
            else:
                GDALDestroyRPCTransformer(self._transformer)
    
    def __init__(self, rpcs, **kwargs):
        cdef char **papszMD = NULL
        cdef char **options = NULL
        cdef int bReversed = 0
        cdef double dfPixErrThreshold = 0.1  # GDAL default
        cdef GDALRPCInfo rpcinfo
        
        if hasattr(rpcs, 'to_gdal'):
            rpcs = rpcs.to_gdal()
        for key, val in rpcs.items():
            key = key.upper().encode('utf-8')
            val = str(val).encode('utf-8')
            papszMD = CSLSetNameValue(
                papszMD, <const char *>key, <const char *>val)

        for key, val in kwargs.items():
            key = key.upper().encode('utf-8')
            val = str(val).encode('utf-8')
            options = CSLSetNameValue(
                options, <const char *>key, <const char *>val)

        try:
            GDALExtractRPCInfo(papszMD, &rpcinfo)
            self._transformer = exc_wrap_pointer(GDALCreateRPCTransformer(&rpcinfo, bReversed, dfPixErrThreshold, options))
        finally:
            CSLDestroy(options)
            CSLDestroy(papszMD)
    
    def _transform(self, xs, ys, zs, transform_direction):
        cdef int i
        cdef double *x = NULL
        cdef double *y = NULL
        cdef double *z = NULL
        cdef int bDstToSrc = transform_direction
        cdef int src_count
        cdef int *panSuccess = NULL

        n = len(xs)
        x = <double *>CPLMalloc(n * sizeof(double))
        y = <double *>CPLMalloc(n * sizeof(double))
        z = <double *>CPLMalloc(n * sizeof(double))
        panSuccess = <int *>CPLMalloc(n * sizeof(int))
        
        for i in range(n):
            x[i] = xs[i]
            y[i] = ys[i]
            z[i] = zs[i]
        
        try:
            err = GDALRPCTransform(self._transformer, bDstToSrc, n, x, y, z, panSuccess)
            if err == GDALError.failure:
                warnings.warn(
                "Could not transform points using RPCs.",
                RPCTransformWarning)
            res_xs = [0] * n
            res_ys = [0] * n
            res_zs = [0] * n
            checked = False
            for i in range(n):
                # GDALRPCTransformer may return a success overall despite individual points failing. Warn once.
                if not panSuccess[i] and not checked:
                    warnings.warn(
                    "One or more points could not be transformed using RPCs.",
                    RPCTransformWarning)
                    checked = True
                res_xs[i] = x[i]
                res_ys[i] = y[i]
                res_zs[i] = z[i]
        finally:
            CPLFree(x)
            CPLFree(y)
            CPLFree(z)
            CPLFree(panSuccess)

        return (res_xs, res_ys)