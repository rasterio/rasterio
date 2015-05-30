from click.testing import CliRunner


import rasterio
from rasterio.rio.main import main_group


def test_version():
    runner = CliRunner()
    result = runner.invoke(main_group, ['--version'])
    assert result.exit_code == 0
    assert rasterio.__version__ in result.output
