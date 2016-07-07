# GDAL type definitions.


cdef extern from "cpl_conv.h" nogil:

    void *CPLMalloc(size_t)
    void CPLFree(void* ptr)
    void CPLSetThreadLocalConfigOption(const char* key, const char* val)
    void CPLSetConfigOption(const char* key, const char* val)
    const char* CPLGetConfigOption(const char* key, const char* default)


cdef extern from "cpl_error.h":

    ctypedef enum CPLErr:
        CE_None
        CE_Debug
        CE_Warning
        CE_Failure
        CE_Fatal

    # CPLErrorNum eludes me at the moment, I'm calling it 'int'
    # for now.
    ctypedef void (*CPLErrorHandler)(CPLErr, int, const char*)


cdef extern from "cpl_vsi.h":

    ctypedef int vsi_l_offset


cdef extern from "gdal.h":

    ctypedef void * GDALMajorObjectH
    ctypedef void * GDALDatasetH
    ctypedef void * GDALRasterBandH
    ctypedef void * GDALDriverH
    ctypedef void * GDALColorTableH
    ctypedef void * GDALRasterAttributeTableH
    ctypedef void * GDALAsyncReaderH

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

    ctypedef struct GDALColorEntry:
        short c1
        short c2
        short c3
        short c4


cdef extern from "ogr_api.h":

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


cdef extern from "ogr_srs_api.h":

    ctypedef void * OGRCoordinateTransformationH
    ctypedef void * OGRSpatialReferenceH


cdef extern from "gdalwarper.h":

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
