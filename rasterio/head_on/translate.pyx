import rasterio

include "rasterio/gdal.pxi"

from rasterio._io cimport DatasetReaderBase
from rasterio.head_on._translate cimport GDALTranslate, GDALTranslateOptions, GDALTranslateOptionsNew, GDALTranslateOptionsFree


cdef GDALTranslateOptions* create_translate_options(bands=None,
                                                    input_format=None,
                                                    output_format=None) except NULL:
    options = []
    if input_format:
        options += ['-if', str(input_format)]
    if output_format:
        options += ['-of', str(output_format)]
    if bands:
        for band in bands:
            options += ['-b', str(band)]
    enc_str_options = " ".join(options).encode('utf-8')
    cdef char** enc_str_options_ptr = CSLParseCommandLine(enc_str_options)

    cdef GDALTranslateOptions* translate_options = NULL
    with nogil:
         translate_options = GDALTranslateOptionsNew(enc_str_options_ptr, NULL)
    return translate_options

cpdef translate(src_ds,
                dst_ds,
                bands=None,
                input_format=None,
                output_format=None):

    cdef GDALDatasetH src_ds_ptr = NULL

    if isinstance(src_ds, str):
        src_rio = rasterio.open(src_ds)
        src_ds_ptr = (<DatasetReaderBase?> src_rio).handle()
        if src_ds_ptr == NULL:
            raise RuntimeError('Dataset is NULL')
    if isinstance(src_ds, DatasetReaderBase):
        src_rio = src_ds
        src_ds_ptr = (<DatasetReaderBase?> src_rio).handle()
        if src_ds_ptr == NULL:
            raise RuntimeError('Dataset is NULL')
    dst_ds_bytes = dst_ds.encode('utf-8')
    cdef char* dst_ds_enc = dst_ds_bytes


    cdef int pbUsageError = <int> 0
    cdef GDALDatasetH dst_hds = NULL
    cdef GDALTranslateOptions* gdal_translate_options = create_translate_options(bands, input_format, output_format)
    with nogil:
        try:
            dst_hds = GDALTranslate(dst_ds_enc, src_ds_ptr, gdal_translate_options, &pbUsageError)
            if dst_hds == NULL:
                raise RuntimeError('Destination dataset is null!')
        finally:
            GDALTranslateOptionsFree(gdal_translate_options)
            GDALClose(dst_hds)
    src_rio.close()
    return dst_ds
