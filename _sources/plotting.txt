Plotting
********

.. todo::

    * alt color ramps
    * labeling axes with coordinates 
    * multiplots
    * RGB 
   
    
.. code-block:: python

    
    >>> import rasterio
    >>> from matplotlib import pyplot
    >>> src = rasterio.open("tests/data/RGB.byte.tif")
    >>> pyplot.imshow(src.read(1), cmap='pink')
    <matplotlib.image.AxesImage object at 0x...>
    >>> pyplot.show()  # doctest: +SKIP


.. image:: http://farm6.staticflickr.com/5032/13938576006_b99b23271b_o_d.png
