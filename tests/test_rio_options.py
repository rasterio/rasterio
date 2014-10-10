import click
from click.testing import CliRunner


import rasterio
from rasterio.rio import rio


def test_insp():
    runner = CliRunner()
    result = runner.invoke(
        rio.cli,
        ['--version'])
    assert result.exit_code == 0
    assert result.output.strip() == rasterio.__version__
