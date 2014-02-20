# GDAL function definitions.
#

cdef extern from "cpl_conv.h":
    void    CPLFree (void *ptr)
    void    CPLSetThreadLocalConfigOption (char *key, char *val)

cdef extern from "cpl_string.h":
    int CSLCount (char **papszStrList)
    char ** CSLAddNameValue (char **papszStrList, const char *pszName, const char *pszValue)
    int CSLFindName (char **papszStrList, const char *pszName)
    char ** CSLSetNameValue (char **list, char *name, char *val)
    void    CSLDestroy (char **list)

cdef extern from "ogr_srs_api.h":
    void    OSRCleanup ()
    void *  OSRClone (void *srs)
    void    OSRDestroySpatialReference (void *srs)
    int     OSRExportToProj4 (void *srs, char **params)
    int     OSRExportToWkt (void *srs, char **params)
    int     OSRImportFromProj4 (void *srs, char *proj)
    void *  OSRNewSpatialReference (char *wkt)
    void    OSRRelease (void *srs)

cdef extern from "gdal.h":
    void GDALAllRegister()
    int GDALGetDriverCount()

    void * GDALGetDriverByName(const char *name)
    void * GDALOpen(const char *filename, int access)
    
    void GDALClose(void *ds)
    void * GDALGetDatasetDriver(void *ds)
    int GDALGetGeoTransform	(void *ds, double *transform)
    const char * GDALGetProjectionRef(void *ds)
    int GDALGetRasterXSize(void *ds)
    int GDALGetRasterYSize(void *ds)
    int GDALGetRasterCount(void *ds)
    void * GDALGetRasterBand(void *ds, int num)
    int GDALSetGeoTransform	(void *ds, double *transform)
    int GDALSetProjection(void *ds, const char *wkt)

    void GDALGetBlockSize(void *band, int *xsize, int *ysize)
    int GDALGetRasterDataType(void *band)
    double GDALGetRasterNoDataValue(void *band, int *success)
    int GDALRasterIO(void *band, int access, int xoff, int yoff, int xsize, int ysize, void *buffer, int width, int height, int data_type, int poff, int loff)
    int GDALSetRasterNoDataValue(void *band, double value)

    void * GDALCreate(void *driver, const char *filename, int width, int height, int nbands, int dtype, const char **options)
    void * GDALCreateCopy(void *driver, const char *filename, void *ds, int strict, char **options, void *progress_func, void *progress_data)
    const char * GDALGetDriverShortName(void *driver)
    const char * GDALGetDriverLongName(void *driver)

    char** GDALGetMetadata (void *hObject, const char *pszDomain)
    int GDALSetMetadata (void *hObject, char **papszMD, const char *pszDomain)
    const char* GDALGetMetadataItem(void *hObject, const char *pszName, const char *pszDomain)
    int GDALSetMetadataItem (void *hObject, const char *pszName, const char *pszValue, const char *pszDomain)

    ctypedef struct GDALColorEntry:
        short c1
        short c2
        short c3
        short c4

    const GDALColorEntry *GDALGetColorEntry (void *hTable, int)
    void GDALSetColorEntry (void *hTable, int i, const GDALColorEntry *poEntry)
    int GDALSetRasterColorTable (void *hBand, void *hTable)
    void *GDALGetRasterColorTable (void *hBand)
    void *GDALCreateColorTable (int)
    void GDALDestroyColorTable (void *hTable)
    int GDALGetColorEntryCount (void *hTable)
    int GDALGetRasterColorInterpretation (void *hBand)
    int GDALSetRasterColorInterpretation (void *hBand, int)

    void *GDALGetMaskBand (void *hBand)
    int GDALCreateMaskBand (void *hDS, int flags)

cdef extern from "gdal_alg.h":
    int GDALPolygonize(void *src_band, void *mask_band, void *layer, int fidx, char **options, void *progress_func, void *progress_data)
    int GDALSieveFilter(void *src_band, void *mask_band, void *dst_band, int size, int connectivity, char **options, void *progress_func, void *progress_data)

