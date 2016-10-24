# GDAL function definitions.

include "gdal.pxi"


cdef extern from "cpl_string.h" nogil:

    int CSLCount(char **papszStrList)
    char **CSLAddNameValue(char **papszStrList, const char *pszName,
                           const char *pszValue)
    char **CSLDuplicate(char **papszStrList)
    int CSLFindName(char **papszStrList, const char *pszName)
    int CSLFetchBoolean(char **papszStrList, const char *pszName, int default)
    const char *CSLFetchNameValue(char **papszStrList, const char *pszName)
    char **CSLSetNameValue(char **list, char *name, char *val)
    void CSLDestroy(char **list)


cdef extern from "cpl_vsi.h" nogil:

    unsigned char *VSIGetMemFileBuffer(const char *path,
                                       vsi_l_offset *data_len,
                                       int take_ownership)
    VSILFILE *VSIFileFromMemBuffer(const char *path, void *data,
                                   vsi_l_offset data_len, int take_ownership)
    VSILFILE* VSIFOpenL(const char *path, const char *mode)
    int VSIFCloseL(VSILFILE *fp)
    int VSIUnlink(const char *path)

    int VSIFFlushL(VSILFILE *fp)
    size_t VSIFReadL(void *buffer, size_t nSize, size_t nCount, VSILFILE *fp)
    int VSIFSeekL(VSILFILE *fp, vsi_l_offset nOffset, int nWhence)
    vsi_l_offset VSIFTellL(VSILFILE *fp)
    int VSIFTruncateL(VSILFILE *fp, vsi_l_offset nNewSize)
    size_t VSIFWriteL(void *buffer, size_t nSize, size_t nCount, VSILFILE *fp)


cdef extern from "cpl_error.h" nogil:

    void CPLErrorReset()
    int CPLGetLastErrorNo()
    const char* CPLGetLastErrorMsg()
    CPLErr CPLGetLastErrorType()
    void CPLPushErrorHandler(CPLErrorHandler handler)
    void CPLPopErrorHandler()


cdef extern from "ogr_srs_api.h" nogil:

    OGRCoordinateTransformationH OCTNewCoordinateTransformation(
                                        OGRSpatialReferenceH source,
                                        OGRSpatialReferenceH dest)
    void OCTDestroyCoordinateTransformation(
        OGRCoordinateTransformationH source)
    int OCTTransform(OGRCoordinateTransformationH ct, int nCount, double *x,
                     double *y, double *z)
    int OSRAutoIdentifyEPSG(OGRSpatialReferenceH srs)
    void OSRCleanup()
    OGRSpatialReferenceH OSRClone(OGRSpatialReferenceH srs)
    void OSRDestroySpatialReference(OGRSpatialReferenceH srs)
    int OSRExportToProj4(OGRSpatialReferenceH srs, char **params)
    int OSRExportToWkt(OGRSpatialReferenceH srs, char **params)
    int OSRFixup(OGRSpatialReferenceH srs)
    const char *OSRGetAuthorityName(OGRSpatialReferenceH srs, const char *key)
    const char *OSRGetAuthorityCode(OGRSpatialReferenceH srs, const char *key)
    int OSRImportFromEPSG(OGRSpatialReferenceH srs, int code)
    int OSRImportFromProj4(OGRSpatialReferenceH srs, const char *proj)
    int OSRIsGeographic(OGRSpatialReferenceH srs)
    int OSRIsProjected(OGRSpatialReferenceH srs)
    int OSRIsSame(OGRSpatialReferenceH srs1, OGRSpatialReferenceH srs2)
    OGRSpatialReferenceH OSRNewSpatialReference(const char *wkt)
    void OSRRelease(OGRSpatialReferenceH srs)
    int OSRSetFromUserInput(OGRSpatialReferenceH srs, const char *input)


cdef extern from "ogr_api.h" nogil:

    void OGRRegisterAll()
    void OGRCleanupAll()
    int OGRGetDriverCount()


