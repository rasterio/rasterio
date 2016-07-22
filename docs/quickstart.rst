==========
Quickstart
==========

Reading and writing data files is a spatial data analyst's bread and butter.
This document explains how to use Rasterio to read existing files and to create
new files. Some advanced topics are glossed over to be covered in more detail
elsewhere in Rasterio's documentation. Only the GeoTIFF format is used here,
but the examples do apply to other raster data formats. It is presumed that
Rasterio has been `installed <./installation>`__.

Opening a dataset in reading mode
---------------------------------

Consider an "example.tif" file with 16-bit imagery covering a portion
of the United States's Colorado Plateau [#]_. A rescaled and dynamically squashed
version is shown below.

.. image:: img/example.png

Import rasterio to begin.

.. code-block:: pycon

    >>> import rasterio

Next, open the file.

.. code-block:: pycon

    >>> dataset = rasterio.open('example.tif')

Rasterio's ``rasterio.open()`` takes a path and returns a dataset object. The
path may point to a file of any supported raster format. Rasterio will open it
using the appropriate GDAL format driver.

.. code-block:: pycon

    >>> dataset.name
    'example.tif'
    >>> dataset.mode
    'r'
    >>> dataset.closed
    False

Dataset objects have some of the same properties as Python file objects.

Dataset properties
------------------

Properties of the raster data stored in "example.tif" can be accessed through
properties of `dataset`. Dataset objects have "bands" and this example has 1.

.. code-block:: pycon

    >>> dataset.count
    1

The band's raster array has 7731 columns and 7871 rows.

.. code-block:: pycon

    >>> dataset.width, dataset.height
    (7731, 7871)

The array contains unsigned 16-bit integer values.

.. code-block:: pycon

    >>> dataset.dtypes
    ('uint16',)

The GeoTIFF format also supports signed integers and floats of different size.

Dataset georeferencing
----------------------

A GIS raster dataset is different from an ordinary image. The pixels in the
example are mapped to regions on the earth's surface.

.. code-block:: pycon

    >>> dataset.bounds
    BoundingBox(left=358485.0, bottom=4028985.0, right=590415.0, top=4265115.0)

A raster dataset has a spatial bounding box. Our example covers the world from
358485 meters (in this case) to 590415 meters, left to right, and 4028985
meters to 4265115 meters bottom to top. It covers a region 231.93 kilometers
wide by 236.13 kilometers high.

The ``bounds`` property is derived from a more fundamental property: the
dataset's geospatial ``transform``.

.. code-block:: pycon

    >>> dataset.transform
    Affine(30.0, 0.0, 358485.0,
           0.0, -30.0, 4265115.0)

This is an affine transformation matrix that maps pixel locations in (row, col)
coordinates to (x, y) spatial positions. The product of this matrix and ``(0,
0)``, the row and column coordinates of the upper left corner of the dataset,
is the spatial position of the upper left corner.

.. code-block:: pycon

    >>> dataset.transform * (0, 0)
    (358485.0, 4265115.0)

The position of the lower right corner is obtained similarly.

.. code-block:: pycon

    >>> dataset.transform * (dataset.width, dataset.height)
    (590415.0, 4028985.0)

But what do these numbers mean? 4028985 meters from where? These coordinate
values are relative to the origin of the dataset's coordinate reference system
(CRS).

.. code-block:: pycon

    >>> dataset.crs
    CRS({'init': 'epsg:32612'})

"epsg:32612" identifies a particular coordinate reference system: `UTM
<https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system>`__
zone 12N.  This system is used for mapping areas in the Northern Hemisphere
between 108 and 114 degrees west. The upper left corner of the example dataset,
``(358485.0, 4265115.0)``, is 141.5 kilometers west of zone 12's central meridian
(111 degrees west) and 4265 kilometers north of the equator.

Coordinate reference systems are an advanced topic. Suffice it to say that
between the ``crs`` property and the ``transform`` property a raster dataset is
geo-referenced and can be compared to other GIS datasets.

Reading raster data
-------------------

How can the pixels of a raster band be accessed? By calling ``dataset.read()``
with one of the values from ``dataset.indexes``. By GDAL convention, bands are
indexed from 1.

.. code-block:: pycon

    >>> dataset.indexes
    (1,)
    >>> band_one = dataset.read(1)

The ``read()`` method returns a Numpy N-D array.

.. code-block:: pycon

    >>> band_one
    array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint16)

Pixels of the array can be had by their row, column index.

