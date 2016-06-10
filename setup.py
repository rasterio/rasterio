#!/usr/bin/env python

# Two environmental variables influence this script.
#
# GDAL_CONFIG: the path to a gdal-config program that points to GDAL headers,
# libraries, and data files.
#
# PACKAGE_DATA: if defined, GDAL and PROJ4 data files will be copied into the
# source or binary distribution. This is essential when creating self-contained
# binary wheels.

import itertools
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


def check_output(cmd):
    # since subprocess.check_output doesn't exist in 2.6
    # we wrap it here.
    try:
        out = subprocess.check_output(cmd)
        return out.decode('utf')
    except AttributeError:
        # For some reasone check_output doesn't exist
        # So fall back on Popen
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = p.communicate()
        return out


def copy_data_tree(datadir, destdir):
    try:
        shutil.rmtree(destdir)
    except OSError:
        pass
    shutil.copytree(datadir, destdir)


# python -W all setup.py ...
if 'all' in sys.warnoptions:
    log.level = logging.DEBUG

# Parse the version from the rasterio module.
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
gdal2plus = False
gdal_output = [None] * 4

try:
    import numpy as np
    include_dirs.append(np.get_include())
except ImportError:
    log.critical("Numpy and its headers are required to run setup(). Exiting.")
    sys.exit(1)

try:
    gdal_config = os.environ.get('GDAL_CONFIG', 'gdal-config')
    for i, flag in enumerate(("--cflags", "--libs", "--datadir", "--version")):
        gdal_output[i] = check_output([gdal_config, flag]).strip()

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
    for item in gdal_output[3].split():
        gdal2plus = not item.startswith("1.")

except Exception as e:
    if os.name == "nt":
        log.info(("Building on Windows requires extra options to setup.py to locate needed GDAL files.\n"
                 "More information is available in the README."))
    else:
        log.warning("Failed to get options via gdal-config: %s", str(e))


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

ext_options = dict(
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args)

if not os.name == "nt":
    # These options fail on Windows if using Visual Studio
    ext_options['extra_compile_args'] = ['-Wno-unused-parameter',
                                         '-Wno-unused-function']

cythonize_options = {}
if os.environ.get('CYTHON_COVERAGE'):
    cythonize_options['compiler_directives'] = {'linetrace': True}
    cythonize_options['annotate'] = True
    ext_options['define_macros'] = [('CYTHON_TRACE', '1'),
                                    ('CYTHON_TRACE_NOGIL', '1')]

log.debug('ext_options:\n%s', pprint.pformat(ext_options))

if gdal2plus:
    # GDAL>=2.0 does not require vendorized rasterfill.cpp
    cython_fill = ['rasterio/_fill.pyx']
    sdist_fill = ['rasterio/_fill.cpp']
else:
    cython_fill = ['rasterio/_fill.pyx', 'rasterio/rasterfill.cpp']
    sdist_fill = ['rasterio/_fill.cpp', 'rasterio/rasterfill.cpp']

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
            'rasterio._fill', cython_fill, **ext_options),
        Extension(
            'rasterio._err', ['rasterio/_err.pyx'], **ext_options),
        Extension(
            'rasterio._example', ['rasterio/_example.pyx'], **ext_options),
        Extension(
            'rasterio._crs', ['rasterio/_crs.pyx'], **ext_options)],
        quiet=True, **cythonize_options)

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
            'rasterio._fill', sdist_fill, **ext_options),
        Extension(
            'rasterio._err', ['rasterio/_err.c'], **ext_options),
        Extension(
            'rasterio._example', ['rasterio/_example.c'], **ext_options),
        Extension(
            'rasterio._crs', ['rasterio/_crs.c'], **ext_options)]

with open('README.rst') as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = ['affine', 'cligj', 'numpy', 'snuggs', 'click-plugins']

if sys.version_info < (3, 4):
    inst_reqs.append('enum34')

extra_reqs = {
    'ipython': ['ipython>=2.0'],
    's3': ['boto3>=1.2.4'],
    'plot': ['matplotlib'],
    'test': [
        'pytest>=2.8.2', 'pytest-cov>=2.2.0', 'boto3>=1.2.4', 'packaging'],
    'docs': ['ghp-import', 'numpydoc', 'sphinx', 'sphinx-rtd-theme']}

# Add all extra requirements
extra_reqs['all'] = list(set(itertools.chain(*extra_reqs.values())))

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
        'Programming Language :: Cython',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Scientific/Engineering :: GIS'],
    keywords='raster gdal',
    author='Sean Gillies',
    author_email='sean@mapbox.com',
    url='https://github.com/mapbox/rasterio',
    license='BSD',
    package_dir={'': '.'},
    packages=['rasterio', 'rasterio.rio', 'rasterio.tools'],
    entry_points='''
        [console_scripts]
        rio=rasterio.rio.main:main_group

        [rasterio.rio_commands]
        bounds=rasterio.rio.bounds:bounds
        calc=rasterio.rio.calc:calc
        clip=rasterio.rio.clip:clip
        convert=rasterio.rio.convert:convert
        edit-info=rasterio.rio.edit_info:edit
        env=rasterio.rio.env:env
        info=rasterio.rio.info:info
        insp=rasterio.rio.insp:insp
        mask=rasterio.rio.mask:mask
        merge=rasterio.rio.merge:merge
        overview=rasterio.rio.overview:overview
        rasterize=rasterio.rio.rasterize:rasterize
        sample=rasterio.rio.sample:sample
        shapes=rasterio.rio.shapes:shapes
        stack=rasterio.rio.stack:stack
        warp=rasterio.rio.warp:warp
        transform=rasterio.rio.transform:transform
    ''',
    include_package_data=True,
    ext_modules=ext_modules,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs)

if os.environ.get('PACKAGE_DATA'):
    setup_args['package_data'] = {'rasterio': ['gdal_data/*', 'proj_data/*']}

setup(**setup_args)
