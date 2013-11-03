import logging, subprocess, sys, os
from setuptools import setup, find_packages

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
# Have to do this after importing setuptools, which monkey patches distutils.
from distutils.extension import Extension

# Use Cython if available.
try:
    from Cython.Build import cythonize
except ImportError:
    cythonize = None

logging.basicConfig()
log = logging.getLogger()

version = '0.1'

# By default we'll try to get options via gdal-config. On systems without,
# options will need to be set in setup.cfg or on the setup command line.
include_dirs = []
library_dirs = []
libraries = []
extra_link_args = []

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

import numpy
include_dirs.append(numpy.get_include())

ext_options = dict(
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args)

print(ext_options)

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


setup(name='rasterio',
      version=version,
      description="Reimagining GDAL raster access",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='raster gdal',
      author='Sean Gillies',
      author_email='sean@mapbox.com',
      url='',
      license='BSD',
#      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      package_dir={'': '.'},
      packages=['rasterio'],
      include_package_data=True,
      ext_modules=ext_modules,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
