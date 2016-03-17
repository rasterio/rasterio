Writing Datasets
=================

.. todo::

    ALL THE DETAILS
    drivers
    context manager
    write 3d vs write 2d
    profile.update
    appending to existing data
    transforms
    dtypes
    block windows

Opening a file in writing mode is a little more complicated than opening
a text file in Python. The dimensions of the raster dataset, the 
data types, and the specific format must be specified.

.. code-block:: python

   >>> with rasterio.oepn

Writing data mostly works as with a Python file. There are a few format-
specific differences. TODO: details.

