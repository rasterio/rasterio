include "rasterio/gdal.pxi"

cdef extern from "gdal_utils.h" nogil:

    ctypedef struct GDALTranslateOptions
    ctypedef struct GDALTranslateOptionsForBinary

    void GDALTranslateOptionsFree(GDALTranslateOptions *psOptions)
    GDALDatasetH GDALTranslate(const char *pszDestFilename, GDALDatasetH hSrcDataset,
                               const GDALTranslateOptions *psOptions, int *pbUsageError)
    GDALTranslateOptions *GDALTranslateOptionsNew(char **papszArgv, GDALTranslateOptionsForBinary *psOptionsForBinary)
