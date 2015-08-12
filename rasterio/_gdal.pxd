# GDAL function definitions.
#

cdef extern from "cpl_conv.h" nogil:
    void *  CPLMalloc (size_t)
    void    CPLFree (void *ptr)
    void    CPLSetThreadLocalConfigOption (char *key, char *val)
    const char *CPLGetConfigOption (char *, char *)

cdef extern from "cpl_string.h":
    int CSLCount (char **papszStrList)
    char ** CSLAddNameValue (char **papszStrList, const char *pszName, const char *pszValue)
    char ** CSLDuplicate (char ** papszStrList)

    int CSLFindName (char **papszStrList, const char *pszName)
    const char * CSLFetchNameValue (char **papszStrList, const char *pszName)
    char ** CSLSetNameValue (char **list, char *name, char *val)
    void    CSLDestroy (char **list)

cdef extern from "cpl_vsi.h":
    ctypedef int vsi_l_offset
    unsigned char * VSIGetMemFileBuffer (const char *filename,
                                         vsi_l_offset *data_len,
                                         int take_ownership)

cdef extern from "ogr_srs_api.h":
    void *  OCTNewCoordinateTransformation (void *source, void *dest)
    void    OCTDestroyCoordinateTransformation (void *source)
    int     OCTTransform (void *ct, int nCount, double *x, double *y, double *z)

    int     OSRAutoIdentifyEPSG (void *srs)
    void    OSRCleanup ()
    void *  OSRClone (void *srs)
    void    OSRDestroySpatialReference (void *srs)
    int     OSRExportToProj4 (void *srs, char **params)
    int     OSRExportToWkt (void *srs, char **params)
    int     OSRFixup(void *srs)
    const char * OSRGetAuthorityName (void *srs, const char *key)
    const char * OSRGetAuthorityCode (void *srs, const char *key)
    int     OSRImportFromEPSG (void *srs, int code)
    int     OSRImportFromProj4 (void *srs, char *proj)
    int     OSRIsGeographic(void *srs)
    int     OSRIsProjected(void *srs)
    int     OSRIsSame(void *srs1, void *srs2)
    void *  OSRNewSpatialReference (char *wkt)
    void    OSRRelease (void *srs)
    int     OSRSetFromUserInput (void *srs, char *input)


cdef extern from "gdal.h" nogil:
    void GDALAllRegister()
    int GDALGetDriverCount()
    void * GDALGetDriver(int)
    const char* GDALGetDescription (void *)
    void GDALSetDescription (void *, const char *)

    void * GDALGetDriverByName(const char *name)
    void * GDALOpen(const char *filename, int access) # except -1
    void GDALFlushCache (void *ds)
    void GDALClose(void *ds)
    void * GDALGetDatasetDriver(void *ds)
    int GDALGetGeoTransform	(void *ds, double *transform)
    const char * GDALGetProjectionRef(void *ds)
    int GDALGetRasterXSize(void *ds)
    int GDALGetRasterYSize(void *ds)
    int GDALGetRasterCount(void *ds)

    void * GDALGetRasterBand(void *ds, int num)
    void * GDALGetOverview(void *hband, int num)

    int GDALGetRasterBandXSize(void *hband)
    int GDALGetRasterBandYSize(void *hband)

    int GDALSetGeoTransform	(void *ds, double *transform)
    int GDALSetProjection(void *ds, const char *wkt)

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

    ctypedef enum GDALRWFlag:
        GF_Read
        GF_Write

    void GDALGetBlockSize(void *band, int *xsize, int *ysize)
    int GDALGetRasterDataType(void *band)
    double GDALGetRasterNoDataValue(void *band, int *success)
    int GDALSetRasterNoDataValue(void *band, double value)
    int GDALDatasetRasterIO(void *band, int, int xoff, int yoff, int xsize, int ysize, void *buffer, int width, int height, int, int count, int *bmap, int poff, int loff, int boff)
    int GDALRasterIO(void *band, int, int xoff, int yoff, int xsize, int ysize, void *buffer, int width, int height, int, int poff, int loff)
    int GDALFillRaster(void *band, double rvalue, double ivalue)

    void * GDALCreate(void *driver, const char *filename, int width, int height, int nbands, GDALDataType dtype, const char **options)
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

    const GDALColorEntry * GDALGetColorEntry (void *hTable, int)
    void GDALSetColorEntry (void *hTable, int i, const GDALColorEntry *poEntry)
    int GDALSetRasterColorTable (void *hBand, void *hTable)
    void *GDALGetRasterColorTable (void *hBand)
    void *GDALCreateColorTable (int)
    void GDALDestroyColorTable (void *hTable)
    int GDALGetColorEntryCount (void *hTable)
    int GDALGetRasterColorInterpretation (void *hBand)
    int GDALSetRasterColorInterpretation (void *hBand, int)

    int GDALGetMaskFlags (void *hBand)
    void *GDALGetMaskBand (void *hBand)
    int GDALCreateMaskBand (void *hDS, int flags)

    int GDALGetOverviewCount (void *hBand)
    int GDALBuildOverviews (void *hDS, const char *resampling, int nOverviews, int *overviews, int nBands, int *bands, void *progress_func, void *progress_data)

