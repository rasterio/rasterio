# GDAL type definitions.


cdef extern from "cpl_conv.h":

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

    void CPLErrorReset()
    int CPLGetLastErrorNo()
    const char* CPLGetLastErrorMsg()
    CPLErr CPLGetLastErrorType()
    void CPLSetErrorHandler(CPLErrorHandler handler)


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

    void GDALAllRegister()
    void GDALDestroyDriverManager()
    int GDALGetDriverCount()
    GDALDriverH GDALGetDriver(int i)
    const char * GDALGetDriverShortName(GDALDriverH driver)
    const char * GDALGetDriverLongName(GDALDriverH driver)


cdef extern from "ogr_api.h":

    ctypedef void * OGRLayerH
    ctypedef void * OGRDataSourceH
    ctypedef void * OGRSFDriverH
    ctypedef void * OGRFieldDefnH
    ctypedef void * OGRFeatureDefnH
    ctypedef void * OGRFeatureH
    ctypedef void * OGRGeometryH

    void OGRRegisterAll()
    void OGRCleanupAll()
    int OGRGetDriverCount()


cdef extern from "ogr_srs_api.h":

    ctypedef void * OGRSpatialReferenceH
    ctypedef void * OGRCoordinateTransformationH
