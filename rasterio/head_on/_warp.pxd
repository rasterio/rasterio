include "rasterio/gdal.pxi"

cdef extern from "gdal_utils.h":

    ctypedef struct GDALWarpAppOptions
    ctypedef struct GDALWarpAppOptionsForBinary
    void GDALWarpAppOptionsFree(GDALWarpAppOptions *psOptions)
    void GDALWarpAppOptionsSetWarpOption(GDALWarpAppOptions *psOptions, const char *pszKey, const char *pszValue)

    GDALDatasetH GDALWarp(const char *pszDest, GDALDatasetH hDstDS, int nSrcCount, GDALDatasetH *pahSrcDS, const GDALWarpAppOptions *psOptions, int *pbUsageError)

    GDALWarpAppOptions* GDALWarpAppOptionsNew(char **papszArgv, GDALWarpAppOptionsForBinary *psOptionsForBinary)

