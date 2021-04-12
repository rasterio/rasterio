# cython: language_level=3, boundscheck=False
"""Bridge between Python file-like objects and GDAL VSI."""

include "gdal.pxi"

from collections import Counter
from contextlib import contextmanager
import logging
import os
import sys
from uuid import uuid4
import warnings

import numpy as np

from rasterio._base import tastes_like_gdal, gdal_version
from rasterio._base cimport open_dataset
from rasterio._err import (
    GDALError, CPLE_OpenFailedError, CPLE_IllegalArgError, CPLE_BaseError, CPLE_AWSObjectNotFoundError)
from rasterio.crs import CRS
from rasterio import dtypes
from rasterio.enums import ColorInterp, MaskFlags, Resampling
from rasterio.errors import (
    CRSError, DriverRegistrationError, RasterioIOError,
    NotGeoreferencedWarning, NodataShadowWarning, WindowError,
    UnsupportedOperation, OverviewCreationError, RasterBlockError, InvalidArrayError
)
from rasterio.dtypes import is_ndarray
from rasterio.sample import sample_gen
from rasterio.transform import Affine
from rasterio.path import parse_path, UnparsedPath
from rasterio.vrt import _boundless_vrt_doc
from rasterio.windows import Window, intersection

from libc.stdio cimport printf
from libc.string cimport memcpy

from rasterio import dtypes
from rasterio.enums import Resampling
from rasterio.env import GDALVersion
from rasterio.errors import ResamplingAlgorithmError
from rasterio._base cimport (
_osr_from_crs, _safe_osr_release, get_driver_name, DatasetBase)
from rasterio._err cimport exc_wrap_int, exc_wrap_pointer, exc_wrap_vsilfile

cimport numpy as np
cimport cpython.ref as cpy_ref

log = logging.getLogger(__name__)

gdal33_version_checked = False
gdal33_version_met = False


def _delete_dataset_if_exists(path):

    """Delete a dataset if it already exists.  This operates at a lower
    level than a:

        if rasterio.shutil.exists(path):
            rasterio.shutil.delete(path)

    and can take some shortcuts.

    Parameters
    ----------
    path : str
        Dataset path.
    """

    cdef GDALDatasetH h_dataset = NULL
    cdef GDALDriverH h_driver = NULL
    cdef const char *path_c = NULL

    try:
        h_dataset = open_dataset(path, 0x40, None, None, None)
    except (CPLE_OpenFailedError, CPLE_AWSObjectNotFoundError) as exc:
        log.debug(
            "Skipped delete for overwrite. Dataset does not exist: %r", path)
    else:
        h_driver = GDALGetDatasetDriver(h_dataset)
        GDALClose(h_dataset)
        h_dataset = NULL

        if h_driver != NULL:
            path_b = path.encode("utf-8")
            path_c = path_b
            with nogil:
                err = GDALDeleteDataset(h_driver, path_c)
            exc_wrap_int(err)
    finally:
        if h_dataset != NULL:
            GDALClose(h_dataset)

## Filesystem Functions

cdef int pyvsi_stat(void *pUserData, const char *pszFilename, VSIStatBufL *pStatBuf, int nFlags) with gil:
    # Optional
    printf("stat\n")


cdef int unlink(void *pUserData, const char *pszFilename) with gil:
    # Optional
    printf("unlink\n")


cdef int rename(void *pUserData, const char *oldpath, const char *newpath) with gil:
    # Optional
    printf("rename\n")


cdef int mkdir(void *pUserData, const char *pszDirname, long nMode) with gil:
    # Optional
    printf("mkdir\n")


cdef int rmdir(void *pUserData, const char *pszDirname) with gil:
    # Optional
    printf("rmdir\n")


cdef char** read_dir(void *pUserData, const char *pszDirname, int nMaxFiles) with gil:
    # Optional
    printf("read_dir\n")


cdef char** siblings_files(void *pUserData, const char *pszDirname) with gil:
    # Optional (GDAL 3.2+)
    printf("siblings_files\n")


cdef void* open(void *pUserData, const char *pszDirname, const char *pszAccess) with gil:
    # Mandatory
    print("open")
    if pUserData is NULL:
        print("User data is NULL")
    else:
        print("User data is not NULL")
        #file_wrapper = <object>pUserData
        #print(file_wrapper._file_obj)
    return <void *>pUserData

