rasterio
========

Very easy and direct raster I/O for Python programmers.

This package is aimed at developers who want little more than to read raster
images into Numpy arrays or buffers, operate on them in Python (or Cython), and
write the results out to new raster files.

Rasterio employs GDAL under the hood for file I/O and raster formatting.

Example
-------

Here's an example of the features fasterio aims to provide.

    import numpy
    import rasterio
    
    # Read raster bands directly into provided Numpy arrays.
    with rasterio.open('reflectance.tif') as src:
        vis = src.read_band(2, numpy.zeros((src.shape), numpy.float))
        nir = src.read_band(3, numpy.zeros((src.shape), numpy.float))

    ndvi = (nir-vis)/(nir+vis)
    
    # Write the product as a raster band to a new file.
    with rasterio.open('ndvi.tif', 'w') as dst:
        dst.append_band(ndvi)

Dependencies
------------

C library dependecies:

- GDAL

Python package dependencies:

- numpy
- six

License
-------

See LICENSE.txt

Authors
-------

See AUTHORS.txt

Changes
-------

See CHANGES.txt

