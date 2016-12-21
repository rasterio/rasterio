# GDAL API definitions.

from libc.stdio cimport FILE


cdef extern from "cpl_conv.h" nogil:

    void *CPLMalloc(size_t)
    void CPLFree(void* ptr)
    void CPLSetThreadLocalConfigOption(const char* key, const char* val)
    void CPLSetConfigOption(const char* key, const char* val)
    const char* CPLGetConfigOption(const char* key, const char* default)


cdef extern from "cpl_error.h" nogil:

    ctypedef enum CPLErr:
        CE_None
        CE_Debug
        CE_Warning
        CE_Failure
        CE_Fatal

    # CPLErrorNum eludes me at the moment, I'm calling it 'int'
    # for now.
    ctypedef void (*CPLErrorHandler)(CPLErr, int, const char*)

    void CPLErrorReset()
    int CPLGetLastErrorNo()
    const char* CPLGetLastErrorMsg()
    CPLErr CPLGetLastErrorType()
    void CPLPushErrorHandler(CPLErrorHandler handler)
    void CPLPopErrorHandler()


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

    ctypedef int vsi_l_offset
    ctypedef FILE VSILFILE

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


cdef extern from "gdal.h" nogil:

    ctypedef void * GDALMajorObjectH
    ctypedef void * GDALDatasetH
    ctypedef void * GDALRasterBandH
    ctypedef void * GDALDriverH
    ctypedef void * GDALColorTableH
    ctypedef void * GDALRasterAttributeTableH
    ctypedef void * GDALAsyncReaderH

    ctypedef long long GSpacing

    ctypedef enum GDALDataType:
        GDT_Unknown
        GDT_Byte
        GDT_UInt16
        GDT_Int16
        GDT_UInt32
        GDT_Int32
        GDT_Float32
        GDT_Float64
        GDT_CInt16
        GDT_CInt32
        GDT_CFloat32
        GDT_CFloat64
        GDT_TypeCount

    ctypedef enum GDALAccess:
        GA_ReadOnly
        GA_Update

    ctypedef enum GDALRWFlag:
        GF_Read
        GF_Write

    ctypedef enum GDALRIOResampleAlg:
        GRIORA_NearestNeighbour
        GRIORA_Bilinear
        GRIORA_Cubic,
        GRIORA_CubicSpline
        GRIORA_Lanczos
        GRIORA_Average
        GRIORA_Mode
        GRIORA_Gauss

    ctypedef struct GDALColorEntry:
        short c1
        short c2
        short c3
        short c4

    ctypedef struct GDAL_GCP:
        char *pszId
        char *pszInfo
        double dfGCPPixel
        double dfGCPLine
        double dfGCPX
        double dfGCPY
        double dfGCPZ

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
    CPLErr GDALSetGCPs(GDALDatasetH hDS, int nGCPCount, const GDAL_GCP *pasGCPList,
                       const char *pszGCPProjection)
    const GDAL_GCP *GDALGetGCPs(GDALDatasetH hDS)
    int GDALGetGCPCount(GDALDatasetH hDS)
    const char *GDALGetGCPProjection(GDALDatasetH hDS)


cdef extern from "ogr_api.h" nogil:

    ctypedef void * OGRLayerH
    ctypedef void * OGRDataSourceH
    ctypedef void * OGRSFDriverH
    ctypedef void * OGRFieldDefnH
    ctypedef void * OGRFeatureDefnH
    ctypedef void * OGRFeatureH
    ctypedef void * OGRGeometryH

    ctypedef int OGRErr

    ctypedef struct OGREnvelope:
        double MinX
        double MaxX
        double MinY
        double MaxY

    void OGRRegisterAll()
    void OGRCleanupAll()
    int OGRGetDriverCount()


cdef extern from "gdalwarper.h" nogil:

    ctypedef enum GDALResampleAlg:
        GRA_NearestNeighbour
        GRA_Bilinear
        GRA_Cubic
        GRA_CubicSpline
        GRA_Lanczos
        GRA_Average
        GRA_Mode

    ctypedef int (*GDALMaskFunc)(
        void *pMaskFuncArg, int nBandCount, int eType, int nXOff, int nYOff,
        int nXSize, int nYSize, unsigned char **papabyImageData,
        int bMaskIsFloat, void *pMask)

    ctypedef int (*GDALTransformerFunc)(
        void *pTransformerArg, int bDstToSrc, int nPointCount, double *x,
        double *y, double *z, int *panSuccess)

    ctypedef struct GDALWarpOptions:
        char **papszWarpOptions
        double dfWarpMemoryLimit
        GDALResampleAlg eResampleAlg
        GDALDataType eWorkingDataType
        GDALDatasetH hSrcDS
        GDALDatasetH hDstDS
        # 0 for all bands
        int nBandCount
        # List of source band indexes
        int *panSrcBands
        # List of destination band indexes
        int *panDstBands
        # The source band so use as an alpha (transparency) value, 0=disabled
        int nSrcAlphaBand
        # The dest. band so use as an alpha (transparency) value, 0=disabled
        int nDstAlphaBand
        # The "nodata" value real component for each input band, if NULL there isn't one */
        double *padfSrcNoDataReal
        # The "nodata" value imaginary component - may be NULL even if real component is provided. */
        double *padfSrcNoDataImag
        # The "nodata" value real component for each output band, if NULL there isn't one */
        double *padfDstNoDataReal
        # The "nodata" value imaginary component - may be NULL even if real component is provided. */
        double *padfDstNoDataImag
        # GDALProgressFunc() compatible progress reporting function, or NULL if there isn't one. */
        void *pfnProgress
        # Callback argument to be passed to pfnProgress. */
        void *pProgressArg
        # Type of spatial point transformer function */
        GDALTransformerFunc pfnTransformer
        # Handle to image transformer setup structure */
        void *pTransformerArg
        GDALMaskFunc *papfnSrcPerBandValidityMaskFunc
        void **papSrcPerBandValidityMaskFuncArg
        GDALMaskFunc pfnSrcValidityMaskFunc
        void *pSrcValidityMaskFuncArg
        GDALMaskFunc pfnSrcDensityMaskFunc
        void *pSrcDensityMaskFuncArg
        GDALMaskFunc pfnDstDensityMaskFunc
        void *pDstDensityMaskFuncArg
        GDALMaskFunc pfnDstValidityMaskFunc
        void *pDstValidityMaskFuncArg
        int (*pfnPreWarpChunkProcessor)(void *pKern, void *pArg)
        void *pPreWarpProcessorArg
        int (*pfnPostWarpChunkProcessor)(void *pKern, void *pArg)
        void *pPostWarpProcessorArg
        # Optional OGRPolygonH for a masking cutline. */
        OGRGeometryH hCutline
        # Optional blending distance to apply across cutline in pixels, default is 0
        double dfCutlineBlendDist

    GDALWarpOptions *GDALCreateWarpOptions()
    void GDALDestroyWarpOptions(GDALWarpOptions *options)


cdef extern from "gdal_alg.h" nogil:

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
    void *GDALCreateGenImgProjTransformer2(GDALDatasetH src_hds, GDALDatasetH dst_hds, char **options)
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
            GDALDatasetH hSrcDS, GDALTransformerFunc pfnRawTransformer,
            void * pTransformArg, double * padfGeoTransformOut, int * pnPixels,
            int * pnLines, double * padfExtent, int nOptions)


cdef extern from "ogr_srs_api.h" nogil:

    ctypedef void * OGRCoordinateTransformationH
    ctypedef void * OGRSpatialReferenceH

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
