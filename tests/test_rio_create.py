"""Tests of rio create."""

import rasterio
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.rio.main import main_group


def test_create_bad_transform(runner):
    """Raise BadParameter when transform is invalid."""
    result = runner.invoke(
        main_group,
        [
            "create",
            "--transform",
            "lol",
            "test.tif",
        ],
    )
    assert result.exit_code == 2


def test_create_bad_crs(runner):
    """Raise BadParameter when CRS is invalid."""
    result = runner.invoke(
        main_group,
        [
            "create",
            "--crs",
            "lol",
            "test.tif",
        ],
    )
    assert result.exit_code == 2


def test_create_bad_nodata(runner):
    """Raise BadParameter when nodata is invalid."""
    result = runner.invoke(
        main_group,
        [
            "create",
            "--nodata",
            "lol",
            "test.tif",
        ],
    )
    assert result.exit_code == 2


def test_create_empty(tmp_path, runner):
    """Create a new empty tif."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "--format",
            "GTiff",
            "--dtype",
            "uint8",
            "--count",
            "3",
            "--height",
            "512",
            "--width",
            "256",
            "--crs",
            "EPSG:32618",
            "--transform",
            "[300.0, 0.0, 101985.0, 0.0, -300.0, 2826915.0]",
            outfile,
        ],
    )
    assert result.exit_code == 0

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.driver == "GTiff"
        assert dataset.crs == CRS.from_epsg(32618)
        assert dataset.res == (300.0, 300.0)
        assert dataset.transform.xoff == 101985.0
        assert dataset.transform.yoff == 2826915.0
        assert (dataset.read() == 0).all()


def test_create_bounds(tmp_path, runner):
    """Create a new empty tif with a bounding box."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "--format",
            "GTiff",
            "--dtype",
            "uint8",
            "--count",
            "3",
            "--height",
            "512",
            "--width",
            "256",
            "--crs",
            "EPSG:32618",
            "--bounds",
            ",".join(
                (
                    str(x)
                    for x in [
                        101985.0,
                        2826915.0 - 512 * 300.0,
                        101985.0 + 256 * 300.0,
                        2826915.0,
                    ]
                )
            ),
            outfile,
        ],
    )
    assert result.exit_code == 0

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.driver == "GTiff"
        assert dataset.crs == CRS.from_epsg(32618)
        assert dataset.res == (300.0, 300.0)
        assert dataset.transform.xoff == 101985.0
        assert dataset.transform.yoff == 2826915.0
        assert (dataset.read() == 0).all()


def test_create_override_warning(tmp_path, runner):
    """Warn if both --bounds and --transform are used."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "--format",
            "GTiff",
            "--dtype",
            "uint8",
            "--count",
            "3",
            "--height",
            "512",
            "--width",
            "256",
            "--crs",
            "EPSG:32618",
            "--transform",
            "[300.0, 0.0, 101985.0, 0.0, -300.0, 2826915.0]",
            "--bounds",
            "0,0,1,1",
            outfile,
        ],
    )
    assert result.exit_code == 0
    assert "Use only one" in result.output

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.driver == "GTiff"
        assert dataset.crs == CRS.from_epsg(32618)
        assert dataset.res == (300.0, 300.0)
        assert dataset.transform.xoff == 101985.0
        assert dataset.transform.yoff == 2826915.0
        assert (dataset.read() == 0).all()


def test_create_bounds(tmp_path, runner):
    """Create a new empty tif with a bounding box."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "--format",
            "GTiff",
            "--dtype",
            "uint8",
            "--count",
            "3",
            "--height",
            "512",
            "--width",
            "256",
            "--crs",
            "EPSG:32618",
            "--bounds",
            ",".join(
                (
                    str(x)
                    for x in [
                        101985.0,
                        2826915.0 - 512 * 300.0,
                        101985.0 + 256 * 300.0,
                        2826915.0,
                    ]
                )
            ),
            outfile,
        ],
    )
    assert result.exit_code == 0

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.driver == "GTiff"
        assert dataset.crs == CRS.from_epsg(32618)
        assert dataset.res == (300.0, 300.0)
        assert dataset.transform.xoff == 101985.0
        assert dataset.transform.yoff == 2826915.0
        assert (dataset.read() == 0).all()

def test_create_short_opts(tmp_path, runner):
    """Create a new empty tif using short options."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "-f",
            "GTiff",
            "-t",
            "uint8",
            "-n",
            "3",
            "-h",
            "512",
            "-w",
            "256",
            outfile,
        ],
    )
    assert result.exit_code == 0

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.driver == "GTiff"
        assert (dataset.read() == 0).all()


def test_create_nodata(tmp_path, runner):
    """Create a new tif with no valid data."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "-f",
            "GTiff",
            "-t",
            "uint8",
            "-n",
            "3",
            "-h",
            "512",
            "-w",
            "256",
            "--nodata",
            "255",
            outfile,
        ],
    )
    assert result.exit_code == 0

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.nodatavals == (255, 255, 255)
        assert dataset.driver == "GTiff"
        raster = dataset.read(masked=True)
        assert (raster.data == 255).all()
        assert raster.mask.all()


