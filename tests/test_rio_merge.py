import sys
import os
import logging
import click
import numpy
from click.testing import CliRunner
from pytest import fixture

import rasterio
from rasterio.rio.merge import merge


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": (-114, 0.2, 0, 46, 0, -0.2),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.drivers():
        with rasterio.open(str(tmpdir.join('one.tif')), 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.uint8)
            data[0:6, 0:6] = 255
            dst.write_band(1, data)

        with rasterio.open(str(tmpdir.join('two.tif')), 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.uint8)
            data[4:8, 4:8] = 254
            dst.write_band(1, data)

    return tmpdir


def test_merge(test_data_dir):
    outputname = str(test_data_dir.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir.listdir()]
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


def test_merge_warn(test_data_dir):
    outputname = str(test_data_dir.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(merge, inputs + [outputname] + ['-n', '-1'])
    assert result.exit_code == 0
    assert "using the --nodata option for better results" in result.output


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


# Non-coincident datasets test fixture.
# Two overlapping GeoTIFFs, one to the NW and one to the SE.
@fixture(scope='function')
def test_data_dir_overlapping(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": (-114, 0.2, 0, 46, 0, -0.2),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.drivers():
        with rasterio.open(str(tmpdir.join('nw.tif')), 'w', **kwargs) as dst:
            data = numpy.ones((10, 10), dtype=rasterio.uint8)
            dst.write_band(1, data)

        kwargs['transform'] = (-113, 0.2, 0, 45, 0, -0.2)
        with rasterio.open(str(tmpdir.join('se.tif')), 'w', **kwargs) as dst:
            data = numpy.ones((10, 10), dtype=rasterio.uint8) * 2
            dst.write_band(1, data)

    return tmpdir


def test_merge_overlapping(test_data_dir_overlapping):
    outputname = str(test_data_dir_overlapping.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_overlapping.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(merge, inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        assert out.shape == (15, 15)
        assert out.bounds == (-114, 43, -111, 46)
        data = out.read_band(1, masked=False)
        expected = numpy.zeros((15, 15), dtype=rasterio.uint8)
        expected[0:10, 0:10] = 1
        expected[5:, 5:] = 2
        assert numpy.all(data == expected)


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir_float(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": (-114, 0.2, 0, 46, 0, -0.2),
        "count": 1,
        "dtype": rasterio.float64,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.drivers():
        with rasterio.open(str(tmpdir.join('one.tif')), 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.float64)
            data[0:6, 0:6] = 255
            dst.write_band(1, data)

        with rasterio.open(str(tmpdir.join('two.tif')), 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.float64)
            data[4:8, 4:8] = 254
            dst.write_band(1, data)
    return tmpdir


def test_merge_float(test_data_dir_float):
    outputname = str(test_data_dir_float.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_float.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(merge, inputs + [outputname] + ['-n', '-1.5'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read_band(1, masked=False)
        expected = numpy.ones((10, 10), dtype=rasterio.float64) * -1.5
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert numpy.all(data == expected)
