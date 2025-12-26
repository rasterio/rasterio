#!/usr/bin/env python

# Two environmental variables influence this script.
#
# GDAL_CONFIG: the path to a gdal-config program that points to GDAL headers,
# libraries, and data files.
#
# PACKAGE_DATA: if defined, GDAL and PROJ4 data files will be copied into the
# source or binary distribution. This is essential when creating self-contained
# binary wheels.
#
# GDAL_INSTALL_PREFIX: if defined, we assume that GDAL is installed at this path, under `lib`, `include`, and `share`
# subfolders.

import copy
import logging
import os
import platform
import pprint
import re
import shutil
import sys
from subprocess import check_output

from setuptools import setup
from setuptools.extension import Extension

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger()


def copy_data_tree(datadir, destdir):
    try:
        shutil.rmtree(destdir)
    except OSError:
        pass
    shutil.copytree(datadir, destdir)


# python -W all setup.py ...
if "all" in sys.warnoptions:
    log.level = logging.DEBUG

# Use Cython if available.
try:
    from Cython.Build import cythonize
except ImportError:
    raise SystemExit(
        "ERROR: Cython.Build.cythonize not found. "
        "Cython is required to build rasterio.")

# By default we'll try to get options via gdal-config. On systems without,
# options will need to be set in setup.cfg, on the setup command line, or through
# the GDAL_INSTALL_PREFIX environment variable.
include_dirs: list[str] = []
library_dirs: list[str] = []
libraries: list[str] = []
extra_link_args: list[str] = []
gdal2plus: bool = False
gdal_output: list[str | None] = [None] * 4
gdalversion: str | None = None
gdal_major_version: int = 0
gdal_minor_version: int = 0
gdal_patch_version: int = 0
gdal_data_dir: str | None = None

try:
    import numpy as np

    include_dirs.append(np.get_include())
except ImportError:
    raise SystemExit("ERROR: Numpy and its headers are required to run setup().")

def fill_gdal_build_options_from_prefix(gdal_install_prefix: str) -> None:
    """Fill the global GDAL build options using information from the provided install path.

    gdal_install_prefix should contain `lib`, `include`, and `share` subfolders containing a GDAL install.

    Raise `RuntimeError` if the provided prefix does not seem to contain a GDAL install.
    """
    global \
        gdal_data_dir, \
        gdalversion, \
        gdal_major_version, \
        gdal_minor_version, \
        gdal_patch_version

    if not os.path.isdir(gdal_install_prefix):
        raise FileNotFoundError(
            "GDAL install prefix does not seem to be a directory (value is %s)",
            gdal_install_prefix,
        )

    # Find library directory
    found_library_dir = os.path.join(gdal_install_prefix, "lib")
    if not os.path.isdir(found_library_dir):
        raise RuntimeError("Could not find library directory at %s", found_library_dir)

    # Does the GDAL library file exist?
    found_gdal_lib = os.path.join(
        found_library_dir, "gdal.lib" if os.name == "nt" else "gdal.so"
    )
    if not os.path.isfile(found_gdal_lib):
        raise RuntimeError("Could not find GDAL library file at %s", found_library_dir)
    found_gdal_lib_name = os.path.splitext(os.path.basename(found_gdal_lib))[0]

    # Find include directory
    found_include_dir = os.path.join(gdal_install_prefix, "include")
    if not os.path.isdir(found_include_dir):
        raise RuntimeError("Could not find include directory at %s", found_include_dir)

    # Find GDAL_DATA directory
    found_gdal_data_dir = os.path.join(gdal_install_prefix, "share", "gdal")
    if not os.path.isdir(found_gdal_data_dir):
        raise RuntimeError(
            "Could not find GDAL_DATA directory at %s", found_gdal_data_dir
        )

    # Extract GDAL version numbers
    found_version_header = os.path.join(found_include_dir, "gdal_version.h")
    try:
        with open(found_version_header, "rt") as version_header_stream:
            version_header_text = version_header_stream.read()
    except FileNotFoundError as error:
        raise RuntimeError(
            "Could not find GDAL version header at %s", found_version_header
        ) from error
    major_version_match = re.search(
        r"^#\s*define\s+GDAL_VERSION_MAJOR\s+(\d+)\s*$",
        version_header_text,
        flags=re.MULTILINE,
    )
    minor_version_match = re.search(
        r"^#\s*define\s+GDAL_VERSION_MINOR\s+(\d+)\s*$",
        version_header_text,
        flags=re.MULTILINE,
    )
    rev_version_match = re.search(
        r"^#\s*define\s+GDAL_VERSION_REV\s+(\d+)\s*$",
        version_header_text,
        flags=re.MULTILINE,
    )
    if major_version_match and minor_version_match and rev_version_match:
        gdal_version_numbers: tuple[int, int, int] = (
            int(major_version_match.group(1)),
            int(minor_version_match.group(1)),
            int(rev_version_match.group(1)),
        )
    else:
        raise RuntimeError("Could not read GDAL version numbers from gdal_version.h")

    log.info(
        "Found a GDAL install at %s that seems complete, using it", gdal_install_prefix
    )
    library_dirs.append(found_library_dir)
    include_dirs.append(found_include_dir)
    gdalversion = ".".join(map(str, gdal_version_numbers))
    gdal_major_version, gdal_minor_version, gdal_patch_version = gdal_version_numbers
    libraries.append(found_gdal_lib_name)
    gdal_data_dir = found_gdal_data_dir


