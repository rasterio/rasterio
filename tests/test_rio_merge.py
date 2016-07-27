"""Unittests for $ rio merge"""


import sys
import os
import logging

import affine
from click.testing import CliRunner
import numpy as np
from pytest import fixture

import rasterio
from rasterio.merge import merge
from rasterio.rio.main import main_group
from rasterio.transform import Affine


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir_1(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }

    with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8)
        data[0:6, 0:6] = 255
        dst.write(data, indexes=1)

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8)
        data[4:8, 4:8] = 254
        dst.write(data, indexes=1)

    return tmpdir


@fixture(scope='function')
def test_data_dir_2(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10
        # these files have undefined nodata.
    }

    with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.uint8)
        data[0:6, 0:6] = 255
        dst.write(data, indexes=1)

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.uint8)
        data[4:8, 4:8] = 254
        dst.write(data, indexes=1)

    return tmpdir


def test_merge_with_colormap(test_data_dir_1):
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()

    # Add a colormap to the first input prior merge
    with rasterio.open(inputs[0], 'r+') as src:
        src.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 0, 0)})

    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as out:
        cmap = out.colormap(1)
        assert cmap[0] == (255, 0, 0, 255)
        assert cmap[255] == (0, 0, 0, 255)


def test_merge_with_nodata(test_data_dir_1):
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        expected = np.ones((10, 10), dtype=rasterio.uint8)
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert np.all(data == expected)


def test_merge_warn(test_data_dir_1):
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] + ['--nodata', '-1'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    assert "using the --nodata option for better results" in result.output


def test_merge_without_nodata(test_data_dir_2):
    outputname = str(test_data_dir_2.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_2.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        expected = np.zeros((10, 10), dtype=rasterio.uint8)
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert np.all(data == expected)


def test_merge_output_exists(tmpdir):
    outputname = str(tmpdir.join('merged.tif'))
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['merge', 'tests/data/RGB.byte.tif', outputname])
    assert result.exit_code == 0
    result = runner.invoke(
        main_group, ['merge', 'tests/data/RGB.byte.tif', outputname])
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_merge_output_exists_without_nodata_fails(test_data_dir_2):
    """Fails without --force-overwrite"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, [
            'merge', str(test_data_dir_2.join('a.tif')),
            str(test_data_dir_2.join('b.tif'))])
    assert result.exit_code == 1


def test_merge_output_exists_without_nodata(test_data_dir_2):
    """Succeeds with --force-overwrite"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, [
            'merge', '--force-overwrite', str(test_data_dir_2.join('a.tif')),
            str(test_data_dir_2.join('b.tif'))])
    assert result.exit_code == 0


def test_merge_err():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['merge', 'tests'])
    assert result.exit_code == 1


