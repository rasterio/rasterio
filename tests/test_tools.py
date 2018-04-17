from functools import partial

from rasterio.features import dataset_features
from rasterio.tools import JSONSequenceTool


def test_dataset_features(tmpdir):
    """JSON sequence tool works with dataset_features"""
    tool = JSONSequenceTool(partial(dataset_features, bidx=1, as_mask=True))

    tool("tests/data/RGB.byte.tif", str(tmpdir.join("footprint.jsons")))

    assert tmpdir.join("footprint.jsons").read().find("Feature") == 10
