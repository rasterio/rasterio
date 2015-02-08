#!/usr/bin/env python

# Two environmental variables influence this script.
#
# GDAL_CONFIG: the path to a gdal-config program that points to GDAL headers,
# libraries, and data files.
#
# PACKAGE_DATA: if defined, GDAL and PROJ4 data files will be copied into the
# source or binary distribution. This is essential when creating self-contained
# binary wheels.

import logging
import os
import pprint
import shutil
import subprocess
import sys

from setuptools import setup
from setuptools.extension import Extension

logging.basicConfig()
log = logging.getLogger()

# python -W all setup.py ...
if 'all' in sys.warnoptions:
    log.level = logging.DEBUG

# Parse the version from the fiona module.
with open('rasterio/__init__.py') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

with open('VERSION.txt', 'w') as f:
    f.write(version)

# Use Cython if available.
try:
    from Cython.Build import cythonize
except ImportError:
    cythonize = None

# By default we'll try to get options via gdal-config. On systems without,
# options will need to be set in setup.cfg or on the setup command line.
include_dirs = []
library_dirs = []
libraries = []
extra_link_args = []

try:
    import numpy
    include_dirs.append(numpy.get_include())
except ImportError:
    log.critical("Numpy and its headers are required to run setup(). Exiting.")
    sys.exit(1)

try:
    gdal_config = os.environ.get('GDAL_CONFIG', 'gdal-config')
    with open("gdal-config.txt", "w") as gcfg:
        subprocess.call([gdal_config, "--cflags"], stdout=gcfg)
        subprocess.call([gdal_config, "--libs"], stdout=gcfg)
        subprocess.call([gdal_config, "--datadir"], stdout=gcfg)
    with open("gdal-config.txt", "r") as gcfg:
        cflags = gcfg.readline().strip()
        libs = gcfg.readline().strip()
        datadir = gcfg.readline().strip()
    for item in cflags.split():
        if item.startswith("-I"):
            include_dirs.extend(item[2:].split(":"))
    for item in libs.split():
        if item.startswith("-L"):
            library_dirs.extend(item[2:].split(":"))
        elif item.startswith("-l"):
            libraries.append(item[2:])
        else:
            # e.g. -framework GDAL
            extra_link_args.append(item)

    # Conditionally copy the GDAL data. To be used in conjunction with
    # the bdist_wheel command to make self-contained binary wheels.
    if os.environ.get('PACKAGE_DATA'):
        try:
            shutil.rmtree('rasterio/gdal_data')
        except OSError:
            pass
        shutil.copytree(datadir, 'rasterio/gdal_data')

except Exception as e:
    log.warning("Failed to get options via gdal-config: %s", str(e))

# Conditionally copy PROJ.4 data.
if os.environ.get('PACKAGE_DATA'):
    projdatadir = os.environ.get('PROJ_LIB', '/usr/local/share/proj')
    if os.path.exists(projdatadir):
        try:
            shutil.rmtree('rasterio/proj_data')
        except OSError:
            pass
        shutil.copytree(projdatadir, 'rasterio/proj_data')

ext_options = dict(
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args)

log.debug('ext_options:\n%s', pprint.pformat(ext_options))

# When building from a repo, Cython is required.
if os.path.exists("MANIFEST.in") and "clean" not in sys.argv:
    log.info("MANIFEST.in found, presume a repo, cythonizing...")
    if not cythonize:
        log.critical(
            "Cython.Build.cythonize not found. "
            "Cython is required to build from a repo.")
        sys.exit(1)
    ext_modules = cythonize([
        Extension(
            'rasterio._base', ['rasterio/_base.pyx'], **ext_options),
        Extension(
            'rasterio._io', ['rasterio/_io.pyx'], **ext_options),
        Extension(
            'rasterio._copy', ['rasterio/_copy.pyx'], **ext_options),
        Extension(
            'rasterio._features', ['rasterio/_features.pyx'], **ext_options),
        Extension(
            'rasterio._drivers', ['rasterio/_drivers.pyx'], **ext_options),
        Extension(
            'rasterio._warp', ['rasterio/_warp.pyx'], **ext_options),
        Extension(
            'rasterio._fill', ['rasterio/_fill.pyx', 'rasterio/rasterfill.cpp'], **ext_options),
        Extension(
            'rasterio._err', ['rasterio/_err.pyx'], **ext_options),
        Extension(
            'rasterio._example', ['rasterio/_example.pyx'], **ext_options),
        ], quiet=True)

# If there's no manifest template, as in an sdist, we just specify .c files.
else:
    ext_modules = [
        Extension(
            'rasterio._base', ['rasterio/_base.c'], **ext_options),
        Extension(
            'rasterio._io', ['rasterio/_io.c'], **ext_options),
        Extension(
            'rasterio._copy', ['rasterio/_copy.c'], **ext_options),
        Extension(
            'rasterio._features', ['rasterio/_features.c'], **ext_options),
        Extension(
            'rasterio._drivers', ['rasterio/_drivers.c'], **ext_options),
        Extension(
            'rasterio._warp', ['rasterio/_warp.cpp'], **ext_options),
        Extension(
            'rasterio._fill', ['rasterio/_fill.cpp', 'rasterio/rasterfill.cpp'], **ext_options),
        Extension(
            'rasterio._err', ['rasterio/_err.c'], **ext_options),
        Extension(
            'rasterio._example', ['rasterio/_example.c'], **ext_options),
            ]

with open('README.rst') as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = [
    'affine>=1.0',
    'cligj',
    'Numpy>=1.7' ]

if sys.version_info < (3, 4):
    inst_reqs.append('enum34')

setup_args = dict(
    name='rasterio',
    version=version,
    description="Fast and direct raster I/O for use with Numpy and SciPy",
    long_description=readme,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: C',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Scientific/Engineering :: GIS'],
    keywords='raster gdal',
    author='Sean Gillies',
    author_email='sean@mapbox.com',
    url='https://github.com/mapbox/rasterio',
    license='BSD',
    package_dir={'': '.'},
    packages=['rasterio', 'rasterio.rio'],
    entry_points='''
        [console_scripts]
        rio=rasterio.rio.main:cli
    ''',
    include_package_data=True,
    ext_modules=ext_modules,
    zip_safe=False,
    install_requires=inst_reqs)

if os.environ.get('PACKAGE_DATA'):
    setup_args['package_data'] = {'rasterio': ['gdal_data/*', 'proj_data/*']}

setup(**setup_args)
