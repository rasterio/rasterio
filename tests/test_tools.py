from functools import partial

from rasterio.features import dataset_features
from rasterio import tools


def test_dataset_features_tool(tmpdir, path_rgb_byte_tif):
    """Example tool works"""
    features_file = tmpdir.join("footprint.jsons")

    tools.dataset_features_tool(path_rgb_byte_tif, str(features_file), func_kwargs=dict(bidx=1, as_mask=True))

    assert features_file.read().count("Feature") == 9


def test_dataset_features_partial(tmpdir, path_rgb_byte_tif):
    """JSON sequence tool works with partially evaluated dataset_features"""
    features_file = tmpdir.join("footprint.jsons")
    tool = tools.JSONSequenceTool(partial(dataset_features, bidx=1, as_mask=True))

    tool(path_rgb_byte_tif, str(features_file))

    assert features_file.read().count("Feature") == 9