if "clean" not in sys.argv:
    try:
        provided_gdal_install_prefix = os.environ.get("GDAL_INSTALL_PREFIX", None)
        if provided_gdal_install_prefix:
            log.info(
                "Getting GDAL build options from GDAL_INSTALL_PREFIX environment variable set to %s",
                provided_gdal_install_prefix,
            )
            fill_gdal_build_options_from_prefix(provided_gdal_install_prefix)
        else:
            log.info("Using gdal-config to get GDAL build options")
            gdal_config = os.environ.get("GDAL_CONFIG", "gdal-config")
            for i, flag in enumerate(("--cflags", "--libs", "--datadir", "--version")):
                gdal_output[i] = (
                    check_output([gdal_config, flag]).decode("utf-8").strip()
                )

            for item in gdal_output[0].split():
                if item.startswith("-I"):
                    include_dirs.extend(item[2:].split(":"))
            for item in gdal_output[1].split():
                if item.startswith("-L"):
                    library_dirs.extend(item[2:].split(":"))
                elif item.startswith("-l"):
                    libraries.append(item[2:])
                else:
                    # e.g. -framework GDAL
                    extra_link_args.append(item)
            # datadir, gdal_output[2] handled below

            gdalversion = gdal_output[3]
            if gdalversion:
                log.info("GDAL API version obtained from gdal-config: %s", gdalversion)

    except Exception as e:
        if os.name == "nt":
            log.info("Building on Windows requires extra options to setup.py "
                     "to locate needed GDAL files. More information is available "
                     "in the README.")
        else:
            log.warning("Failed to get options via gdal-config: %s", str(e))

    # Get GDAL API version from environment variable.
    if 'GDAL_VERSION' in os.environ:
        gdalversion = os.environ['GDAL_VERSION']
        log.info("GDAL API version obtained from environment: %s", gdalversion)

    # Get GDAL API version from the command line if specified there.
    if '--gdalversion' in sys.argv:
        index = sys.argv.index('--gdalversion')
        sys.argv.pop(index)
        gdalversion = sys.argv.pop(index)
        log.info("GDAL API version obtained from command line option: %s",
                 gdalversion)

    if not gdalversion:
        raise SystemExit("ERROR: A GDAL API version must be specified. Provide a path "
                 "to gdal-config using a GDAL_CONFIG environment variable "
                 "or use a GDAL_VERSION environment variable.")

    gdal_major_version, gdal_minor_version, gdal_patch_version = map(
        int, re.findall("[0-9]+", gdalversion)[:3]
    )

    if (gdal_major_version, gdal_minor_version) < (3, 8):
        raise SystemExit("ERROR: GDAL >= 3.8 is required for rasterio. "
                 "Please upgrade GDAL.")

# Conditionally copy the GDAL data. To be used in conjunction with
# the bdist_wheel command to make self-contained binary wheels.
gdal_data_destination = "rasterio/gdal_data"
if gdal_data_dir is not None:
    log.info("Copying previously-found GDAL data from %s", gdal_data_dir)
    copy_data_tree(gdal_data_dir, gdal_data_destination)
