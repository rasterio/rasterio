# GDAL function definitions.
#
cdef extern from "gdal.h":
    void GDALAllRegister()
    void * GDALOpen(const char *filename, int access)
    void GDALClose(void *ds)
    int GDALGetRasterXSize(void *ds)
    int GDALGetRasterYSize(void *ds)
    int GDALGetRasterCount(void *ds)
    void * GDALGetRasterBand(void *ds, int num)
    int GDALRasterIO(void *band, int access, int xoff, int yoff, int xsize, int ysize, void *buffer, int width, int height, int data_type, int poff, int loff)
    void * GDALCreateCopy(void *driver, const char *filename, void *ds, int strict, char **options, void *progress_func, void *progress_data)
    void * GDALGetDriverByName(const char *name)

