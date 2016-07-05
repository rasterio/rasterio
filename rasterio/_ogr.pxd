cdef extern from "ogr_core.h":
    char *  OGRGeometryTypeToName(int)


cdef extern from "ogr_srs_api.h":

    ctypedef void * OGRSpatialReferenceH
    ctypedef void * OGRCoordinateTransformationH


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

    char *  OGR_Dr_GetName(OGRSFDriverH driver)
    OGRDataSourceH OGR_Dr_CreateDataSource(OGRSFDriverH driver, char *path, char **options)
    int     OGR_Dr_DeleteDataSource(OGRSFDriverH driver, char *)
    int     OGR_DS_DeleteLayer(OGRDataSourceH datasource, int n)
    OGRLayerH OGR_DS_CreateLayer(OGRDataSourceH datasource, char *name, OGRSpatialReferenceH crs, int geomType, char **options)
    void *  OGR_DS_ExecuteSQL(OGRDataSourceH datasource, char *name, void *filter, char *dialext)
    void    OGR_DS_Destroy(OGRDataSourceH datasource)
    OGRSFDriverH OGR_DS_GetDriver(OGRLayerH layer_defn)
    OGRLayerH OGR_DS_GetLayerByName(OGRDataSourceH datasource, char *name)
    int     OGR_DS_GetLayerCount(OGRDataSourceH datasource)
    OGRLayerH OGR_DS_GetLayer(OGRDataSourceH datasource, int n)
    void    OGR_DS_ReleaseResultSet(OGRDataSourceH datasource, void *results)
    int     OGR_DS_SyncToDisk(OGRDataSourceH datasource)
    OGRFeatureH OGR_F_Create(OGRFeatureDefnH featuredefn)
    void    OGR_F_Destroy(OGRFeatureH feature)
    long    OGR_F_GetFID(OGRFeatureH feature)
    int     OGR_F_IsFieldSet(OGRFeatureH feature, int n)
    int     OGR_F_GetFieldAsDateTime(OGRFeatureH feature, int n, int *y, int *m, int *d, int *h, int *m, int *s, int *z)
    double  OGR_F_GetFieldAsDouble(OGRFeatureH feature, int n)
    int     OGR_F_GetFieldAsInteger(OGRFeatureH feature, int n)
    char *  OGR_F_GetFieldAsString(OGRFeatureH feature, int n)
    int     OGR_F_GetFieldCount(OGRFeatureH feature)
    OGRFieldDefnH OGR_F_GetFieldDefnRef(OGRFeatureH feature, int n)
    int     OGR_F_GetFieldIndex(OGRFeatureH feature, char *name)
    OGRGeometryH OGR_F_GetGeometryRef(OGRFeatureH feature)
    void    OGR_F_SetFieldDateTime(OGRFeatureH feature, int n, int y, int m, int d, int hh, int mm, int ss, int tz)
    void    OGR_F_SetFieldDouble(OGRFeatureH feature, int n, double value)
    void    OGR_F_SetFieldInteger(OGRFeatureH feature, int n, int value)
    void    OGR_F_SetFieldString(OGRFeatureH feature, int n, char *value)
    int     OGR_F_SetGeometryDirectly(OGRFeatureH feature, OGRGeometryH geometry)
    void *  OGR_FD_Create(char *name)
    int     OGR_FD_GetFieldCount(OGRFeatureDefnH featuredefn)
    OGRFieldDefnH OGR_FD_GetFieldDefn(OGRFeatureDefnH featuredefn, int n)
    int     OGR_FD_GetGeomType(OGRFeatureDefnH featuredefn)
    char *  OGR_FD_GetName(OGRFeatureDefnH featuredefn)
    OGRFieldDefnH OGR_Fld_Create(char *name, int fieldtype)
    void    OGR_Fld_Destroy(OGRFieldDefnH)
    char *  OGR_Fld_GetNameRef(OGRFieldDefnH)
    int     OGR_Fld_GetPrecision(OGRFieldDefnH)
    int     OGR_Fld_GetType(OGRFieldDefnH)
    int     OGR_Fld_GetWidth(OGRFieldDefnH)
    void    OGR_Fld_Set(OGRFieldDefnH, char *name, int fieldtype, int width, int precision, int justification)
    void    OGR_Fld_SetPrecision(OGRFieldDefnH, int n)
    void    OGR_Fld_SetWidth(OGRFieldDefnH, int n)
    OGRErr  OGR_G_AddGeometryDirectly(OGRGeometryH geometry, void *part)
    void    OGR_G_AddPoint(OGRGeometryH geometry, double x, double y, double z)
    void    OGR_G_AddPoint_2D(OGRGeometryH geometry, double x, double y)
    void    OGR_G_CloseRings(OGRGeometryH geometry)
    OGRGeometryH OGR_G_CreateGeometry(int wkbtypecode)
    OGRGeometryH OGR_G_CreateGeometryFromJson(char *json)
    void    OGR_G_DestroyGeometry(OGRGeometryH geometry)
    unsigned char *  OGR_G_ExportToJson(OGRGeometryH geometry)
    void    OGR_G_ExportToWkb(OGRGeometryH geometry, int endianness, char *buffer)
    int     OGR_G_GetCoordinateDimension(OGRGeometryH geometry)
    int     OGR_G_GetGeometryCount(OGRGeometryH geometry)
    unsigned char *  OGR_G_GetGeometryName(OGRGeometryH geometry)
    int     OGR_G_GetGeometryType(OGRGeometryH geometry)
    OGRGeometryH OGR_G_GetGeometryRef(OGRGeometryH geometry, int n)
    int     OGR_G_GetPointCount(OGRGeometryH geometry)
    double  OGR_G_GetX(OGRGeometryH geometry, int n)
    double  OGR_G_GetY(OGRGeometryH geometry, int n)
    double  OGR_G_GetZ(OGRGeometryH geometry, int n)
    void    OGR_G_ImportFromWkb(OGRGeometryH geometry, unsigned char *bytes, int nbytes)
    int     OGR_G_WkbSize(OGRGeometryH geometry)
    OGRErr  OGR_L_CreateFeature(OGRLayerH layer, OGRFeatureH feature)
    int     OGR_L_CreateField(OGRLayerH layer, OGRFieldDefnH, int flexible)
    OGRErr  OGR_L_GetExtent(OGRLayerH layer, void *extent, int force)
    OGRFeatureH OGR_L_GetFeature(OGRLayerH layer, int n)
    int     OGR_L_GetFeatureCount(OGRLayerH layer, int m)
    void *  OGR_L_GetLayerDefn(OGRLayerH layer)
    char *  OGR_L_GetName(OGRLayerH layer)
    OGRFeatureH OGR_L_GetNextFeature(OGRLayerH layer)
    void *  OGR_L_GetSpatialFilter(OGRLayerH layer)
    OGRSpatialReferenceH OGR_L_GetSpatialRef(OGRLayerH layer)
    void    OGR_L_ResetReading(OGRLayerH layer)
    void    OGR_L_SetSpatialFilter(OGRLayerH layer, OGRGeometryH geometry)
    void    OGR_L_SetSpatialFilterRect(
                OGRLayerH layer, double minx, double miny, double maxx, double maxy)
    int     OGR_L_TestCapability(OGRLayerH layer, char *name)
    OGRSFDriverH OGRGetDriverByName(char *)
    void *  OGROpen(char *path, int mode, void *x)
    void *  OGROpenShared(char *path, int mode, void *x)
    int     OGRReleaseDataSource(OGRDataSourceH datasource)
    void    OGRRegisterAll()
    void    OGRCleanupAll()
