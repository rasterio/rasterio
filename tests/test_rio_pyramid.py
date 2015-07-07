import logging
import sys

from click.testing import CliRunner

import rasterio
from rasterio.rio import pyramid


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_build(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(pyramid.pyramid, [inputfile, '--build', '2,4,8'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.overviews(1) == [2, 4, 8]
        assert src.overviews(2) == [2, 4, 8]
        assert src.overviews(3) == [2, 4, 8]


def test_build(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(pyramid.pyramid, [inputfile, '--build', '2^1..3'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.overviews(1) == [2, 4, 8]
        assert src.overviews(2) == [2, 4, 8]
        assert src.overviews(3) == [2, 4, 8]


def test_ls(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(pyramid.pyramid, [inputfile, '--ls'])
    assert result.exit_code == 0
    assert result.output == 'Band 1: \nBand 2: \nBand 3: \n'
