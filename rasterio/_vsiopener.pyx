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
cdef str PREFIX = "/vsipyopener/"
cdef bytes PREFIX_BYTES = PREFIX.encode("utf-8")

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

    if VSIFileManager.GetHandler("") == VSIFileManager.GetHandler(PREFIX_BYTES):
        log.debug("Installing Python opener handler plugin...")
        return VSIInstallPluginHandler(PREFIX_BYTES, callbacks_struct)
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
    if pszAccess != b"r" and pszAccess != b"rb":
        log.error("Python opener is currently a read-only interface.")
        return NULL

    if pUserData is NULL:
        log.error("Python opener registry is not initialized.")
        return NULL

    cdef dict registry = <object>pUserData
    filename = pszFilename.decode("utf-8")

    log.debug("Looking up opener: registry=%r, filename=%r", registry, filename)
    try:
        file_opener = registry[filename]
    except KeyError:
        log.info("Object not found: registry=%r, filename=%r", registry, filename)
        return NULL

    cdef object file_obj

    try:
        file_obj = file_opener(filename, "rb")
    except ValueError:
        file_obj = file_opener(filename)

    if hasattr(file_obj, "open"):
        file_obj = file_obj.open()

    log.debug("Opened file object: file_obj=%r", file_obj)
    _OPEN_FILE_OBJS.add(file_obj)
    return <void *>file_obj


cdef vsi_l_offset pyopener_tell(void *pFile) except -1 with gil:
    cdef object file_obj = <object>pFile
    cdef long pos = file_obj.tell()
    return <vsi_l_offset>pos


cdef int pyopener_seek(void *pFile, vsi_l_offset nOffset, int nWhence) except -1 with gil:
    cdef object file_obj = <object>pFile
    # TODO: Add "seekable" check?
    file_obj.seek(nOffset, nWhence)
    return 0


cdef size_t pyopener_read(void *pFile, void *pBuffer, size_t nSize, size_t nCount) except -1 with gil:
    cdef object file_obj = <object>pFile
    cdef bytes python_data = file_obj.read(nSize * nCount)
    cdef int num_bytes = len(python_data)
    # NOTE: We have to cast to char* first, otherwise Cython doesn't do the conversion properly
    memcpy(pBuffer, <void*><char*>python_data, num_bytes)
    return <size_t>(num_bytes / nSize)


cdef int pyopener_close(void *pFile) except -1 with gil:
    cdef object file_obj = <object>pFile
    log.debug("Closing: file_obj=%r", file_obj)
    try:
        file_obj.close()
    except AttributeError:
        log.exception()
        pass
    except Exception:
        log.exception()
        raise

    _OPEN_FILE_OBJS.remove(file_obj)
    return 0


@contextlib.contextmanager
def _opener_registration(urlpath, opener):
    filename = urlpath
    _OPENER_REGISTRY[filename] = opener
    try:
        yield f"{PREFIX}{filename}"
    finally:
        _ = _OPENER_REGISTRY.pop(filename)