cdef extern from "gdalwarper.h":

    ctypedef enum GDALResampleAlg:
        GRA_NearestNeighbour
        GRA_Bilinear
        GRA_Cubic
        GRA_CubicSpline
        GRA_Lanczos
        GRA_Average 
        GRA_Mode

    ctypedef int (*GDALMaskFunc)( void *pMaskFuncArg,
                 int nBandCount, int eType, 
                 int nXOff, int nYOff, 
                 int nXSize, int nYSize,
                 unsigned char **papabyImageData, 
                 int bMaskIsFloat, void *pMask )

    ctypedef int (*GDALTransformerFunc)( void *pTransformerArg, 
                        int bDstToSrc, int nPointCount, 
                        double *x, double *y, double *z, int *panSuccess )

    ctypedef struct GDALWarpOptions:
        char **papszWarpOptions
        double dfWarpMemoryLimit
        GDALResampleAlg eResampleAlg
        GDALDataType eWorkingDataType
        void *hSrcDS
        void *hDstDS
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
        GDALMaskFunc        pfnSrcValidityMaskFunc
        void               *pSrcValidityMaskFuncArg
        GDALMaskFunc        pfnSrcDensityMaskFunc
        void               *pSrcDensityMaskFuncArg
        GDALMaskFunc        pfnDstDensityMaskFunc
        void               *pDstDensityMaskFuncArg
        GDALMaskFunc        pfnDstValidityMaskFunc
        void               *pDstValidityMaskFuncArg
        int              (*pfnPreWarpChunkProcessor)( void *pKern, void *pArg )
        void               *pPreWarpProcessorArg
        int              (*pfnPostWarpChunkProcessor)( void *pKern, void *pArg)
        void               *pPostWarpProcessorArg
        # Optional OGRPolygonH for a masking cutline. */
        void               *hCutline
        # Optional blending distance to apply across cutline in pixels, default is 0
        double              dfCutlineBlendDist

    GDALWarpOptions *GDALCreateWarpOptions()
    void GDALDestroyWarpOptions(GDALWarpOptions *)

cdef extern from "gdal_alg.h":
    
    int GDALPolygonize(void *src_band, void *mask_band, void *layer, int fidx, char **options, void *progress_func, void *progress_data)
    int GDALFPolygonize(void *src_band, void *mask_band, void *layer, int fidx, char **options, void *progress_func, void *progress_data)
    int GDALSieveFilter(void *src_band, void *mask_band, void *dst_band, int size, int connectivity, char **options, void *progress_func, void *progress_data)
    int GDALRasterizeGeometries(void *out_ds, int band_count, int *dst_bands, int geom_count, void **geometries,
                            GDALTransformerFunc transform_func, void *transform, double *pixel_values, char **options,
                            void *progress_func, void *progress_data)

    void *GDALCreateGenImgProjTransformer(void* hSrcDS, const char *pszSrcWKT,
                                 void* hDstDS, const char *pszDstWKT,
                                 int bGCPUseOK, double dfGCPErrorThreshold,
                                 int nOrder )
    int GDALGenImgProjTransform(void *pTransformArg, int bDstToSrc, int nPointCount, double *x, double *y, double *z, int *panSuccess )
    void GDALDestroyGenImgProjTransformer( void * )

    void *GDALCreateApproxTransformer( GDALTransformerFunc pfnRawTransformer, void *pRawTransformerArg, double dfMaxError )
    int  GDALApproxTransform(void *pTransformArg, int bDstToSrc, int nPointCount, double *x, double *y, double *z, int *panSuccess )
    void GDALDestroyApproxTransformer( void * )

    int GDALFillNodata(void *dst_band, void *mask_band, double max_search_distance, int deprecated, int smoothing_iterations, char **options, void *progress_func, void *progress_data)
    int GDALChecksumImage(void *band, int xoff, int yoff, int width, int height)
