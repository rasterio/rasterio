import json
import logging
import sys

from click.testing import CliRunner

import rasterio
from rasterio.rio.edit import edit


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_edit_nodata(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--nodata', '255'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.nodata == 255.0


def test_edit_crs_epsg(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--crs', 'EPSG:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_proj4(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--crs', '+init=epsg:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_obj(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        edit, [inputfile, '--crs', '{"init": "epsg:32618"}'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_transform_affine(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    input_t = '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'
    result = runner.invoke(edit, [inputfile, '--transform', input_t])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        for a, b in zip(src.affine, json.loads(input_t)):
            assert round(a, 6) == round(b, 6)


def test_edit_transform_gdal(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    input_t = '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'
    result = runner.invoke(edit, [
        inputfile,
        '--transform', '[101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        for a, b in zip(src.affine, json.loads(input_t)):
            assert round(a, 6) == round(b, 6)


def test_edit_tags(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [
        inputfile, '--tag', 'lol=1', '--tag', 'wut=2'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.tags()['lol'] == '1'
        assert src.tags()['wut'] == '2'
