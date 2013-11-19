import logging
import os
import subprocess
import sys
from setuptools import setup, find_packages

from distutils.extension import Extension

logging.basicConfig()
log = logging.getLogger()

version = '0.1'

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
    gdal_config = "gdal-config"
    with open("gdal-config.txt", "w") as gcfg:
        subprocess.call([gdal_config, "--cflags"], stdout=gcfg)
        subprocess.call([gdal_config, "--libs"], stdout=gcfg)
    with open("gdal-config.txt", "r") as gcfg:
        cflags = gcfg.readline().strip()
        libs = gcfg.readline().strip()
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
except Exception as e:
    log.warning("Failed to get options via gdal-config: %s", str(e))

ext_options = dict(
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args)

# When building from a repo, Cython is required.
if os.path.exists("MANIFEST.in"):
    log.info("MANIFEST.in found, presume a repo, cythonizing...")
    if not cythonize:
        log.critical(
            "Cython.Build.cythonize not found. "
            "Cython is required to build from a repo.")
        sys.exit(1)
    ext_modules = cythonize([
        Extension(
            'rasterio._io', ['rasterio/_io.pyx'], **ext_options)])

# If there's no manifest template, as in an sdist, we just specify .c files.
else:
    ext_modules = [
        Extension(
            'rasterio._io', ['rasterio/_io.c'], **ext_options)]

with open('README.rst') as f:
    readme = f.read()

setup(name='rasterio',
      version=version,
      description=(
          "Fast and direct raster I/O for Python programmers who use Numpy"),
      long_description=readme,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: C',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.0',
          'Programming Language :: Python :: 3.1',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Topic :: Multimedia :: Graphics :: Graphics Conversion',
          'Topic :: Scientific/Engineering :: GIS'
          ],
      keywords='raster gdal',
      author='Sean Gillies',
      author_email='sean@mapbox.com',
      url='https://github.com/sgillies/rasterio',
      license='BSD',
      package_dir={'': '.'},
      packages=['rasterio'],
      include_package_data=True,
      ext_modules=ext_modules,
      zip_safe=False,
      install_requires=[
          'Numpy',
          'setuptools'
      ])
