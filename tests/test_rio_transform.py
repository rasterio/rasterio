from rasterio.rio.main import main_group


def test_transform(runner):
    """Coordinates are transformed."""
    result = runner.invoke(
        main_group,
        ["transform", "--dst-crs=EPSG:32618", "--precision=2"],
        input="[-78.0, 23.0]",
    )
    assert result.output.rstrip("\n") == "[192457.13, 2546667.68]"
