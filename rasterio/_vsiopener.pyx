# cython: language_level=3, boundscheck=False
# distutils: language = c++
"""Bridge between Python file openers and GDAL VSI.

Based on _filepath.pyx.
"""

include "gdal.pxi"

import contextlib
from contextvars import ContextVar
import logging
import os
from pathlib import Path
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
        callbacks_struct.read_dir = <VSIFilesystemPluginReadDirCallback>pyopener_read_dir
        callbacks_struct.stat = <VSIFilesystemPluginStatCallback>pyopener_stat
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


cdef int pyopener_stat(void *pUserData, const char *pszFilename, VSIStatBufL *pStatBuf, int nFlags) except -1 with gil:
    if pUserData is NULL:
        CPLError(CE_Failure, <CPLErrorNum>1, <const char *>"%s", <const char *>"Python opener is not initialized.")
        return -1

    cdef object var = <object>pUserData
    cdef dict registry = var.get()
    urlpath = pszFilename.decode("utf-8")
    # The code below is just a test that we can assemble an st_mode
    # value for GDAL from Python filesystem is_file and is_dir methods.
    # Eventually we're going to dispatch to methods of the opener that
    # was registered for the filename.
    import stat
    try:
        from urllib.parse import urlparse
        parsed_uri = urlparse(urlpath)
        path_to_check = Path(parsed_uri.path)
        parent = path_to_check.parent
        # Note that "r" mode is used here under the assumption that GDAL
        # doesn't read_dir when writing data. Could be wrong!
        mode = "rb"
        key = ((parsed_uri.scheme, parsed_uri.netloc, parent.as_posix()), mode[0])
        log.debug("Looking up opener in stat: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)

        try:
            file_opener = registry[key]
        except KeyError as err:
            log.debug("Opener not found in registry: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)
            errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
            errmsg_b = errmsg.encode("utf-8")
            # 4 is CPLE_OpenFailedError.
            CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
            return -1

        size = file_opener.size(urlpath)
        if file_opener.is_file(urlpath):
            fmode = 0o170000 | stat.S_IFREG
        elif file_opener.is_dir(urlpath):
            fmode = 0o170000 | stat.S_IFDIR
        else:
            fmode = 0
    except Exception as err:
        errmsg = f"Opener failed to determine file info: {repr(err)}"
        errmsg_b = errmsg.encode("utf-8")
        # 4 is CPLE_OpenFailedError.
        CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
        return -1
    else:
        pStatBuf.st_size = size
        pStatBuf.st_mode = fmode
    return 0


cdef char ** pyopener_read_dir(void *pUserData, const char *pszDirname, int nMaxFiles) except NULL with gil:
    """Return directory listing."""
    if pUserData is NULL:
        CPLError(CE_Failure, <CPLErrorNum>1, <const char *>"%s", <const char *>"Python opener is not initialized.")
        return NULL

    cdef object var = <object>pUserData
    cdef dict registry = var.get()
    urlpath = pszDirname.decode("utf-8")
    mode = "rb"
    log.debug("Looking up opener in read_dir: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)

    from urllib.parse import urlparse
    parsed_uri = urlparse(urlpath)
    # Note that "r" mode is used here under the assumption that GDAL
    # doesn't read_dir when writing data. Could be wrong!
    key = ((parsed_uri.scheme, parsed_uri.netloc, parsed_uri.path), mode[0])

    try:
        file_opener = registry[key]
    except KeyError as err:
        log.debug("Opener not found in registry: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)
        errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
        errmsg_b = errmsg.encode("utf-8")
        # 4 is CPLE_OpenFailedError.
        CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
        return NULL

    # GDAL wants relative file names.
    contents = [Path(item).name for item in file_opener.ls(urlpath)]
    log.debug("Looking for dir contents: urlpath=%r, contents=%r", urlpath, contents)
    cdef char **name_list = NULL

    for name in contents:
        sib = name.encode("utf-8")
        CSLAddString(name_list, <char *>sib)
    return name_list


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
    log.debug("Looking up opener in open: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)
    # Note: the opener is added to the registry in rasterio.open().

    from urllib.parse import urlparse
    parsed_uri = urlparse(urlpath)
    path_to_check = Path(parsed_uri.path)
    parent = path_to_check.parent
    key = ((parsed_uri.scheme, parsed_uri.netloc, parent.as_posix()), mode[0])

    try:
        file_opener = registry[key]
    except KeyError as err:
        log.debug("Opener not found in registry: registry=%r, urlpath=%r, mode=%r", registry, urlpath, mode)
        errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
        errmsg_b = errmsg.encode("utf-8")
        # 4 is CPLE_OpenFailedError.
        CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
        return NULL

    cdef object file_obj

    try:
        file_obj = file_opener.open(urlpath, mode)
    except ValueError as err:
        # ZipFile.open doesn't accept binary modes like "rb" and will
        # raise ValueError if given one. We strip the mode in this case.
        try:
            file_obj = file_opener.open(urlpath, mode.rstrip("b"))
        except Exception as err:
            errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
            errmsg_b = errmsg.encode("utf-8")
            # 4 is CPLE_OpenFailedError.
            CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
            return NULL
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
    except (AttributeError, TypeError) as err:
        log.error("File object is not a context manager: file_obj=%r", file_obj)
        errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
        errmsg_b = errmsg.encode("utf-8")
        # 4 is CPLE_OpenFailedError.
        CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
        return NULL
    except FileNotFoundError as err:
        log.info("OpenFile doesn't resolve: file_obj=%r", file_obj)
        errmsg = f"Opener failed to open file with arguments ({repr(urlpath)}, {repr(mode)}): {repr(err)}"
        errmsg_b = errmsg.encode("utf-8")
        # 4 is CPLE_OpenFailedError.
        CPLError(CE_Failure, <CPLErrorNum>4, <const char *>"%s", <const char *>errmsg_b)
        return NULL
    else:
        exit_stacks = _OPEN_FILE_EXIT_STACKS.get()
        exit_stacks[file_obj] = stack
        _OPEN_FILE_EXIT_STACKS.set(exit_stacks)
        log.debug("Returning: file_obj=%r", file_obj)
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
def _opener_registration(urlpath, mode, obj):
    registry = _OPENER_REGISTRY.get()
    from urllib.parse import urlparse
    parsed_uri = urlparse(urlpath)
    path_to_check = Path(parsed_uri.path)
    parent = path_to_check.parent

    key = ((parsed_uri.scheme, parsed_uri.netloc, parent.as_posix()), mode[0])
    # Might raise.
    opener = _create_opener(obj)

    if key in registry:
        if registry[key] != opener:
            raise OpenerRegistrationError(f"Opener already registered for urlpath and mode.")
        else:
            try:
                yield f"{PREFIX}{urlpath}"
            finally:
                registry = _OPENER_REGISTRY.get()
                _ = registry.pop(key, None)
                _OPENER_REGISTRY.set(registry)
    else:
        registry[key] = opener
        _OPENER_REGISTRY.set(registry)
        try:
            yield f"{PREFIX}{urlpath}"
        finally:
            registry = _OPENER_REGISTRY.get()
            _ = registry.pop(key, None)
            _OPENER_REGISTRY.set(registry)


class _FileOpener:
    """Adapts a Python file object to the opener interface."""
    def __init__(self, obj):
        self._obj = obj
    def open(self, path, mode="r", **kwds):
        return self._obj(path, mode=mode, **kwds)
    def is_file(self, path):
        return True
    def is_dir(self, path):
        return False
    def ls(self, path):
        return []
    def size(self, path):
        with self._obj(path) as f:
            f.seek(0, os.SEEK_END)
            return f.tell()


class _FilesystemOpener:
    """Adapts an fsspec filesystem object to the opener interface."""
    def __init__(self, obj):
        self._obj = obj
    def open(self, path, mode="r", **kwds):
        return self._obj.open(path, mode=mode, **kwds)
    def is_file(self, path):
        return self._obj.is_file(path)
    def is_dir(self, path):
        return self._obj.is_dir(path)
    def ls(self, path):
        return self._obj.ls(path)
    def size(self, path):
        return self.size(path)


def _create_opener(obj):
    """Adapt Python file and fsspec objects to the opener interface."""
    if callable(obj):
        opener = _FileOpener(obj)
    else:
        opener = _FilesystemOpener(obj)

    # Before returning we do a quick check that the opener will
    # plausibly function.
    try:
        _ = opener.size("test")
    except (FileNotFoundError, KeyError):
        # We expect the path to not resolve.
        pass
    except (AttributeError, TypeError, ValueError) as err:
        raise OpenerRegistrationError(f"Opener is invalid.") from err

    return opener
