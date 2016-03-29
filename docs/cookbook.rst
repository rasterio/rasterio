=================
Rasterio Cookbook
=================

.. todo::

    Fill out examples of using rasterio to handle tasks from typical
    GIS and remote sensing workflows.

The Rasterio cookbook is intended to provide in-depth examples of rasterio usage
that are not covered by the basic usage in the User's Manual. Before using code
from the cookbook, you should be familar with the basic usage of rasterio; see
"Reading Datasets", "Working with Datasets" and "Writing Datasets" to brush up on
the fundamentals.

Generating summary statistics for each band
-------------------------------------------

.. literalinclude:: recipies/band_summary_stats.py
    :language: python
    :linenos:

.. code::

    $ python docs/recipies/band_summary_stats.py
    [{'max': 255, 'mean': 29.94772668847656, 'median': 13.0, 'min': 0},
     {'max': 255, 'mean': 44.516147889382289, 'median': 30.0, 'min': 0},
     {'max': 255, 'mean': 48.113056354742945, 'median': 30.0, 'min': 0}]

Raster algebra
--------------

Resampling rasters to a different cell size
--------------------------------------------

Reproject/warp a raster to a different CRS
------------------------------------------

Raster to polygon features
--------------------------

Rasterizing GeoJSON features
----------------------------

Clipping raster to a polygon feature
------------------------------------

Creating valid data bounding polygons
-------------------------------------

Raster to vector line feature
-----------------------------

Creating raster from numpy array
--------------------------------

Creating a least cost path
--------------------------

Using a scipy filter to smooth a raster
---------------------------------------

This recipie demonstrates the use of scipy's `signal processing filters <http://docs.scipy.org/doc/scipy/reference/signal.html#signal-processing-scipy-signal>`_ to manipulate multi-band raster imagery
and save the results to a new GeoTIFF. Here we apply a median filter to smooth
the image and remove small inclusions (at the expense of some sharpness and detail).

.. literalinclude:: recipies/filter.py
    :language: python
    :linenos:

.. code::

    $ python docs/recipies/filter.py


The original image

.. image:: img/RGB.byte.jpg
    :scale: 50 %

With median filter applied

.. image:: img/filtered.jpg
    :scale: 50 %

Using skimage to adjust the saturation of a RGB raster
------------------------------------------------------

This recipie demonstrates the use of manipulating color with the scikit image `color module <http://scikit-image.org/docs/stable/api/skimage.color.html>`_.

.. literalinclude:: recipies/saturation.py
    :language: python
    :linenos:

.. code::

    $ python docs/recipies/saturation.py


The original image

.. image:: img/RGB.byte.jpg
    :scale: 50 %

With increased saturation

.. image:: img/saturation.jpg
    :scale: 50 %
