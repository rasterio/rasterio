# GDAL function definitions.
#

cdef extern from "cpl_conv.h":
    void    CPLFree (void *ptr)
    void    CPLSetThreadLocalConfigOption (char *key, char *val)

cdef extern from "cpl_string.h":
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
    
    int GDALGetRasterDataType(void *band)
    int GDALRasterIO(void *band, int access, int xoff, int yoff, int xsize, int ysize, void *buffer, int width, int height, int data_type, int poff, int loff)

    void * GDALCreate(void *driver, const char *filename, int width, int height, int nbands, int dtype, const char **options)
    void * GDALCreateCopy(void *driver, const char *filename, void *ds, int strict, char **options, void *progress_func, void *progress_data)
    const char * GDALGetDriverShortName(void *driver)
    const char * GDALGetDriverLongName(void *driver)