## File functions


cdef vsi_l_offset tell(void *pFile) with gil:
    print("tell")
    cdef object file_wrapper = <object>pFile
    cdef object file_obj = file_wrapper._file_obj
    pos = file_obj.tell()
    return <vsi_l_offset>pos


cdef int seek(void *pFile, vsi_l_offset nOffset, int nWhence) except -1 with gil:
    print("seek")
    cdef object file_wrapper = <object>pFile
    cdef object file_obj = file_wrapper._file_obj
    # TODO: Add "seekable" check?
    file_obj.seek(nOffset, nWhence)
    return 0


cdef size_t read(void *pFile, void *pBuffer, size_t nSize, size_t nCount) with gil:
    print("read")
    cdef object file_wrapper = <object>pFile
    cdef object file_obj = file_wrapper._file_obj
    cdef bytes python_data = file_obj.read(nSize * nCount)
    cdef int num_bytes = len(python_data)
    # NOTE: We have to cast to char* first, otherwise Cython doesn't do the conversion properly
    memcpy(pBuffer, <void*><char*>python_data, num_bytes)
    return <size_t>(num_bytes / nSize)


cdef int read_multi_range(void *pFile, int, void **ppData, const vsi_l_offset *panOffsets, const size_t *panSizes) with gil:
    # Optional
    print("read_multi_range")


cdef VSIRangeStatus get_range_status(void *pFile, vsi_l_offset nOffset, vsi_l_offset nLength) with gil:
    # Optional
    print("get_range_status")


cdef int eof(void *pFile) with gil:
    # Mandatory?
    print("eof")


cdef size_t write(void *pFile, const void *pBuffer, size_t nSize, size_t nCount) with gil:
    print("write")


cdef int flash(void *pFile) with gil:
    # Optional
    print("flash")


cdef int truncate(void *pFile, vsi_l_offset nNewSize) with gil:
    print("truncate")


cdef int close(void *pFile) except -1 with gil:
    # Optional
    print("close")
    # XXX: We probably shouldn't close the file object for the user
    return 0


cdef int install_rasterio_pyvsi_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct):
    # TODO:
    cdef int install_status = VSIInstallPluginHandler("/vsipythonfilelike/", callbacks_struct)
    return install_status