def test_create_creation_opts(tmp_path, runner):
    """Create a new tif with creation/opening options."""
    outfile = str(tmp_path.joinpath("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "create",
            "-f",
            "GTiff",
            "-t",
            "uint8",
            "-n",
            "3",
            "-h",
            "512",
            "-w",
            "256",
            "--co",
            "tiled=true",
            "--co",
            "blockxsize=128",
            "--co",
            "blockysize=256",
            outfile,
        ],
    )
    assert result.exit_code == 0

    with rasterio.open(outfile) as dataset:
        assert dataset.shape == (512, 256)
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")
        assert dataset.driver == "GTiff"
        assert all(((256, 128) == hw for hw in dataset.block_shapes))


def test_create_no_overwrite(tmp_path, runner):
    """Don't allow overwrite of existing file without option."""
    outpath = tmp_path.joinpath("out.tif")
    outpath.touch()
    outfile = str(outpath)

    result = runner.invoke(
        main_group,
        [
            "create",
            "-f",
            "GTiff",
            "-t",
            "uint8",
            "-n",
            "3",
            "-h",
            "512",
            "-w",
            "256",
            outfile,
        ],
    )
    assert result.exit_code == 1
    assert "File exists and won't be overwritten" in result.output


def test_create_overwrite(tmp_path, runner):
    """Allow overwrite of existing file with option."""
    outpath = tmp_path.joinpath("out.tif")
    outpath.touch()
    outfile = str(outpath)

    result = runner.invoke(
        main_group,
        [
            "create",
            "-f",
            "GTiff",
            "-t",
            "uint8",
            "-n",
            "3",
            "-h",
            "512",
            "-w",
            "256",
            "--overwrite",
            outfile,
        ],
    )
    assert result.exit_code == 0


def test_create_no_overwrite_nonfile(runner):
    """Don't allow overwrite of existing non-file without option."""
    with MemoryFile(bytes(bytearray(100000))) as memfile:
        result = runner.invoke(
            main_group,
            [
                "create",
                "-f",
                "GTiff",
                "-t",
                "uint8",
                "-n",
                "3",
                "-h",
                "512",
                "-w",
                "256",
                memfile.name,
            ],
        )
        assert result.exit_code == 1
        assert "Object exists and won't be overwritten" in result.output


def test_create_overwrite_nonfile(runner):
    """Allow overwrite of existing non-file with option."""
    with MemoryFile(bytes(bytearray(100000))) as memfile:
        result = runner.invoke(
            main_group,
            [
                "create",
                "-f",
                "GTiff",
                "-t",
                "uint8",
                "-n",
                "1",
                "-h",
                "16",
                "-w",
                "16",
                "--overwrite",
                memfile.name,
            ],
        )
        assert result.exit_code == 0

        with rasterio.open(memfile.name) as dataset:
            assert dataset.count == 1
            assert dataset.height == 16
            assert dataset.width == 16


def test_create_no_overwrite_nonfile_2(path_rgb_byte_tif, runner):
    """Don't allow overwrite of existing non-file dataset without option."""
    with open(path_rgb_byte_tif, "rb") as dataset:
        data = dataset.read()

    with MemoryFile(data) as memfile:
        result = runner.invoke(
            main_group,
            [
                "create",
                "-f",
                "GTiff",
                "-t",
                "uint8",
                "-n",
                "3",
                "-h",
                "512",
                "-w",
                "256",
                memfile.name,
            ],
        )
        assert result.exit_code == 1
        assert "Dataset exists and won't be overwritten" in result.output
        assert memfile.read(1024) == data[:1024]


def test_create_overwrite_nonfile_2(path_rgb_byte_tif, runner):
    """Allow overwrite of existing non-file dataset with option."""
    with open(path_rgb_byte_tif, "rb") as dataset:
        data = dataset.read()

    with MemoryFile(data) as memfile:
        result = runner.invoke(
            main_group,
            [
                "create",
                "-f",
                "GTiff",
                "-t",
                "uint8",
                "-n",
                "1",
                "-h",
                "512",
                "-w",
                "256",
                "--overwrite",
                memfile.name,
            ],
        )
        assert result.exit_code == 0

        with rasterio.open(memfile.name) as dataset:
            assert dataset.count == 1
            assert dataset.height == 512
            assert dataset.width == 256
