Overviews
=========

Overviews are reduced resolution versions of your dataset that can speed up
rendering when you don't need full resolution. By precomputing the upsampled
pixels, rendering can be significantly faster when zoomed out.

Overviews can be stored internally or externally, depending on the file format.


In some cases we may want to make a copy of the test data to avoid
altering the original.

.. code-block:: python

    >>> import shutil
    >>> path = shutil.copy('tests/data/RGB.byte.tif', '/tmp/RGB.byte.tif')

We must specify the zoom factors for which to build overviews. Commonly
these are exponents of 2

.. code-block:: python

    >>> factors = [2, 4, 8, 16]

To control the visual quality of the overviews, the 'nearest', 'cubic',
'average', 'mode', and 'gauss' resampling alogrithms are available. These are
available through the ``Resampling`` enum

.. code-block:: python

   >>> from rasterio.enums import Resampling

Creating overviews requires opening a dataset in ``r+`` mode, which
gives us access to update the data in place. By convention we also
add a tag in the ``rio_overview`` namespace so that readers can 
determine what resampling method was used.

.. code-block:: python

    >>> import rasterio
    >>> dst = rasterio.open(path, 'r+')
    >>> dst.build_overviews(factors, Resampling.average)
    >>> dst.update_tags(ns='rio_overview', resampling='average')
    >>> dst.close()

We can read the updated dataset and confirm that the overviews are present

.. code-block:: python

    >>> src = rasterio.open(path, 'r')
    >>> [src.overviews(i) for i in src.indexes]
    [[2, 4, 8, 16], [2, 4, 8, 16], [2, 4, 8, 16]]
    >>> src.tags(ns='rio_overview').get('resampling')
    'average'

And to leverage the overviews, we can perform a decimated read at a reduced
resolution which should allow libgdal to read directly from the overviews
rather than compute them on-the-fly.

.. code-block:: python

    >>> src.read().shape
    (3, 718, 791)
    >>> src.read(out_shape=(3, int(src.height / 4), int(src.width / 4))).shape
    (3, 179, 197)


