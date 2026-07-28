import os

import rasterio

include "rasterio/gdal.pxi"

from rasterio._io cimport DatasetReaderBase
from rasterio.head_on._warp cimport GDALWarpAppOptions, GDALWarpAppOptionsFree, GDALWarp, GDALWarpAppOptionsNew


cdef GDALWarpAppOptions* create_warp_app_options(output_crs=None,
                                                 warp_memory_limit=None,
                                                 multi=None,
                                                 multi_threads=os.cpu_count(),
                                                 cutline_fn=None,
                                                 cutline_layer=None,
                                                 crop_to_cutline=None,
                                                 input_format=None,
                                                 output_format=None,
                                                 overwrite=None,
                                                 src_nodata=None,
                                                 dst_nodata=None,
                                                 set_source_color_interp=None,
                                                 resampling=None,
                                                 write_flush=None):
    options = []
    if output_crs:
        options += ['-t_srs', str(output_crs)]
    if input_format:
        options += ['-if', str(input_format)]
    if output_format:
        options += ['-of', str(output_format)]
    if warp_memory_limit:
        options += ['-wm', str(warp_memory_limit)]
    if write_flush:
        options += ['-wo', 'WRITE_FLUSH=YES']
    if multi:
        options += ['-multi']
        if multi_threads:
            options += ['-wo', f'NUM_THREADS={multi_threads}']
    if cutline_fn:
        options += ['-cutline', str(cutline_fn)]
        if crop_to_cutline:
            options += ['-crop_to_cutline']
        if cutline_layer:
            options += ['-cl', str(cutline_layer)]
    if overwrite:
        options += ['-overwrite']
    if src_nodata:
        options += ['-srcnodata', str(src_nodata)]
    if dst_nodata:
        options += ['-dstnodata', str(dst_nodata)]
    if set_source_color_interp:
        options += ['-setci']
    if resampling:
        options += ['-r', str(resampling)]

    enc_str_options = " ".join(options).encode('utf-8')
    cdef char** enc_str_options_ptr = CSLParseCommandLine(enc_str_options)

    cdef GDALWarpAppOptions* warp_app_options = NULL
    warp_app_options = GDALWarpAppOptionsNew(enc_str_options_ptr, NULL)
    return warp_app_options


cpdef warp(src_ds,
           dst_ds,
           output_crs=None,
           warp_memory_limit=None,
           multi=None,
           multi_threads=os.cpu_count(),
           cutline_fn=None,
           cutline_layer=None,
           crop_to_cutline=None,
           input_format=None,
           output_format=None,
           overwrite=None,
           src_nodata=None,
           dst_nodata=None,
           set_source_color_interp=None,
           resampling=None,
           write_flush=None):

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

    cdef GDALDatasetH *src_ds_ptr_list = NULL
    src_ds_ptr_list = <GDALDatasetH *> CPLMalloc(1 * sizeof(GDALDatasetH))
    src_ds_ptr_list[0] = src_ds_ptr

    cdef int pbUsageError = <int> 0
    cdef int src_count = <int> 1

    cdef GDALDatasetH dst_hds = NULL
    cdef GDALWarpAppOptions *warp_app_options = NULL
    warp_app_options = create_warp_app_options(
                                                                        output_crs,
                                                                        warp_memory_limit,
                                                                        multi,
                                                                        multi_threads,
                                                                        cutline_fn,
                                                                        cutline_layer,
                                                                        crop_to_cutline,
                                                                        input_format,
                                                                        output_format,
                                                                        overwrite,
                                                                        write_flush)
    try:
        dst_hds = GDALWarp(dst_ds_enc, NULL, src_count, src_ds_ptr_list, warp_app_options, &pbUsageError)
        if dst_hds == NULL:
            raise RuntimeError('Destination dataset is null!')
    finally:
        GDALClose(dst_hds)
        CPLFree(src_ds_ptr_list)
        GDALWarpAppOptionsFree(warp_app_options)
    src_rio.close()
    return dst_ds