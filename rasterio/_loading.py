import glob
import os
import logging
import contextlib
import platform
import sys

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# With Python >= 3.8 on Windows directories in PATH are not automatically
# searched for DLL dependencies and must be added manually with
# os.add_dll_directory.
# see https://github.com/Toblerity/Fiona/issues/851

@contextlib.contextmanager
def add_gdal_dll_directories():
    dll_dirs = []
    if platform.system() == 'Windows' and sys.version_info >= (3, 8):
        dll_directory = os.path.join(os.path.dirname(__file__), '.libs')
        if os.path.exists(dll_directory):
            dll_dirs.append(os.add_dll_directory(dll_directory))
        else:
            if 'PATH' in os.environ:
                for p in os.environ['PATH'].split(os.pathsep):
                    if glob.glob(os.path.join(p, 'gdal*.dll')):
                        os.add_dll_directory(p)
    try:
        yield None
    finally:
        for dll_dir in dll_dirs:
            dll_dir.close()