cdef extern from "gdal.h" nogil:

    void GDALAllRegister()
    void GDALDestroyDriverManager()
    int GDALGetDriverCount()
    GDALDriverH GDALGetDriver(int i)
    const char *GDALGetDriverShortName(GDALDriverH driver)
    const char *GDALGetDriverLongName(GDALDriverH driver)
    const char* GDALGetDescription(GDALMajorObjectH obj)
    void GDALSetDescription(GDALMajorObjectH obj, const char *text)
    GDALDriverH GDALGetDriverByName(const char *name)
    GDALDatasetH GDALOpen(const char *filename, int access) # except -1
    void GDALFlushCache(GDALDatasetH hds)
    void GDALClose(GDALDatasetH hds)
    GDALDriverH GDALGetDatasetDriver(GDALDatasetH hds)
    int GDALGetGeoTransform(GDALDatasetH hds, double *transform)
    const char *GDALGetProjectionRef(GDALDatasetH hds)
    int GDALGetRasterXSize(GDALDatasetH hds)
    int GDALGetRasterYSize(GDALDatasetH hds)
    int GDALGetRasterCount(GDALDatasetH hds)
    GDALRasterBandH GDALGetRasterBand(GDALDatasetH hds, int num)
    GDALRasterBandH GDALGetOverview(GDALRasterBandH hband, int num)
    int GDALGetRasterBandXSize(GDALRasterBandH hband)
    int GDALGetRasterBandYSize(GDALRasterBandH hband)
    const char *GDALGetRasterUnitType(GDALRasterBandH hband)
    CPLErr GDALSetRasterUnitType(GDALRasterBandH hband, const char *val)
    int GDALSetGeoTransform(GDALDatasetH hds, double *transform)
    int GDALSetProjection(GDALDatasetH hds, const char *wkt)
    void GDALGetBlockSize(GDALRasterBandH , int *xsize, int *ysize)
    int GDALGetRasterDataType(GDALRasterBandH band)
    double GDALGetRasterNoDataValue(GDALRasterBandH band, int *success)
    int GDALSetRasterNoDataValue(GDALRasterBandH band, double value)
    int GDALDatasetRasterIO(GDALRasterBandH band, int, int xoff, int yoff,
                            int xsize, int ysize, void *buffer, int width,
                            int height, int, int count, int *bmap, int poff,
                            int loff, int boff)
    int GDALRasterIO(GDALRasterBandH band, int, int xoff, int yoff, int xsize,
                     int ysize, void *buffer, int width, int height, int,
                     int poff, int loff)
    int GDALFillRaster(GDALRasterBandH band, double rvalue, double ivalue)
    GDALDatasetH GDALCreate(GDALDriverH driver, const char *path, int width,
                            int height, int nbands, GDALDataType dtype,
                            const char **options)
    GDALDatasetH GDALCreateCopy(GDALDriverH driver, const char *path,
                                GDALDatasetH hds, int strict, char **options,
                                void *progress_func, void *progress_data)
    char** GDALGetMetadata(GDALMajorObjectH obj, const char *pszDomain)
    int GDALSetMetadata(GDALMajorObjectH obj, char **papszMD,
                        const char *pszDomain)
    const char* GDALGetMetadataItem(GDALMajorObjectH obj, const char *pszName,
                                    const char *pszDomain)
    int GDALSetMetadataItem(GDALMajorObjectH obj, const char *pszName,
                            const char *pszValue, const char *pszDomain)
    const GDALColorEntry *GDALGetColorEntry(GDALColorTableH table, int)
    void GDALSetColorEntry(GDALColorTableH table, int i,
                           const GDALColorEntry *poEntry)
    int GDALSetRasterColorTable(GDALRasterBandH band, GDALColorTableH table)
    GDALColorTableH GDALGetRasterColorTable(GDALRasterBandH band)
    GDALColorTableH GDALCreateColorTable(int)
    void GDALDestroyColorTable(GDALColorTableH table)
    int GDALGetColorEntryCount(GDALColorTableH table)
    int GDALGetRasterColorInterpretation(GDALRasterBandH band)
    int GDALSetRasterColorInterpretation(GDALRasterBandH band, int)
    int GDALGetMaskFlags(GDALRasterBandH band)
    void *GDALGetMaskBand(GDALRasterBandH band)
    int GDALCreateMaskBand(GDALDatasetH hds, int flags)
    int GDALGetOverviewCount(GDALRasterBandH band)
    int GDALBuildOverviews(GDALDatasetH hds, const char *resampling,
                           int nOverviews, int *overviews, int nBands,
                           int *bands, void *progress_func,
                           void *progress_data)
    int GDALCheckVersion(int nVersionMajor, int nVersionMinor,
                         const char *pszCallingComponentName)
    const char* GDALVersionInfo(const char *pszRequest)


