Tagging datasets and bands
==========================

GDAL's `data model <http://www.gdal.org/gdal_datamodel.html>`__ includes
collections of key, value pairs for major classes. In that model, these are
"metadata", but since they don't have to be just for metadata, these key, value
pairs are called "tags" in rasterio.

Reading tags
------------

I'm going to use the rasterio interactive inspector in these examples below.

.. code-block:: console

    $ rasterio.insp tests/data/RGB.byte.tif
    Rasterio 0.6 Interactive Inspector (Python 2.7.5)
    Type "src.name", "src.read_band(1)", or "help(src)" for more information.
    >>> 

Tags belong to namespaces. To get a copy of a dataset's tags from the default
namespace, just call ``tags()`` with no arguments.

.. code-block:: pycon

    >>>src.tags()
    {u'AREA_OR_POINT': u'Area'}

A dataset's bands may have tags, too. Here are the tags from the default namespace
for the first band, accessed using the positional band index argument of ``tags()``.

.. code-block:: pycon

    >>> src.tags(1)
    {u'STATISTICS_MEAN': u'29.947726688477', u'STATISTICS_MINIMUM': u'0', u'STATISTICS_MAXIMUM': u'255', u'STATISTICS_STDDEV': u'52.340921626611'}

These are the tags that came with the sample data I'm using to test rasterio. In
practice, maintaining stats in the tags can be unreliable as there is no automatic
update of the tags when the band's image data changes.

The 3 standard, non-default GDAL tag namespaces are 'SUBDATASETS', 'IMAGE_STRUCTURE', 
and 'RPC'. You can get the tags from these namespaces using the `ns` keyword of
``tags()``.

.. code-block:: pycon

    >>> src.tags(ns='IMAGE_STRUCTURE')
    {u'INTERLEAVE': u'PIXEL'}
    >>> src.tags(ns='SUBDATASETS')
    {}
    >>> src.tags(ns='RPC')
    {}

Writing tags
------------

You can add new tags to a dataset or band, in the default or another namespace,
using the ``update_tags()`` method. Unicode tag values, too, at least for TIFF
files.

.. code-block:: python
    
    import rasterio

    with rasterio.open(
            '/tmp/test.tif', 
            'w', 
            driver='GTiff', 
            count=1, 
            dtype=rasterio.uint8, 
            width=10, 
            height=10) as dst:

        dst.update_tags(a='1', b='2')
        dst.update_tags(1, c=3)
        with pytest.raises(ValueError):
            dst.update_tags(4, d=4)
        
        # True
        assert dst.tags() == {'a': '1', 'b': '2'}
        # True
        assert dst.tags(1) == {'c': '3' }
        
        dst.update_tags(ns='rasterio_testing', rus=u'другая строка')
        # True
        assert dst.tags(ns='rasterio_testing') == {'rus': u'другая строка'}

As with image data, tags aren't written to the file on disk until the dataset
is closed.

