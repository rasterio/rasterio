"""Rasterio tools module

See this RFC about Rasterio tools:
https://github.com/mapbox/rasterio/issues/1300.
"""

import json

import rasterio
from rasterio.features import dataset_features


class JSONSequenceTool(object):
    """Extracts data from a dataset file and saves a JSON sequence
    """

    def __init__(self, func):
        """Initialize tool

        Parameters
        ----------
        func : callable
            A function or other callable object that takes a dataset and
            yields JSON serializable objects.
        """
        self.func = func

    def __call__(self, src, dst, src_opts=None, dst_opts=None, config=None):
        """Execute the tool's primary function

        Parameters
        ----------
        src : str or PathLike object
            A dataset path or URL. Will be opened in "r" mode using
            src_opts.
        dst : str or Path-like object
            A path or or PathLike object. Will be opened in "w" mode.
        src_opts : mapping
            Options that will be passed to rasterio.open when opening
            src.
        dst_opts : mapping
            Options that will be passed to json.dumps when serializing
            output.
        config : mapping
            Rasterio Env options.

        Returns
        -------
        None

        Side effects
        ------------
        Writes sequences of JSON texts to the named output file.
        """
        src_opts = src_opts or {}
        dst_opts = dst_opts or {}
        config = config or {}

        with rasterio.Env(**config):
            with open(dst, 'w') as fdst, rasterio.open(src, **src_opts) as dsrc:
                for obj in self.func(dsrc):
                    fdst.write(json.dumps(obj, **dst_opts))