.. code-block:: pycon

    >>> band_one[dataset.height // 2, dataset.width // 2]
    17491

Spatial indexing
----------------

Datasets have a method of getting indexes for spatial points. To get the value
for the pixel 100 kilometers east and 50 kilometers south of the dataset's
upper left corner, do the following.

.. code-block:: pycon

    >>> x, y = (dataset.bounds.left + 100000, dataset.bounds.top - 50000)
    >>> row, col = dataset.index(x, y)
    >>> row, col
    (1666, 3333)
    >>> band_one[row, col]
    7566

To get the spatial coordinates of a pixel, use the dataset's ``xy()`` method.
The coordinates of the center of the image are

.. code-block:: pycon

    >>> dataset.xy(dataset.width // 2, dataset.height // 2)
    (476550.0, 4149150.0)

Creating data
-------------

An N-D array of values can be written to a raster data file and thus shared
with other GIS applications such as QGIS using Rasterio dataset objects.

As an example, consider an array of floating point values representing, e.g.,
a temperature or pressure anomaly field measured or modeled on a regular grid,
240 columns by 180 rows. The first and last grid points on the horizontal axis
are located at 4.0 degrees west and 4.0 degrees east longitude, the first and
last grid points on the vertical axis are located at 3 degrees south and
3 degrees north latitude.

.. code-block:: pycon

    >>> import numpy as np
    >>> x = np.linspace(-4.0, 4.0, 240)
    >>> y = np.linspace(-3.0, 3.0, 180)
    >>> X, Y = np.meshgrid(x, y)
    >>> Z1 = np.exp(-2 * np.log(2) * ((X - 0.5) ** 2 + (Y - 0.5) ** 2) / 1 ** 2)
    >>> Z2 = np.exp(-3 * np.log(2) * ((X + 0.5) ** 2 + (Y + 0.5) ** 2) / 2.5 ** 2)
    >>> Z = 10.0 * (Z2 - Z1)

The fictional field for this example consists of the difference of two Gaussian
distributions. Its contours are shown below.

.. image:: img/field.png


Opening a dataset in writing mode
---------------------------------

To save this array along with georeferencing information to a new raster data
file, call ``rasterio.open()`` with a path to the new file to be created,
``'w'`` to specify writing mode, and keyword arguments specifying

* the name of the desired format driver
* the width, or number of columns, of the dataset
* the height, or number of rows, of the dataset
* a count of the dataset bands
* the data type of the dataset
* a coordinate reference system identifier or description
* an affine transformation matrix, and
* a "nodata" value

In this example the coordinate reference system will be "+proj=latlong", which
describes an equirectangular coordinate reference system with units of decimal
degrees. The appropriate affine transformation matrix can be computed using
a function in the ``rasterio.transform`` module.

.. code-block:: pycon

   >>> from rasterio.transform import from_origin
   >>> res = (x[-1] - x[0]) / 240.0
   >>> transform = from_origin(x[0] - res / 2, y[-1] + res / 2, res, res)
   >>> transform
   Affine(0.033333333333333333, 0.0, -4.0166666666666666,
          0.0, -0.033333333333333333, 3.0166666666666666)

The upper left point in the example grid is at 3 degrees west and 2 degrees
north. The raster pixel centered on this grid point extends ``res / 2``, or
1/60 degrees, in each direction, hence the shift in the expression above.

A dataset for storing the example grid is opened like so

.. code-block:: pycon

    >>> new_dataset = rasterio.open('/tmp/new.tif', 'w', driver='GTiff',
    ...                             height=Z.shape[0], width=Z.shape[1],
    ...                             count=1, dtype=Z.dtype,
    ...                             crs='+proj=latlong', transform=transform)

Values for the `height`, `width`, and `dtype` keyword arguments are taken
directly from properties of the grid, ``Z``. Not all raster formats can support
the 64-bit float values in ``Z``, but the GeoTIFF format can.

Saving raster data
------------------

To save the grid, call the new dataset's ``write()`` method with the grid and
target band number as arguments.

.. code-block:: pycon

    >>> new_dataset.write(Z, 1)

and then call the ``close()`` method to sync data to disk and finish.

.. code-block:: pycon

    >>> new_dataset.close()

Because Rasterio's dataset objects implement Python's context manager protocol,
it is possible to do the following instead.

.. code-block:: python

    with rasterio.open('/tmp/new.tif', 'w', driver='GTiff', height=Z.shape[0],
                       width=Z.shape[1], count=1, dtype=Z.dtype,
                       crs='+proj=latlong', transform=transform) as dst:
        dst.write(Z, 1)

These are the basics of reading and writing raster data files. More features
and examples are contained in the `advanced topics <advanced>`__ section.

.. [#] "example.tif" is an alias for band 4 of Landsat scene LC80370342016194LGN00.
