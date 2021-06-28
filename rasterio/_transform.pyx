# cython: language_level=3, boundscheck=False, c_string_type=unicode, c_string_encoding=utf8

"""Transforms."""

include "gdal.pxi"

import logging
import warnings

from rasterio._err import GDALError
from rasterio._err cimport exc_wrap_pointer
from rasterio.errors import NotGeoreferencedWarning, TransformWarning

log = logging.getLogger(__name__)


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


cdef class RPCTransformerBase:
    """
    Rational Polynomial Coefficients (RPC) transformer base class
    """
    cdef void *_transformer
    cdef bint _closed

    def __cinit__(self):
        self._transformer = NULL
        self._closed = True

    def __dealloc__(self):
        self.close()

    def __init__(self, rpcs, **kwargs):
        """
        Construct a new RPC transformer

        The RPCs map geographic coordinates referenced against the WGS84 ellipsoid (longitude, latitude, height)
        to image pixel/line coordinates. The reverse is done through an iterative solver implemented
        in GDAL.

        Parameters
        ----------
        rpcs : rasterio.rpc.RPC or dict
            RPCs for a dataset. If passing a dict, should be in the form expected
            by rasterio.rpc.RPC.from_gdal.
        kwargs : dict
            GDALCreateRPCTransformer options. See
            https://gdal.org/api/gdal_alg.html#_CPPv426GDALCreateRPCTransformerV2PK13GDALRPCInfoV2idPPc.

        Notes
        -----
        Explicit control of the transformer (and open datasets if RPC_DEM
        is specified) can be achieved by use within a context manager or 
        by calling `close()` method e.g.

        >>> with rasterio.transform.RPCTransformer(rpcs) as transform:
        ...    transform.xy(0, 0)
        >>> transform.xy(0, 0)
        ValueError: Unexpected NULL transformer

        Coordinate transformations using RPCs are typically:
            1. Only well-defined over the extent of the dataset the RPCs were generated.
            2. Require accurate height values in order to provide accurate results.
               Consider using RPC_DEM to supply a DEM to sample accurate height measurements
               from.
        """
        cdef char **papszMD = NULL
        cdef char **options = NULL
        cdef int bReversed = 1
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
            if key == b"RPC_DEM":
                # don't .upper() since might be a path
                val = str(val).encode('utf-8')
            else:
                val = str(val).upper().encode('utf-8')
            options = CSLSetNameValue(
                options, <const char *>key, <const char *>val)
            log.debug("Set RPCTransformer option {0!r}={1!r}".format(key, val))

        try:
            GDALExtractRPCInfo(papszMD, &rpcinfo)
            self._transformer = exc_wrap_pointer(GDALCreateRPCTransformer(&rpcinfo, bReversed, dfPixErrThreshold, options))
            self._closed = False
        finally:
            CSLDestroy(options)
            CSLDestroy(papszMD)

    def _transform(self, xs, ys, zs, transform_direction):
        """
        General computation of dataset pixel/line <-> lon/lat/height coordinates using RPCs

        Parameters
        ----------
        xs, ys, zs : list
            List of coordinates to be transformed. May be either pixel/line/height or
            lon/lat/height)
        transform_direction : TransformDirection
            The transform direction i.e. forward implies pixel/line -> lon/lat/height
            while reverse implies lon/lat/height -> pixel/line. 

        Raises
        ------
        ValueError
            If transformer is NULL

        Warns
        -----
        rasterio.errors.TransformWarning
            If one or more coordinates failed to transform

        Returns
        -------
        tuple of list
    
        Notes
        -----
        When RPC_DEM option is used, height (zs) values in _transform are ignored by GDAL and instead sampled from a DEM

        """
        if self._transformer == NULL:
            raise ValueError("Unexpected NULL transformer")

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
                TransformWarning)
            res_xs = [0] * n
            res_ys = [0] * n
            res_zs = [0] * n
            checked = False
            for i in range(n):
                # GDALRPCTransformer may return a success overall despite individual points failing. Warn once.
                if not panSuccess[i] and not checked:
                    warnings.warn(
                    "One or more points could not be transformed using RPCs.",
                    TransformWarning)
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

    def close(self):
        """
        Destroy transformer
        """
        if self._transformer != NULL:
            GDALDestroyRPCTransformer(self._transformer)
        self._transformer = NULL
        self._closed = True

    @property
    def closed(self):
        """
        Returns if transformer is NULL
        """
        return self._closed

cdef class GCPTransformerBase:
    cdef void *_transformer
    cdef bint _closed

    def __cinit__(self):
        self._transformer = NULL
        self._closed = True

    def __dealloc__(self):
        self.close()

    def __init__(self, gcps):
        """
        Construct a new GCP transformer

        The RPCs map geographic coordinates referenced against the WGS84 ellipsoid (longitude, latitude, height)
        to image pixel/line coordinates. The reverse is done through an iterative solver implemented
        in GDAL.

        Parameters
        ----------
        gcps : a sequence of GroundControlPoint
            Ground Control Points for a dataset.
        """
        cdef int bReversed = 1
        cdef int nReqOrder = 0  # let GDAL determine polynomial order
        cdef GDAL_GCP *gcplist = <GDAL_GCP *>CPLMalloc(len(gcps) * sizeof(GDAL_GCP))
        cdef int nGCPCount = len(gcps)

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
            self._transformer = exc_wrap_pointer(GDALCreateGCPTransformer(nGCPCount, gcplist, nReqOrder, bReversed))
            self._closed = False
        finally:
            CPLFree(gcplist)

    def _transform(self, xs, ys, zs, transform_direction):
        """
        General computation of dataset pixel/line <-> lon/lat/height coordinates using GCPs

        Parameters
        ----------
        xs, ys, zs : list
            List of coordinates to be transformed. May be either pixel/line/height or
            lon/lat/height)
        transform_direction : TransformDirection
            The transform direction i.e. forward implies pixel/line -> lon/lat/height
            while reverse implies lon/lat/height -> pixel/line. 

        Raises
        ------
        ValueError
            If transformer is NULL

        Warns
        -----
        rasterio.errors.TransformWarning
            If one or more coordinates failed to transform

        Returns
        -------
        tuple of list
        """
        if self._transformer == NULL:
            raise ValueError("Unexpected NULL transformer")

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
            err = GDALGCPTransform(self._transformer, bDstToSrc, n, x, y, z, panSuccess)
            if err == GDALError.failure:
                warnings.warn(
                "Could not transform points using GCPs.",
                TransformWarning)
            res_xs = [0] * n
            res_ys = [0] * n
            res_zs = [0] * n
            checked = False
            for i in range(n):
                # GDALGCPTransformer may return a success overall despite individual points failing. Warn once.
                if not panSuccess[i] and not checked:
                    warnings.warn(
                    "One or more points could not be transformed using GCPs.",
                    TransformWarning)
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

    def close(self):
        """
        Destroy transformer
        """
        if self._transformer != NULL:
            GDALDestroyGCPTransformer(self._transformer)
        self._transformer = NULL
        self._closed = True

    @property
    def closed(self):
        """
        Returns if transformer is NULL
        """
        return self._closed