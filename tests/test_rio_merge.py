import sys
import os
import logging
import click
import numpy
from click.testing import CliRunner
from pytest import fixture

import rasterio
from rasterio.rio.merge import merge


logging.basicConfig(stream=sys.stderr, level=logging.INFO)


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir_1(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": (-114, 0.2, 0, 46, 0, -0.1),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }

    with rasterio.drivers():

        with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
            data = numpy.ones((10, 10), dtype=rasterio.uint8)
            data[0:6, 0:6] = 255
            dst.write_band(1, data)

        with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
            data = numpy.ones((10, 10), dtype=rasterio.uint8)
            data[4:8, 4:8] = 254
            dst.write_band(1, data)

    return tmpdir


@fixture(scope='function')
def test_data_dir_2(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": (-114, 0.2, 0, 46, 0, -0.1),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10
        # these files have undefined nodata.
    }

    with rasterio.drivers():

        with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.uint8)
            data[0:6, 0:6] = 255
            dst.write_band(1, data)

        with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.uint8)
            data[4:8, 4:8] = 254
            dst.write_band(1, data)

    return tmpdir


def test_merge_with_nodata(test_data_dir_1):
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(merge, inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read_band(1, masked=False)
        expected = numpy.ones((10, 10), dtype=rasterio.uint8)
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert numpy.all(data == expected)


def test_merge_without_nodata(test_data_dir_2):
    outputname = str(test_data_dir_2.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_2.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(merge, inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read_band(1, masked=False)
        expected = numpy.zeros((10, 10), dtype=rasterio.uint8)
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert numpy.all(data == expected)


def test_merge_output_exists(tmpdir):
    outputname = str(tmpdir.join('merged.tif'))
    runner = CliRunner()
    result = runner.invoke(
        merge,
        ['tests/data/RGB.byte.tif', outputname])
    assert result.exit_code == 0
    result = runner.invoke(
        merge,
        ['tests/data/RGB.byte.tif', outputname])
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_merge_output_exists_without_nodata(test_data_dir_2):
    runner = CliRunner()
    result = runner.invoke(
        merge,
        [str(test_data_dir_2.join('a.tif')),
            str(test_data_dir_2.join('b.tif'))])
    assert result.exit_code == 0


def test_merge_err():
    runner = CliRunner()
    result = runner.invoke(
        merge,
        ['tests'])
    assert result.exit_code == 1


def test_format_jpeg(tmpdir):
    outputname = str(tmpdir.join('stacked.jpg'))
    runner = CliRunner()
    result = runner.invoke(
        merge,
        ['tests/data/RGB.byte.tif', outputname, '--format', 'JPEG'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
