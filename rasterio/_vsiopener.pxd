include "gdal.pxi"

cdef int install_pyopener_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct)
cdef void uninstall_pyopener_plugin(VSIFilesystemPluginCallbacksStruct *callbacks_struct)
