from rasterio.rio.main import main_group


def test_env_gdal_data(runner):
    """GDAL data directory printed without error."""
    result = runner.invoke(
        main_group,
        ["env", "--gdal-data"],
    )


def test_env_proj_data(runner):
    """PROJ data directory printed without error."""
    result = runner.invoke(
        main_group,
        ["env", "--proj-data"],
    )


def test_env_credentials(runner):
    """Credentials printed without error."""
    result = runner.invoke(
        main_group,
        ["env", "--credentials"],
    )


def test_env_formats(runner):
    """GTIFF format driver is registered."""
    result = runner.invoke(
        main_group,
        ["env", "--formats"],
    )
    assert "GTiff" in result.output
