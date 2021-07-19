#!/usr/bin/env python

# Two environmental variables influence this script.
#
# GDAL_CONFIG: the path to a gdal-config program that points to GDAL headers,
# libraries, and data files.
#
# PACKAGE_DATA: if defined, GDAL and PROJ4 data files will be copied into the
# source or binary distribution. This is essential when creating self-contained
# binary wheels.

import copy
from distutils.command.sdist import sdist
import itertools
import logging
import os
import platform
import pprint
import shutil
from subprocess import check_output
import sys

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

# Parse the version from the rasterio module.
with open("rasterio/__init__.py") as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

with open("VERSION.txt", "w") as f:
    f.write(version)

# Use Cython if available.
try:
    from Cython.Build import cythonize
except ImportError:
    raise SystemExit(
        "ERROR: Cython.Build.cythonize not found. "
        "Cython is required to build rasterio.")

# By default we'll try to get options via gdal-config. On systems without,
# options will need to be set in setup.cfg or on the setup command line.
include_dirs = []
library_dirs = []
libraries = []
extra_link_args = []
gdal2plus = False
gdal_output = [None] * 4
gdalversion = None
gdal_major_version = 0
gdal_minor_version = 0
sdist_fill = []

try:
    import numpy as np

    include_dirs.append(np.get_include())
except ImportError:
    raise SystemExit("ERROR: Numpy and its headers are required to run setup().")

if "clean" not in sys.argv:
    try:
        gdal_config = os.environ.get('GDAL_CONFIG', 'gdal-config')
        for i, flag in enumerate(("--cflags", "--libs", "--datadir", "--version")):
            gdal_output[i] = check_output([gdal_config, flag]).decode("utf-8").strip()

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
            log.info("GDAL API version obtained from gdal-config: %s",
                     gdalversion)

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

    gdal_version_parts = gdalversion.split('.')
    gdal_major_version = int(gdal_version_parts[0])
    gdal_minor_version = int(gdal_version_parts[1])

    if (gdal_major_version, gdal_minor_version) < (2, 3):
        raise SystemExit("ERROR: GDAL >= 2.3 is required for rasterio. "
                 "Please upgrade GDAL.")

# Conditionally copy the GDAL data. To be used in conjunction with
# the bdist_wheel command to make self-contained binary wheels.
if os.environ.get('PACKAGE_DATA'):
    destdir = 'rasterio/gdal_data'
    if gdal_output[2]:
        log.info("Copying gdal data from %s" % gdal_output[2])
        copy_data_tree(gdal_output[2], destdir)
    else:
        # check to see if GDAL_DATA is defined
        gdal_data = os.environ.get('GDAL_DATA', None)
        if gdal_data:
            log.info("Copying gdal_data from %s" % gdal_data)
            copy_data_tree(gdal_data, destdir)

    # Conditionally copy PROJ.4 data.
    projdatadir = os.environ.get('PROJ_LIB', '/usr/local/share/proj')
    if os.path.exists(projdatadir):
        log.info("Copying proj_data from %s" % projdatadir)
        copy_data_tree(projdatadir, 'rasterio/proj_data')



