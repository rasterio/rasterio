from pkg_resources import iter_entry_points

import rasterio
from rasterio.rio.main import main_group


def test_version(runner):
    result = runner.invoke(main_group, ['--version'])
    assert result.exit_code == 0
    assert rasterio.__version__ in result.output


def test_all_registered():
    # This test makes sure that all of the subcommands defined in the
    # rasterio.rio_commands entry-point are actually registered to the main
    # cli group.
    for ep in iter_entry_points('rasterio.rio_commands'):
        assert ep.name in main_group.commands
