# cython: boundscheck=False, c_string_type=unicode, c_string_encoding=utf8
"""Transforms."""

include "gdal.pxi"

import warnings

from rasterio._err import GDALError
from rasterio._err cimport exc_wrap_pointer
from rasterio.errors import NotGeoreferencedWarning

def _rpc_transformer(rpcs, xs, ys, zs=None, transform_direction=1, **kwargs):
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
    cdef double dfPixErrThreshold = 0.0
    cdef int *success_ptr = NULL

    n = len(xs)
    x = <double *>CPLMalloc(n * sizeof(double))
    y = <double *>CPLMalloc(n * sizeof(double))
    z = <double *>CPLMalloc(n * sizeof(double))

    if not zs:
        zs = [0.] * n
    for i in range(n):
        x[i] = xs[i]
        y[i] = ys[i]
        z[i] = zs[i]

    success_ptr = <int *>CPLMalloc(n * sizeof(int))

    for key, val in rpcs.items():
        key = key.upper().encode('utf-8')
        val = str(val).upper().encode('utf-8')
        papszMD = CSLSetNameValue(
            papszMD, <const char *>key, <const char *>val)

    for key, val in kwargs.items():
        key = key.upper().encode('utf-8')
        val = str(val).upper().encode('utf-8')
        options = CSLSetNameValue(
            options, <const char *>key, <const char *>val)
    try:
        GDALExtractRPCInfo(papszMD, &rpcinfo)
        pTransformArg = exc_wrap_pointer(GDALCreateRPCTransformer(&rpcinfo, bReversed, dfPixErrThreshold, options))
        err = GDALRPCTransform(pTransformArg, bDstToSrc, n, x, y, z, success_ptr)
        if err == GDALError.failure:
            warnings.warn(
            "Could not transform points using RPCs",
            NotGeoreferencedWarning)
        res_xs = [0] * n
        res_ys = [0] * n
        res_zs = [0] * n
        for i in range(n):
            res_xs[i] = x[i]
            res_ys[i] = y[i]
            res_zs[i] = z[i]
    finally:
        CPLFree(x)
        CPLFree(y)
        CPLFree(z)
        CPLFree(success_ptr)
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