elif os.environ.get("PACKAGE_DATA"):
    if gdal_output[2]:
        log.info("Copying gdal data from %s" % gdal_output[2])
        copy_data_tree(gdal_output[2], gdal_data_destination)
    else:
        # check to see if GDAL_DATA is defined
        gdal_data = os.environ.get('GDAL_DATA', None)
        if gdal_data:
            log.info("Copying gdal_data from %s" % gdal_data)
            copy_data_tree(gdal_data, gdal_data_destination)

    # Conditionally copy PROJ DATA.
    projdatadir = os.environ.get('PROJ_DATA', os.environ.get('PROJ_LIB', '/usr/local/share/proj'))
    if os.path.exists(projdatadir):
        log.info("Copying proj_data from %s" % projdatadir)
        copy_data_tree(projdatadir, 'rasterio/proj_data')
else:
    log.info("Not copying GDAL data to the final package")

compile_time_env = {
    "CTE_GDAL_MAJOR_VERSION": gdal_major_version,
    "CTE_GDAL_MINOR_VERSION": gdal_minor_version,
    "CTE_GDAL_PATCH_VERSION": gdal_patch_version,
}

ext_options = {
    'include_dirs': include_dirs,
    'library_dirs': library_dirs,
    'libraries': libraries,
    'extra_link_args': extra_link_args,
    'define_macros': [],
    'cython_compile_time_env': compile_time_env
}

if not os.name == "nt":
    # These options fail on Windows if using Visual Studio
    ext_options['extra_compile_args'] = ['-Wno-unused-parameter',
                                         '-Wno-unused-function']

# Copy extension options for cpp extension modules.
cpp_ext_options = copy.deepcopy(ext_options)

# Remove -std=c++11 from C extension options.
try:
    ext_options['extra_link_args'].remove('-std=c++11')
    ext_options['extra_compile_args'].remove('-std=c++11')
except Exception:
    pass

cpp11_flag = '-std=c++11'

# 'extra_compile_args' may not be defined
eca = cpp_ext_options.get('extra_compile_args', [])

if platform.system() == 'Darwin':

    if cpp11_flag not in eca:
        eca.append(cpp11_flag)

    eca += [cpp11_flag, '-mmacosx-version-min=10.9', '-stdlib=libc++']

# TODO: Windows

elif cpp11_flag not in eca:
    eca.append(cpp11_flag)

cpp_ext_options['extra_compile_args'] = eca

# Configure optional Cython coverage.
cythonize_options = {"language_level": sys.version_info[0], "compiler_directives": {"freethreading_compatible": True}}
if os.environ.get('CYTHON_COVERAGE'):
    cythonize_options['compiler_directives'].update(linetrace=True)
    cythonize_options['annotate'] = True
    ext_options['define_macros'].extend(
        [('CYTHON_TRACE', '1'), ('CYTHON_TRACE_NOGIL', '1')])

log.debug('ext_options:\n%s', pprint.pformat(ext_options))

ext_modules = None
if "clean" not in sys.argv:
    extensions = [
        Extension("rasterio._base", ["rasterio/_base.pyx"], **ext_options),
        Extension("rasterio._io", ["rasterio/_io.pyx"], **ext_options),
        Extension("rasterio._features", ["rasterio/_features.pyx"], **ext_options),
        Extension("rasterio._env", ["rasterio/_env.pyx"], **ext_options),
        Extension("rasterio._warp", ["rasterio/_warp.pyx"], **cpp_ext_options),
        Extension("rasterio._fill", ["rasterio/_fill.pyx"], **cpp_ext_options),
        Extension("rasterio._err", ["rasterio/_err.pyx"], **ext_options),
        Extension("rasterio._example", ["rasterio/_example.pyx"], **ext_options),
        Extension("rasterio._version", ["rasterio/_version.pyx"], **ext_options),
        Extension("rasterio.cache", ["rasterio/cache.pyx"], **ext_options),
        Extension("rasterio.crs", ["rasterio/crs.pyx"], **ext_options),
        Extension("rasterio.shutil", ["rasterio/shutil.pyx"], **ext_options),
        Extension("rasterio._transform", ["rasterio/_transform.pyx"], **ext_options),
        Extension("rasterio._filepath", ["rasterio/_filepath.pyx"], **cpp_ext_options),
        Extension(
            "rasterio._vsiopener", ["rasterio/_vsiopener.pyx"], **ext_options
        ),
    ]
    ext_modules = cythonize(
        extensions, quiet=True, compile_time_env=compile_time_env, **cythonize_options
    )

setup_args = {}
if os.environ.get('PACKAGE_DATA'):
    setup_args['package_data'] = {'rasterio': ['gdal_data/*', 'proj_data/*']}

# See pyproject.toml for project metadata
setup(
    name="rasterio",  # need by GitHub dependency graph
    ext_modules=ext_modules,
    **setup_args,
)
