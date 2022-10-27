"""Zarr storage"""

from collections.abc import MutableMapping
import json
import logging
from pathlib import Path

import numpy
from rasterio.windows import Window

log = logging.getLogger(__name__)


class RasterioStore(MutableMapping):
    def __init__(self, dataset):
        self.dataset = dataset
        chunk_height, chunk_width = self.dataset.block_shapes[0]
        self._data = {
            ".zgroup": json.dumps({"zarr_format": 2}).encode("utf-8"),
            Path(self.dataset.name).name
            + "/.zarray": json.dumps(
                {
                    "zarr_format": 2,
                    "shape": (
                        self.dataset.count,
                        self.dataset.height,
                        self.dataset.width,
                    ),
                    "chunks": (
                        1,
                        chunk_height,
                        chunk_width,
                    ),
                    "dtype": numpy.dtype(self.dataset.dtypes[0]).str,
                    "compressor": None,
                    "fill_value": None,
                    "order": "C",
                    "filters": None,
                }
            ).encode("utf-8"),
            Path(self.dataset.name).name + "/.zattrs": json.dumps({}),
        }

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        elif key.startswith(Path(self.dataset.name).name):
            chunk_height, chunk_width = self.dataset.block_shapes[0]
            chunking = key.split("/")[-1]
            bc, rc, cc = [int(x) for x in chunking.split(".")]
            chunk = self.dataset.read(
                bc + 1,
                window=Window(
                    cc * chunk_width, rc * chunk_height, chunk_width, chunk_height
                ),
                boundless=True,
            )
            return chunk
        else:
            raise KeyError("Key not found")

    def __setitem__(self, key, val):
        pass

    def __delitem__(self, key, val):
        pass

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)
