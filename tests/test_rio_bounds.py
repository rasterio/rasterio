import pytest

import rasterio
from rasterio.rio.main import main_group

def test_bounds_sequence_single(runner, basic_image_file):
    """
    --sequence option should produce a feature collection for a single image.
    """
    result = runner.invoke(main_group, ['bounds', '--sequence', basic_image_file])

    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 1

def tests_bounds_sequence_multiple(runner, basic_image_file):
    """
    --sequence option should produce a feature collection for each image passed as argument.
    """
    result = runner.invoke(main_group, ['bounds', '--sequence', basic_image_file, basic_image_file])

    assert result.output.count('"FeatureCollection"') == 2
    assert result.output.count('"Feature"') == 2

def test_bounds_no_sequence_multiple(runner, basic_image_file):
    """
    --no-sequence option should produce a single feature collection
    """
    result = runner.invoke(main_group, ['bounds', '--no-sequence', basic_image_file, basic_image_file])

    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 2
