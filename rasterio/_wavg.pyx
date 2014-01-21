
import logging
import numpy as np
cimport numpy as np
import os

ctypedef np.uint8_t DTYPE_UBYTE_t
ctypedef np.float_t DTYPE_FLOAT_t

cdef extern from "math.h":
    double exp(double x)

# GDAL function definitions. TODO: into a .pyd file.
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

logger = logging.getLogger('fasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
logger.addHandler(NullHandler())

cdef void weights(
        unsigned char[:, :] image, 
        unsigned char[:, :] quality,
        double[:, :] product,
        double[:, :] weight,
        double Q=10.0,
        double K=1.0
        ):
    cdef int i, j
    cdef float p, wq, w
    I = image.shape[0]
    J = image.shape[1]
    for i in range(I):
        for j in range(J):
            p = product[i, j]
            w = weight[i, j]
            wq = 1.0/(1.0 + exp(-K*(<double>quality[i, j]-Q)))
            weight[i, j] = w + wq
            product[i, j] = p + wq*<double>image[i, j]

def ndvi(double [:, :] vis, double [:, :] nir):
    cdef i, j
    # cdef double v, n
    cdef double [:, :] prod
    I = vis.shape[0]
    J = vis.shape[1]
    product = np.empty((I, J), dtype=np.float)
    prod = product
    for i in range(I):
        for j in range(J):
            # v = vis[i,j]
            # n = nir[i,j]
            prod[i,j] = (nir[i,j]-vis[i,j])/(nir[i,j]+vis[i,j])
    return product

def avg(input_filenames, output_filename, origin, exponent):
    """Average input files and output."""
    # TODO: validate arguments.
    cdef void *ds
    cdef void *drv
    cdef void *out_ds
    cdef void *band
    cdef const char *fname
    cdef double q = origin
    cdef double k = exponent

    cdef np.ndarray[DTYPE_UBYTE_t, ndim=2, mode="c"] im

    GDALAllRegister()
    
    # Grab parameters of the input data and initialize an output file
    cdef const char *first_name = input_filenames[0]
    ds = GDALOpen(first_name, 0)
    width = GDALGetRasterXSize(ds)
    height = GDALGetRasterYSize(ds)
    nbands = GDALGetRasterCount(ds)

    cdef const char *output_name = output_filename
    drv = GDALGetDriverByName("GTiff")
    out_ds = GDALCreateCopy(drv, output_name, ds, 0, NULL, NULL, NULL)
    GDALClose(out_ds)
    GDALClose(ds)

    image = np.empty((height, width), np.ubyte)
    quality = np.ones((height, width), np.ubyte)
    product = np.zeros((height, width), np.float_)
    weight = np.zeros((height, width), np.float_)
    
    # Open output image for update
    out_ds = GDALOpen(output_name, 1)

    for i in range(5):

        for filename in input_filenames:
            fname = filename
            ds = GDALOpen(fname, 0)
            band = GDALGetRasterBand(ds, i+1)
            im = image # casts the numpy array to a C type
            GDALRasterIO(
                band, 0, 0, 0, width, height, 
                &im[0,0], width, height, 1, 0, 0)

            # Get the quality band.
            if i==0:
                band = GDALGetRasterBand(ds, 6)
                im = quality # casts the numpy array to a C type
                GDALRasterIO(
                    band, 0, 0, 0, width, height, 
                    &im[0,0], width, height, 1, 0, 0)
                
            GDALClose(ds)
            
            logger.debug("Band: %d, File: %s\n", i, filename)
            
            # Compute this file's contribution to the product and weight
            weights(image, quality, product, weight, q, k)

            logger.debug("Product range: %r\n", [np.min(product), np.max(product)])
            logger.debug("Weight range: %r\n", [np.min(weight), np.max(weight)])
        
        product /= weight
        
        np.rint(product, image)

        band = GDALGetRasterBand(out_ds, i+1)
        im = image
        GDALRasterIO(
            band, 1, 0, 0, width, height, 
            &im[0,0], width, height, 1, 0, 0)

    GDALClose(out_ds)
    return 0