compile_time_env = {
    "CTE_GDAL_MAJOR_VERSION": gdal_major_version,
    "CTE_GDAL_MINOR_VERSION": gdal_minor_version,
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

# GDAL 2.3 and newer requires C++11
if (gdal_major_version, gdal_minor_version) >= (2, 3):
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
cythonize_options = {"language_level": sys.version_info[0]}
if os.environ.get('CYTHON_COVERAGE'):
    cythonize_options['compiler_directives'] = {'linetrace': True}
    cythonize_options['annotate'] = True
    ext_options['define_macros'].extend(
        [('CYTHON_TRACE', '1'), ('CYTHON_TRACE_NOGIL', '1')])

log.debug('ext_options:\n%s', pprint.pformat(ext_options))

ext_modules = None
if "clean" not in sys.argv:
    ext_modules = cythonize([
        Extension(
            'rasterio._base', ['rasterio/_base.pyx'], **ext_options),
        Extension(
            'rasterio._io', ['rasterio/_io.pyx'], **ext_options),
        Extension(
            'rasterio._features', ['rasterio/_features.pyx'], **ext_options),
        Extension(
            'rasterio._env', ['rasterio/_env.pyx'], **ext_options),
        Extension(
            'rasterio._warp', ['rasterio/_warp.pyx'], **cpp_ext_options),
        Extension(
            'rasterio._fill', ['rasterio/_fill.pyx'], **cpp_ext_options),
        Extension(
            'rasterio._err', ['rasterio/_err.pyx'], **ext_options),
        Extension(
            'rasterio._example', ['rasterio/_example.pyx'], **ext_options),
        Extension(
            'rasterio._crs', ['rasterio/_crs.pyx'], **ext_options),
        Extension(
            'rasterio.shutil', ['rasterio/shutil.pyx'], **ext_options),
        Extension(
            'rasterio._transform', ['rasterio/_transform.pyx'], **ext_options)],
        quiet=True, compile_time_env=compile_time_env, **cythonize_options)



with open("README.rst", encoding="utf-8") as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = [
    "affine",
    "attrs",
    "certifi",
    "click>=4.0",
    "cligj>=0.5",
    "numpy",
    "snuggs>=1.4.1",
    "click-plugins",
    "setuptools",
]

extra_reqs = {
    "docs": ["ghp-import", "numpydoc", "sphinx", "sphinx-rtd-theme"],
    "ipython": ["ipython>=2.0"],
    "plot": ["matplotlib"],
    "s3": ["boto3>=1.2.4"],
    "test": [
        "boto3>=1.2.4",
        "hypothesis",
        "packaging",
        "pytest-cov>=2.2.0",
        "pytest>=2.8.2",
        "shapely",
    ],
}

# Add all extra requirements
extra_reqs["all"] = list(set(itertools.chain(*extra_reqs.values())))

setup_args = dict(
    name="rasterio",
    version=version,
    description="Fast and direct raster I/O for use with Numpy and SciPy",
    long_description=readme,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: C",
        "Programming Language :: Cython",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="raster gdal",
    author="Sean Gillies",
    author_email="sean@mapbox.com",
    url="https://github.com/mapbox/rasterio",
    license="BSD",
    package_dir={"": "."},
    packages=["rasterio", "rasterio.rio"],
    entry_points="""
        [console_scripts]
        rio=rasterio.rio.main:main_group

        [rasterio.rio_commands]
        blocks=rasterio.rio.blocks:blocks
        bounds=rasterio.rio.bounds:bounds
        calc=rasterio.rio.calc:calc
        clip=rasterio.rio.clip:clip
        convert=rasterio.rio.convert:convert
        edit-info=rasterio.rio.edit_info:edit
        env=rasterio.rio.env:env
        gcps=rasterio.rio.gcps:gcps
        info=rasterio.rio.info:info
        insp=rasterio.rio.insp:insp
        mask=rasterio.rio.mask:mask
        merge=rasterio.rio.merge:merge
        overview=rasterio.rio.overview:overview
        rasterize=rasterio.rio.rasterize:rasterize
        rm=rasterio.rio.rm:rm
        sample=rasterio.rio.sample:sample
        shapes=rasterio.rio.shapes:shapes
        stack=rasterio.rio.stack:stack
        transform=rasterio.rio.transform:transform
        warp=rasterio.rio.warp:warp
    """,
    include_package_data=True,
    ext_modules=ext_modules,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
    python_requires=">=3.6",
)

if os.environ.get('PACKAGE_DATA'):
    setup_args['package_data'] = {'rasterio': ['gdal_data/*', 'proj_data/*']}

setup(**setup_args)