def test_format_jpeg(tmpdir):
    outputname = str(tmpdir.join('stacked.jpg'))
    runner = CliRunner()
    result = runner.invoke(
        main_group, [
            'merge', 'tests/data/RGB.byte.tif', outputname,
            '--format', 'JPEG'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)


# Non-coincident datasets test fixture.
# Two overlapping GeoTIFFs, one to the NW and one to the SE.
@fixture(scope='function')
def test_data_dir_overlapping(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.open(str(tmpdir.join('se.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8)
        dst.write(data, indexes=1)

    kwargs['transform'] = affine.Affine(0.2, 0, -113,
                                        0, -0.2, 45)
    with rasterio.open(str(tmpdir.join('nw.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8) * 2
        dst.write(data, indexes=1)

    return tmpdir


def test_merge_overlapping(test_data_dir_overlapping):
    outputname = str(test_data_dir_overlapping.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_overlapping.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        assert out.shape == (15, 15)
        assert out.bounds == (-114, 43, -111, 46)
        data = out.read(1, masked=False)
        expected = np.zeros((15, 15), dtype=rasterio.uint8)
        expected[0:10, 0:10] = 1
        expected[5:, 5:] = 2
        assert np.all(data == expected)


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir_float(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.float64,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.open(str(tmpdir.join('two.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.float64)
        data[0:6, 0:6] = 255
        dst.write(data, indexes=1)

    with rasterio.open(str(tmpdir.join('one.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.float64)
        data[4:8, 4:8] = 254
        dst.write(data, indexes=1)
    return tmpdir


def test_merge_float(test_data_dir_float):
    outputname = str(test_data_dir_float.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_float.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] + ['--nodata', '-1.5'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        expected = np.ones((10, 10), dtype=rasterio.float64) * -1.5
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert np.all(data == expected)


# Test below comes from issue #288. There was an off-by-one error in
# pasting image data into the canvas array.

@fixture(scope='function')
def tiffs(tmpdir):

    data = np.ones((1, 1, 1), 'uint8')

    kwargs = {
        'count': '1',
        'driver': 'GTiff',
        'dtype': 'uint8',
        'height': 1,
        'width': 1}

    kwargs['transform'] = Affine(1, 0, 1,
                                 0, -1, 1)
    with rasterio.open(str(tmpdir.join('a-sw.tif')), 'w', **kwargs) as r:
        r.write(data * 40)

    kwargs['transform'] = Affine(1, 0, 2,
                                 0, -1, 2)
    with rasterio.open(str(tmpdir.join('b-ct.tif')), 'w', **kwargs) as r:
        r.write(data * 60)

    kwargs['transform'] = Affine(2, 0, 3,
                                 0, -2, 4)
    with rasterio.open(str(tmpdir.join('c-ne.tif')), 'w', **kwargs) as r:
        r.write(data * 90)

    kwargs['transform'] = Affine(2, 0, 2,
                                 0, -2, 4)
    with rasterio.open(str(tmpdir.join('d-ne.tif')), 'w', **kwargs) as r:
        r.write(data * 120)

    return tmpdir


def test_merge_tiny(tiffs):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0

    # Output should be
    #
    # [[  0 120  90  90]
    #  [  0 120  90  90]
    #  [  0  60   0   0]
    #  [ 40   0   0   0]]

    with rasterio.open(outputname) as src:
        data = src.read()
        assert (data[0][0:2, 1] == 120).all()
        assert (data[0][0:2, 2:4] == 90).all()
        assert data[0][2][1] == 60
        assert data[0][3][0] == 40


def test_merge_tiny_output_opt(tiffs):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + ['-o', outputname])
    assert result.exit_code == 0

    # Output should be
    #
    # [[  0 120  90  90]
    #  [  0 120  90  90]
    #  [  0  60   0   0]
    #  [ 40   0   0   0]]

    with rasterio.open(outputname) as src:
        data = src.read()
        assert (data[0][0:2, 1] == 120).all()
        assert (data[0][0:2, 2:4] == 90).all()
        assert data[0][2][1] == 60
        assert data[0][3][0] == 40


def test_merge_tiny_res_bounds(tiffs):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname, '--res', 2, '--bounds', 1, 0, 5, 4])
    assert result.exit_code == 0

    # Output should be
    # [[[120  90]
    #   [ 40   0]]]

    with rasterio.open(outputname) as src:
        data = src.read()
        print(data)
        assert data[0, 0, 0] == 120
        assert data[0, 0, 1] == 90
        assert data[0, 1, 0] == 40
        assert data[0, 1, 1] == 0


def test_merge_tiny_res_high_precision(tiffs):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    runner = CliRunner()
    result = runner.invoke(
        main_group,
        ['merge'] + inputs + [outputname, '--res', 2, '--precision', 15])
    assert result.exit_code == 0

    # Output should be
    # [[[120  90]
    #   [ 40   0]]]

    with rasterio.open(outputname) as src:
        data = src.read()
        print(data)
        assert data[0, 0, 0] == 120
        assert data[0, 0, 1] == 90
        assert data[0, 1, 0] == 40
        assert data[0, 1, 1] == 0


def test_merge_rgb(tmpdir):
    """Get back original image"""
    outputname = str(tmpdir.join('merged.tif'))
    inputs = [
        'tests/data/rgb1.tif',
        'tests/data/rgb2.tif',
        'tests/data/rgb3.tif',
        'tests/data/rgb4.tif']
    runner = CliRunner()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0

    with rasterio.open(outputname) as src:
        assert [src.checksum(i) for i in src.indexes] == [25420, 29131, 37860]


def test_merge_tiny_intres(tiffs):
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    sources = [rasterio.open(x) for x in inputs]
    merge(sources, res=2)