cdef extern from "gdalwarper.h":

    GDALWarpOptions *GDALCreateWarpOptions()
    void GDALDestroyWarpOptions(GDALWarpOptions *options)


cdef extern from "gdal_alg.h":

    int GDALPolygonize(GDALRasterBandH band, GDALRasterBandH mask_band,
                       OGRLayerH layer, int fidx, char **options,
                       void *progress_func, void *progress_data)
    int GDALFPolygonize(GDALRasterBandH band, GDALRasterBandH mask_band,
                        OGRLayerH layer, int fidx, char **options,
                        void *progress_func, void *progress_data)
    int GDALSieveFilter(GDALRasterBandH src_band, GDALRasterBandH mask_band,
                        GDALRasterBandH dst_band, int size, int connectivity,
                        char **options, void *progress_func,
                        void *progress_data)
    int GDALRasterizeGeometries(GDALDatasetH hds, int band_count,
                                int *dst_bands, int geom_count,
                                OGRGeometryH *geometries,
                                GDALTransformerFunc transform_func,
                                void *transform, double *pixel_values,
                                char **options, void *progress_func,
                                void *progress_data)
    void *GDALCreateGenImgProjTransformer(GDALDatasetH src_hds,
                                 const char *pszSrcWKT, GDALDatasetH dst_hds,
                                 const char *pszDstWKT,
                                 int bGCPUseOK, double dfGCPErrorThreshold,
                                 int nOrder)
    void *GDALCreateGenImgProjTransformer3(
            const char *pszSrcWKT, const double *padfSrcGeoTransform,
            const char *pszDstWKT, const double *padfDstGeoTransform)
    int GDALGenImgProjTransform(void *pTransformArg, int bDstToSrc,
                                int nPointCount, double *x, double *y,
                                double *z, int *panSuccess)
    void GDALDestroyGenImgProjTransformer(void *)
    void *GDALCreateApproxTransformer(GDALTransformerFunc pfnRawTransformer,
                                      void *pRawTransformerArg,
                                      double dfMaxError)
    int  GDALApproxTransform(void *pTransformArg, int bDstToSrc, int npoints,
                             double *x, double *y, double *z, int *panSuccess)
    void GDALDestroyApproxTransformer(void *)
    void GDALApproxTransformerOwnsSubtransformer(void *, int)
    int GDALFillNodata(GDALRasterBandH dst_band, GDALRasterBandH mask_band,
                       double max_search_distance, int deprecated,
                       int smoothing_iterations, char **options,
                       void *progress_func, void *progress_data)
    int GDALChecksumImage(GDALRasterBandH band, int xoff, int yoff, int width,
                          int height)
    int GDALSuggestedWarpOutput2(
            GDALDatasetH hSrcDS,GDALTransformerFunc pfnRawTransformer,
            void * pTransformArg, double * padfGeoTransformOut, int * pnPixels,
            int * pnLines, double * padfExtent, int nOptions)
