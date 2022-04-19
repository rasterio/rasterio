cdef extern from "gdal.h" nogil:
    int GDALCheckVersion(int nVersionMajor, int nVersionMinor,
                         const char *pszCallingComponentName)
    const char* GDALVersionInfo(const char *pszRequest)

IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION, CTE_GDAL_PATCH_VERSION) >= (3, 0, 1):
    cdef extern from "ogr_srs_api.h" nogil:
        void OSRGetPROJVersion(int *pnMajor, int *pnMinor, int *pnPatch)

IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 4):
    cdef extern from "ogr_core.h" nogil:
        bint OGRGetGEOSVersion(int *pnMajor, int *pnMinor, int *pnPatch)