cdef class PyVSIFileBase:

    cdef VSIFilesystemPluginCallbacksStruct* _vsif

    def __cinit__(self, file_or_bytes, *args, **kwargs):
        self._vsif = VSIAllocFilesystemPluginCallbacksStruct()
        # XXX: Should we inc ref?
        # self._vsif.pUserData = NULL
        self._vsif.pUserData = <void*>self
        self._vsif.open = <VSIFilesystemPluginOpenCallback>open

        self._vsif.tell = <VSIFilesystemPluginTellCallback>tell
        self._vsif.seek = <VSIFilesystemPluginSeekCallback>seek
        self._vsif.read = <VSIFilesystemPluginReadCallback>read
        self._vsif.read_multi_range = <VSIFilesystemPluginReadMultiRangeCallback>read_multi_range
        self._vsif.eof = <VSIFilesystemPluginEofCallback>eof
        self._vsif.close = <VSIFilesystemPluginCloseCallback>close

    def __dealloc__(self):
        if self._vsif is not NULL:
            self._vsif.pUserData = NULL
            VSIFreeFilesystemPluginCallbacksStruct(self._vsif)
            self._vsif = NULL

    def __init__(self, file_or_bytes=None, dirname=None, filename=None, ext='.tif'):
        """A file in an in-memory filesystem.

        Parameters
        ----------
        file_or_bytes : file or bytes
            A file opened in binary mode or bytes
        filename : str
            A filename for the in-memory file under /vsimem
        ext : str
            A file extension for the in-memory file under /vsimem. Ignored if
            filename was provided.

        """
        # if file_or_bytes:
        #     if hasattr(file_or_bytes, 'read'):
        #         initial_bytes = file_or_bytes.read()
        #     elif isinstance(file_or_bytes, bytes):
        #         initial_bytes = file_or_bytes
        #     else:
        #         raise TypeError(
        #             "Constructor argument must be a file opened in binary "
        #             "mode or bytes.")
        # else:
        #     initial_bytes = b''

        # Make an in-memory directory specific to this dataset to help organize
        # auxiliary files.
        self._dirname = dirname or str(uuid4())
        # VSIMkdir("/vsimem/{0}".format(self._dirname).encode("utf-8"), 0666)

        if filename:
            # GDAL's SRTMHGT driver requires the filename to be "correct" (match
            # the bounds being written)
            self.name = "/vsipythonfilelike/{0}/{1}".format(self._dirname, filename)
        else:
            # GDAL 2.1 requires a .zip extension for zipped files.
            self.name = "/vsipythonfilelike/{0}/{0}.{1}".format(self._dirname, ext.lstrip('.'))

        self._path = self.name.encode('utf-8')

        # self._initial_bytes = initial_bytes
        # cdef unsigned char *buffer = self._initial_bytes

        # self._vsif = VSIFileFromMemBuffer(
        #     self._path, buffer, len(self._initial_bytes), 0)
        # self._vsif = PythonVSIVirtualHandleWrapper(<cpy_ref.PyObject*>file_or_bytes)
        # vsifile_handle = CreatePyVSIInMem(self._path, self._vsif)
        # print("VSIFile handle: ", vsifile_handle == NULL)
        self._file_obj = file_or_bytes
        self.mode = "r"

        # else:
        #     self._vsif = VSIFOpenL(self._path, "w+")
        #     self.mode = "w+"

        # if self._vsif == NULL:
        #     raise IOError("Failed to open in-memory file.")

        self.closed = False

        # TODO: Error checking
        install_rasterio_pyvsi_plugin(self._vsif)

    def exists(self):
        """Test if the in-memory file exists.

        Returns
        -------
        bool
            True if the in-memory file exists.

        """
        print("exists")
        cdef VSIStatBufL st_buf
        return VSIStatL(self._path, &st_buf) == 0

    def __len__(self):
        """Length of the file's buffer in number of bytes.

        Returns
        -------
        int
        """
        print("__len__")
        try:
            return self._file_obj.size
        except AttributeError:
            # FIXME: What should this actually do?
            return 0
        # return self.getbuffer().size

    # def getbuffer(self):
    #     """Return a view on bytes of the file."""
    #     print("getbuffer")
    #     cdef unsigned char *buffer = NULL
    #     cdef vsi_l_offset buffer_len = 0
    #     cdef np.uint8_t [:] buff_view
    #
    #     buffer = VSIGetMemFileBuffer(self._path, &buffer_len, 0)
    #
    #     if buffer == NULL or buffer_len == 0:
    #         buff_view = np.array([], dtype='uint8')
    #     else:
    #         buff_view = <np.uint8_t[:buffer_len]>buffer
    #     return buff_view

    def close(self):
        print("Python close")
        if hasattr(self, '_vsif') and self._vsif is not NULL:
            print("vsif is not Null")
            VSIFCloseL(<VSILFILE *>self._vsif)
        self._vsif = NULL
        # _delete_dataset_if_exists(self.name)
        # VSIRmdir(self._dirname.encode("utf-8"))
        self.closed = True

    def seek(self, offset, whence=0):
        print("python seek: ", offset, whence)
        return VSIFSeekL(<VSILFILE *>self._vsif, offset, whence)

    def tell(self):
        print("python tell:", self._vsif != NULL)
        if self._vsif != NULL:
            return VSIFTellL(<VSILFILE *>self._vsif)
        else:
            return 0

    def read(self, size=-1):
        """Read size bytes from MemoryFile."""
        print("python read:", size)
        cdef bytes result
        cdef unsigned char *buffer = NULL
        cdef vsi_l_offset buffer_len = 0

        if size < 0:
            buffer = VSIGetMemFileBuffer(self._path, &buffer_len, 0)
            size = buffer_len

        buffer = <unsigned char *>CPLMalloc(size)

        try:
            objects_read = VSIFReadL(buffer, 1, size, <VSILFILE *>self._vsif)
            result = <bytes>buffer[:objects_read]

        finally:
            CPLFree(buffer)

        return result

    def write(self, data):
        """Write data bytes to MemoryFile"""
        print("python write")
        cdef const unsigned char *view = <bytes>data
        n = len(data)
        result = VSIFWriteL(view, 1, n, <VSILFILE *>self._vsif)
        VSIFFlushL(<VSILFILE *>self._vsif)
        return result

cdef public api void cy_call_print(object self):
    try:
        print(self)
    except Exception:
        print("ERROR")
