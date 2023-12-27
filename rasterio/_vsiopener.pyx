# cython: language_level=3, boundscheck=False
# distutils: language = c++
"""Bridge between Python file openers and GDAL VSI.

Based on _filepath.pyx.
"""

include "gdal.pxi"

import contextlib
from contextvars import ContextVar
import logging
from uuid import uuid4

from libc.string cimport memcpy
cimport numpy as np

from rasterio.errors import OpenerRegistrationError

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
_OPENER_REGISTRY = ContextVar("opener_registery")
_OPENER_REGISTRY.set({})
_OPEN_FILE_EXIT_STACKS = ContextVar("open_file_exit_stacks")
_OPEN_FILE_EXIT_STACKS.set({})


cdef int install_pyopener_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct):
    """Install handlers for python file openers if it isn't already installed."""
    cdef char **registered_prefixes = VSIGetFileSystemsPrefixes()
    cdef int prefix_index = CSLFindString(registered_prefixes, PREFIX_BYTES)
    CSLDestroy(registered_prefixes)

    if prefix_index < 0:
        log.debug("Installing Python opener handler plugin...")
        callbacks_struct = VSIAllocFilesystemPluginCallbacksStruct()
        callbacks_struct.open = <VSIFilesystemPluginOpenCallback>pyopener_open
        callbacks_struct.tell = <VSIFilesystemPluginTellCallback>pyopener_tell
        callbacks_struct.seek = <VSIFilesystemPluginSeekCallback>pyopener_seek
        callbacks_struct.read = <VSIFilesystemPluginReadCallback>pyopener_read
        callbacks_struct.write = <VSIFilesystemPluginWriteCallback>pyopener_write
        callbacks_struct.close = <VSIFilesystemPluginCloseCallback>pyopener_close
        callbacks_struct.pUserData = <void*>_OPENER_REGISTRY
        retval = VSIInstallPluginHandler(PREFIX_BYTES, callbacks_struct)
        VSIFreeFilesystemPluginCallbacksStruct(callbacks_struct)
        return retval
    else:
        return 0


cdef void uninstall_pyopener_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct):
    if callbacks_struct is not NULL:
        callbacks_struct.pUserData = NULL
        VSIFreeFilesystemPluginCallbacksStruct(callbacks_struct)
    callbacks_struct = NULL


cdef void* pyopener_open(void *pUserData, const char *pszFilename, const char *pszAccess) except NULL with gil:
    """Access files in the virtual filesystem.

    This function is mandatory in the GDAL Filesystem Plugin API.
    GDAL may call this function multiple times per filename and each
    result must be seperately seekable.
    """
    if pUserData is NULL:
        CPLError(CE_Failure, <CPLErrorNum>1, <const char *>"%s", <const char *>"Python opener is not initialized.")
        return NULL

    cdef object var = <object>pUserData
    cdef dict registry = var.get()
    urlpath = pszFilename.decode("utf-8")
    mode = pszAccess.decode("utf-8")
    log.debug("Looking up opener: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)
    # Note: the opener is added to the registry in rasterio.open().

    try:
        file_opener = registry[(urlpath, mode[0])]
    except KeyError as err:
        # GDAL is eager to discover auxiliary files and this error will
        # occur often. The Python opener plugin does not support
        # auxiliary files.
        log.debug("Opener not found in registry: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)
        return NULL

    cdef object file_obj

    try:
        file_obj = file_opener(urlpath, mode)
    except ValueError as err:
        # ZipFile.open doesn't accept binary modes like "rb" and will
        # raise ValueError if given one. We strip the mode in this case.
        file_obj = file_opener(urlpath, mode.rstrip("b"))
    except Exception as err:
        errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
        errmsg_b = errmsg.encode("utf-8")
        # 4 is CPLE_OpenFailedError.
        CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
        return NULL

    log.debug("Opened file object: file_obj=%r, mode=%r", file_obj, mode)

    # Before we return, we attempt to enter the file object's context
    # and store an exit callback stack for it.
    stack = contextlib.ExitStack()

    try:
        file_obj = stack.enter_context(file_obj)
    except (AttributeError, TypeError):
        log.debug("File object is not a context manager: file_obj=%r", file_obj)

    exit_stacks = _OPEN_FILE_EXIT_STACKS.get()
    exit_stacks[file_obj] = stack
    _OPEN_FILE_EXIT_STACKS.set(exit_stacks)
    return <void *>file_obj


cdef vsi_l_offset pyopener_tell(void *pFile) except -1 with gil:
    cdef object file_obj = <object>pFile
    return <vsi_l_offset>file_obj.tell()


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


cdef size_t pyopener_write(void *pFile, void *pBuffer, size_t nSize, size_t nCount) except -1 with gil:
    cdef object file_obj = <object>pFile
    buffer_len = nSize * nCount
    cdef np.uint8_t [:] buff_view = <np.uint8_t[:buffer_len]>pBuffer
    log.debug("Writing data: buff_view=%r", buff_view)
    return <size_t>file_obj.write(buff_view)


cdef int pyopener_close(void *pFile) except -1 with gil:
    cdef object file_obj = <object>pFile
    log.debug("Closing: file_obj=%r", file_obj)
    exit_stacks = _OPEN_FILE_EXIT_STACKS.get()
    stack = exit_stacks.pop(file_obj)
    stack.close()
    _OPEN_FILE_EXIT_STACKS.set(exit_stacks)
    return 0


@contextlib.contextmanager
def _opener_registration(urlpath, mode, opener):
    registry = _OPENER_REGISTRY.get()
    if (urlpath, mode) in registry:
        if registry[(urlpath, mode)] != opener:
            raise OpenerRegistrationError(f"Opener already registered for urlpath and mode")
        else:
            try:
                yield f"{PREFIX}{urlpath}"
            finally:
                registry = _OPENER_REGISTRY.get()
                _ = registry.pop((urlpath, mode), None)
                _OPENER_REGISTRY.set(registry)
    else:
        registry[(urlpath, mode)] = opener
        _OPENER_REGISTRY.set(registry)
        try:
            yield f"{PREFIX}{urlpath}"
        finally:
            registry = _OPENER_REGISTRY.get()
            _ = registry.pop((urlpath, mode), None)
            _OPENER_REGISTRY.set(registry)
