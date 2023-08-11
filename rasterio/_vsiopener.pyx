# cython: language_level=3, boundscheck=False
# distutils: language = c++
"""Bridge between Python file openers and GDAL VSI.

Based on _filepath.pyx.
"""

include "gdal.pxi"

import contextlib
import logging
from uuid import uuid4

from libc.string cimport memcpy

log = logging.getLogger(__name__)

gdal33_version_checked = False
gdal33_version_met = False


# NOTE: This has to be defined outside of gdal.pxi or other C extensions will
# try to compile C++ only code included in this header.
cdef extern from "cpl_vsi_virtual.h":
    cdef cppclass VSIFileManager:
        @staticmethod
        void* GetHandler(const char*)


# Prefix for all in-memory paths used by GDAL's VSI system
# Except for errors and log messages this shouldn't really be seen by the user
cdef str FILESYSTEM_PREFIX = "/vsipyopener/"
cdef bytes FILESYSTEM_PREFIX_BYTES = FILESYSTEM_PREFIX.encode("ascii")

# This is global state for the Python filesystem plugin. It currently only
# contains path -> PyOpenerBase (or subclass) instances. This is used by
# the plugin to determine what "files" exist on "disk".
# Currently the only way to "create" a file in the filesystem is to add
# an entry to this dictionary. GDAL will then Open the path later.
cdef _OPENER_REGISTRY = {}
cdef _OPEN_FILE_OBJS = set()


cdef int install_pyopener_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct):
    """Install handlers for python file openers if it isn't already installed."""
    callbacks_struct = VSIAllocFilesystemPluginCallbacksStruct()
    callbacks_struct.open = <VSIFilesystemPluginOpenCallback>pyopener_open
    callbacks_struct.tell = <VSIFilesystemPluginTellCallback>pyopener_tell
    callbacks_struct.seek = <VSIFilesystemPluginSeekCallback>pyopener_seek
    callbacks_struct.read = <VSIFilesystemPluginReadCallback>pyopener_read
    callbacks_struct.close = <VSIFilesystemPluginCloseCallback>pyopener_close
    callbacks_struct.pUserData = <void*>_OPENER_REGISTRY

    if VSIFileManager.GetHandler("") == VSIFileManager.GetHandler(FILESYSTEM_PREFIX_BYTES):
        log.debug("Installing PyOpener filesystem handler plugin...")
        return VSIInstallPluginHandler(FILESYSTEM_PREFIX_BYTES, callbacks_struct)
    else:
        return 0


cdef void uninstall_pyopener_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct):
    if callbacks_struct is not NULL:
        callbacks_struct.pUserData = NULL
        VSIFreeFilesystemPluginCallbacksStruct(callbacks_struct)
    callbacks_struct = NULL


cdef void* pyopener_open(void *pUserData, const char *pszFilename, const char *pszAccess) with gil:
    """Access files in the virtual filesystem.

    This function is mandatory in the GDAL Filesystem Plugin API.
    GDAL may call this function multiple times per filename and each
    result must be seperately seekable.
    """
    cdef object file_opener
    cdef object file_obj

    if pszAccess != b"r" and pszAccess != b"rb":
        log.error("PyOpener is currently a read-only interface.")
        return NULL

    if pUserData is NULL:
        log.error("PyOpener filesystem accessed with uninitialized filesystem info.")
        return NULL

    cdef dict filesystem_info = <object>pUserData

    try:
        file_opener = filesystem_info[pszFilename]
    except KeyError:
        log.info("Object not found in virtual filesystem: filename=%r", pszFilename)
        return NULL

    # Extract the opener's argument from the vsi filename.
    path = pszFilename
    if path.startswith(FILESYSTEM_PREFIX_BYTES):
        path = path[len(FILESYSTEM_PREFIX_BYTES):]

    file_obj = file_opener(path, "rb")
    return <void *>file_obj

    # Open file wrappers are kept in this set and removed when closed.
    # _OPEN_FILE_OBJS.add(file_obj)


cdef vsi_l_offset pyopener_tell(void *pFile) with gil:
    cdef object file_obj = <object>pFile
    cdef long pos = file_obj.tell()
    return <vsi_l_offset>pos


cdef int pyopener_seek(void *pFile, vsi_l_offset nOffset, int nWhence) except -1 with gil:
    cdef object file_obj = <object>pFile
    # TODO: Add "seekable" check?
    file_obj.seek(nOffset, nWhence)
    return 0


cdef size_t pyopener_read(void *pFile, void *pBuffer, size_t nSize, size_t nCount) with gil:
    cdef object file_obj = <object>pFile
    cdef bytes python_data = file_obj.read(nSize * nCount)
    cdef int num_bytes = len(python_data)
    # NOTE: We have to cast to char* first, otherwise Cython doesn't do the conversion properly
    memcpy(pBuffer, <void*><char*>python_data, num_bytes)
    return <size_t>(num_bytes / nSize)


cdef int pyopener_close(void *pFile) except -1 with gil:
    cdef object file_obj = <object>pFile
    try:
        file_obj.close()
    except AttributeError:
        pass

    # _OPEN_FILE_OBJS.remove(file_obj)
    return 0


@contextlib.contextmanager
def _opener_registration(urlpath, opener):
    _OPENER_REGISTRY[urlpath] = opener
    try:
        yield opener
    finally:
        _ = _OPENER_REGISTRY.pop(urlpath)

