import sys
import logging

from click.testing import CliRunner

import rasterio
from rasterio.rio.calc import calc


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_multiply(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '0.10*{1} + 125', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        data = src.read()
        assert data.min() == 125
