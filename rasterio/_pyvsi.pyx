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

from libc.stdio cimport FILE

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


cdef extern from "_pyvsi_handle.h" namespace "pyvsi_handle":
    VSILFILE *CreatePyVSIInMem(const char *pszFilename, PythonVSIVirtualHandle *handle)

    cdef cppclass PythonVSIVirtualHandle:
        PythonVSIVirtualHandle(cpy_ref.PyObject *obj)
        int Seek(vsi_l_offset nOffset, int nWhence)
        vsi_l_offset Tell()
        size_t Read(void *pBuffer, size_t nSize, size_t nCount)
        int ReadMultiRange(int nRanges, void **ppData,
                           const vsi_l_offset* panOffsets,
                           const size_t* panSizes)
        size_t Write(const void *pBuffer, size_t nSize, size_t nCount)
        int Eof()
        int Flush()
        int Close()
        int Truncate(vsi_l_offset nNewSize)
        void *GetNativeFileDescriptor()
        # VSIRangeStatus GetRangeStatus(vsi_l_offset nOffset, vsi_l_offset nLength)


cdef class PyVSIFileBase:

    cdef PythonVSIVirtualHandle* _vsif

    def __cinit__(self, file_or_bytes, *args, **kwargs):
        self._vsif = new PythonVSIVirtualHandle(<cpy_ref.PyObject*>self)
        # self._vsif = new PythonVSIVirtualHandle(<cpy_ref.PyObject*>file_or_bytes)

    def __dealloc__(self):
        if self._vsif:
            del self._vsif

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
        vsifile_handle = CreatePyVSIInMem(self._path, self._vsif)
        print("VSIFile handle: ", vsifile_handle == NULL)
        self._file_obj = file_or_bytes
        self.mode = "r"

        # else:
        #     self._vsif = VSIFOpenL(self._path, "w+")
        #     self.mode = "w+"

        # if self._vsif == NULL:
        #     raise IOError("Failed to open in-memory file.")

        self.closed = False

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
        print("seek: ", offset, whence)
        return VSIFSeekL(<VSILFILE *>self._vsif, offset, whence)

    def tell(self):
        print("tell:", self._vsif != NULL)
        if self._vsif != NULL:
            return VSIFTellL(<VSILFILE *>self._vsif)
        else:
            return 0

    def read(self, size=-1):
        """Read size bytes from MemoryFile."""
        print("tell:", size)
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
        print("write")
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
