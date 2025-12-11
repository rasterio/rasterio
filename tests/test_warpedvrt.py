"""Tests for :py:class:`rasterio.warp.WarpedVRT`."""

import logging
import shutil

import affine
import numpy
import pytest

import rasterio
from rasterio.control import GroundControlPoint
from rasterio.crs import CRS
from rasterio.enums import Resampling, MaskFlags
from rasterio.errors import WarpOptionsError
from rasterio.io import MemoryFile
from rasterio import shutil as rio_shutil
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window

from .conftest import gdal_version, credentials

log = logging.getLogger(__name__)

DST_CRS = "EPSG:3857"


def _copy_update_profile(path_in, path_out, **kwargs):
    """Create a copy of path_in in path_out updating profile with **kwargs"""
    with rasterio.open(str(path_in)) as src:
        profile = src.profile.copy()
        profile.update(kwargs)
        with rasterio.open(str(path_out), "w", **profile) as dst:
            dst.write(src.read())
    return str(path_out)


def test_warped_vrt(path_rgb_byte_tif):
    """A VirtualVRT has the expected VRT properties."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS) as vrt:
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata == 0.0
        assert vrt.dst_nodata == 0.0
        assert vrt.tolerance == 0.125
        assert vrt.resampling == Resampling.nearest
        assert vrt.warp_extras == {"init_dest": "NO_DATA"}
        assert vrt.mask_flag_enums == ([MaskFlags.nodata],) * 3


def test_warped_vrt_nondefault_nodata(path_rgb_byte_tif):
    """A VirtualVRT has expected nondefault nodata values."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS, src_nodata=None, nodata=None) as vrt:
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata is None
        assert vrt.dst_nodata is None
        assert vrt.tolerance == 0.125
        assert vrt.resampling == Resampling.nearest
        assert vrt.warp_extras == {"init_dest": "0"}
        assert vrt.mask_flag_enums == ([MaskFlags.all_valid],) * 3


def test_warped_vrt_add_alpha(dsrec, path_rgb_byte_tif):
    """A VirtualVRT has the expected VRT properties."""
    with rasterio.Env() as env, rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(src, crs=DST_CRS, add_alpha=True) as vrt:

            records = dsrec(env)
            assert len(records) == 1
            assert "2 N GTiff" in records[0]

            assert vrt.dst_crs == CRS.from_string(DST_CRS)
            assert vrt.src_nodata == 0.0
            assert vrt.dst_nodata is None
            assert vrt.tolerance == 0.125
            assert vrt.resampling == Resampling.nearest
            assert vrt.warp_extras == {"init_dest": "NO_DATA"}
            assert vrt.count == 4
            assert vrt.mask_flag_enums == (
                [MaskFlags.per_dataset, MaskFlags.alpha],
            ) * 3 + (
                [MaskFlags.all_valid],
            )

        records = dsrec(env)
        assert len(records) == 1
        assert "1 N GTiff" in records[0]


def test_warped_vrt_msk_add_alpha(dsrec, caplog, path_rgb_msk_byte_tif):
    """Add an alpha band to the VRT to access per-dataset mask of a source"""

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="TRUE"
    ) as env, rasterio.open(
        path_rgb_msk_byte_tif
    ) as src, WarpedVRT(
        src, crs=DST_CRS, add_alpha=True
    ) as vrt:
        assert vrt.src_nodata is None
        assert vrt.dst_nodata is None
        assert vrt.count == 4
        assert vrt.mask_flag_enums == (
            [MaskFlags.per_dataset, MaskFlags.alpha],
        ) * 3 + (
            [MaskFlags.all_valid],
        )
        assert vrt.colorinterp[3] == rasterio.enums.ColorInterp.alpha

        caplog.set_level(logging.DEBUG)
        with rasterio.Env(CPL_DEBUG=True):
            masks = vrt.read_masks()

        assert masks[0, 0, 0] == 0
        assert masks[0].mean() > 0
        assert masks[3, 0, 0] == 255
        assert masks[3].mean() == 255
        assert masks.shape == (4, vrt.height, vrt.width)

        if gdal_version.at_least("3.12"):
            records = dsrec(env)
            assert len(records) == 2
            for record in records:
                if "RGB2.byte.tif.msk" in record:
                    break
            else:
                pytest.fail("Missing .msk dataset in open datasets")
        else:
            assert "RGB2.byte.tif.msk" in caplog.text


def test_warped_vrt_msk_nodata(path_rgb_msk_byte_tif):
    """Specifying dst nodata also works for source with .msk"""
    with rasterio.open(path_rgb_msk_byte_tif) as src, WarpedVRT(src, crs=DST_CRS, nodata=0.0) as vrt:
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata is None
        assert vrt.dst_nodata == 0.0
        assert vrt.count == 3
        assert vrt.mask_flag_enums == ([MaskFlags.nodata],) * 3

        masks = vrt.read_masks()
        assert masks[0, 0, 0] == 0
        assert masks[0].mean() > 0
        assert len(vrt.colorinterp) == 3


def test_warped_vrt_source(path_rgb_byte_tif):
    """A VirtualVRT has the expected source dataset."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS) as vrt:
        assert vrt.src_dataset == src


def test_warped_vrt_set_src_crs_default(path_rgb_byte_tif, tmpdir):
    """A warped VRT's dst_src defaults to the given src_crs"""
    path_crs_unset = str(tmpdir.join("rgb_byte_crs_unset.tif"))
    _copy_update_profile(path_rgb_byte_tif, path_crs_unset, crs=None)
    with rasterio.open(path_rgb_byte_tif) as src:
        original_crs = src.crs
    with rasterio.open(path_crs_unset) as src, WarpedVRT(src, src_crs=original_crs) as vrt:
        assert vrt.src_crs == original_crs
        assert vrt.dst_crs == original_crs

def test_wrap_file(path_rgb_byte_tif):
    """A VirtualVRT has the expected dataset properties."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS) as vrt:
        assert vrt.crs == CRS.from_string(DST_CRS)
        assert tuple(round(x, 1) for x in vrt.bounds) == (
            -8789636.7, 2700460.0, -8524406.4, 2943560.2
        )
        assert vrt.name.startswith("WarpedVRT(")
        assert vrt.name.endswith("RGB.byte.tif)")
        assert vrt.indexes == (1, 2, 3)
        assert vrt.nodatavals == (0, 0, 0)
        assert vrt.dtypes == ("uint8", "uint8", "uint8")
        assert vrt.read().shape == (3, 736, 803)


def test_warped_vrt_dimensions(path_rgb_byte_tif):
    """
    A WarpedVRT with target dimensions has the expected dataset
    properties.
    """
    with rasterio.open(path_rgb_byte_tif) as src:
        extent = (-20037508.34, 20037508.34)
        size = (2 ** 16) * 256
        resolution = (extent[1] - extent[0]) / size
        dst_transform = affine.Affine(
            resolution, 0.0, extent[0], 0.0, -resolution, extent[1]
        )
        with WarpedVRT(
            src, crs=DST_CRS, width=size, height=size, transform=dst_transform
        ) as vrt:
            assert vrt.dst_crs == CRS.from_string(DST_CRS)
            assert vrt.src_nodata == 0.0
            assert vrt.dst_nodata == 0.0
            assert vrt.resampling == Resampling.nearest
            assert vrt.width == size
            assert vrt.height == size
            assert vrt.transform == dst_transform
            assert vrt.warp_extras == {"init_dest": "NO_DATA"}


def test_warp_extras(path_rgb_byte_tif):
    """INIT_DEST warp extra is passed through."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS, init_dest=255) as vrt:
        rgb = vrt.read()
        assert (rgb[:, 0, 0] == 255).all()


def test_transformer_options(path_rgb_byte_tif):
    transform = affine.Affine(
        1.0003577499128138, 0.0, -8848646.496183893,
        0.0, -1.0003577499128138, 720.9022505759253,
    )
    transformer_options = {
        "SRC_METHOD": "NO_GEOTRANSFORM",
        "DST_METHOD": "NO_GEOTRANSFORM",
    }
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(
        src,
        crs=DST_CRS,
        **transformer_options,
    ) as vrt:
        for key, value in transformer_options.items():
            assert vrt.warp_extras[key] == value
            assert vrt.transform.almost_equals(transform)


def test_transformer_options__width_height(path_rgb_byte_tif):
    transform = affine.Affine(79.1, 0.0, 0.0, 0.0, -71.8, 718.0)
    transformer_options = {
        "SRC_METHOD": "NO_GEOTRANSFORM",
        "DST_METHOD": "NO_GEOTRANSFORM",
    }
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(
        src,
        crs=DST_CRS,
        width=10,
        height=10,
        **transformer_options,
    ) as vrt:
        for key, value in transformer_options.items():
            assert vrt.warp_extras[key] == value
        assert vrt.transform.almost_equals(transform)


@credentials
@pytest.mark.network
def test_wrap_s3():
    """A warp wrapper's dataset has the expected properties"""
    L8TIF = "s3://sentinel-cogs/sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A/B01.tif"
    with rasterio.open(L8TIF) as src, WarpedVRT(src, crs=DST_CRS, src_nodata=0, nodata=0) as vrt:
        assert vrt.crs == DST_CRS
        assert tuple(round(x, 1) for x in vrt.bounds) == (
            9222324.9, -14139657.4, 9730075.2, -13635650.5
        )
        assert vrt.name == f"WarpedVRT({L8TIF})"
        assert vrt.indexes == (1,)
        assert vrt.nodatavals == (0,)
        assert vrt.dtypes == ("uint16",)
        assert vrt.shape == (1885, 1899)


def test_warped_vrt_nodata_read(path_rgb_byte_tif):
    """A read from a VirtualVRT respects dst_nodata."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS, src_nodata=0) as vrt:
        data = vrt.read(1, masked=True)
        assert data.mask.any()
        mask = vrt.dataset_mask()
        assert not mask.all()


@pytest.mark.parametrize("complex", (True, False))
def test_crs_should_be_set(path_rgb_byte_tif, tmpdir, complex):

    """When ``dst_height``, ``dst_width``, and ``dst_transform`` are set
    :py:class:`rasterio.warp.WarpedVRT` calls ``GDALCreateWarpedVRT()``,
    which requires the caller to then set a projection with
    ``GDALSetProjection()``.

    Permalink to ``GDALCreateWarpedVRT()`` call:

        https://github.com/rasterio/rasterio/blob/1f759e5f67628f163ea2550d8926b91545245712/rasterio/_warp.pyx#L753

    """

    vrt_path = str(tmpdir.join("test_crs_should_be_set.vrt"))

    with rasterio.open(path_rgb_byte_tif) as src:

        dst_crs = "EPSG:4326"
        dst_height = dst_width = 10
        dst_bounds = transform_bounds(src.crs, dst_crs, *src.bounds)

        # Destination transform
        left, bottom, right, top = dst_bounds
        xres = (right - left) / dst_width
        yres = (top - bottom) / dst_height
        dst_transform = affine.Affine(xres, 0.0, left, 0.0, -yres, top)

        # The 'complex' test case hits the affected code path
        vrt_options = {"dst_crs": dst_crs}
        if complex:
            vrt_options.update(
                crs=dst_crs,
                height=dst_height,
                width=dst_width,
                transform=dst_transform,
                resampling=Resampling.nearest,
            )

        with WarpedVRT(src, **vrt_options) as vrt:
            rio_shutil.copy(vrt, vrt_path, driver="VRT")
        with rasterio.open(vrt_path) as src:
            assert src.crs


def test_boundless_read_prohibited(path_rgb_byte_tif):
    """Boundless read of a VRT is prohibited"""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src) as vrt:
        with pytest.raises(ValueError):
            vrt.read(
                boundless=True,
                window=Window(-200, -200, 1000, 1000),
                out_shape=((3, 600, 600)),
            )


def test_boundless_masks_read_prohibited(path_rgb_byte_tif):
    """Boundless masks read of a VRT is prohibited"""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src) as vrt:
        with pytest.raises(ValueError):
            vrt.read_masks(
                boundless=True,
                window=Window(-200, -200, 1000, 1000),
                out_shape=((3, 600, 600)),
            )


def test_no_add_alpha_read(path_rgb_msk_byte_tif):
    """An alpha band is not added if add_alpha=False"""
    with rasterio.open(path_rgb_msk_byte_tif) as src, WarpedVRT(
        src, add_alpha=False
    ) as vrt:
        assert vrt.count == 3


def test_image(red_green):
    """Read a red image with black background"""
    with rasterio.Env():
        with rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(
            src,
            transform=affine.Affine.translation(-src.width / 4, src.height / 4) * src.transform,
            width=2 * src.width,
            height=2 * src.height
        ) as vrt:
            data = vrt.read()
            image = numpy.moveaxis(data, 0, -1)
            assert image[31, 31, 0] == 0
            assert image[32, 32, 0] == 204
            assert image[32, 32, 1] == 17


def test_image_nodata_mask(red_green):
    """Nodata of 0 masks out the black background"""
    with rasterio.Env(), rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(
        src,
        nodata=0,
        transform=affine.Affine.translation(-src.width / 2, src.height / 2) * src.transform,
        width=3 * src.width,
        height=3 * src.height
    ) as vrt:
        masks = vrt.read_masks()
        image = numpy.moveaxis(masks, 0, -1)
        assert image[63, 63, 0] == 0
        assert image[64, 64, 0] == 255


def test_hit_ovr(red_green):
    """Zoomed out read hits the overviews"""
    # GDAL doesn't log overview hits for local files , so we copy the
    # overviews of green.tif over the red overviews and expect to find
    # green pixels below.
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="TRUE"):
        green_ovr = red_green.join("green.tif.ovr")
        shutil.move(green_ovr, red_green.join("red.tif.ovr"))
        assert not green_ovr.exists()
        with rasterio.open(str(red_green.join("red.tif.ovr"))) as ovr:
            data = ovr.read()
            assert (data[1] == 204).all()

        with rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(src) as vrt:
            data = vrt.read(out_shape=(vrt.count, vrt.height // 2, vrt.width // 2))
            image = numpy.moveaxis(data, 0, -1)
            assert image[0, 0, 0] == 17
            assert image[0, 0, 1] == 204


def test_warped_vrt_1band_add_alpha():
    """Add an alpha band to the VRT to access per-dataset mask of a source"""
    with rasterio.open('tests/data/shade.tif') as src, WarpedVRT(src, add_alpha=True) as vrt:
        assert vrt.count == 2
        assert vrt.mask_flag_enums == (
            [MaskFlags.per_dataset, MaskFlags.alpha],
            [MaskFlags.all_valid]
        )


def test_invalid_add_alpha():
    """Adding an alpha band to a VRT that already has one fails"""
    with rasterio.open('tests/data/RGBA.byte.tif') as src:
        with pytest.raises(WarpOptionsError):
            WarpedVRT(src, add_alpha=True)


def test_warpedvrt_float32_preserve(data):
    """WarpedVRT preserves float32 dtype of source"""
    with rasterio.open("tests/data/float32.tif") as src, WarpedVRT(src, src_crs="EPSG:4326") as vrt:
            assert src.dtypes == vrt.dtypes == ("float32",)


def test_warpedvrt_float32_override(data):
    """Override GDAL defaults for working data type"""
    float32file = str(data.join("float32.tif"))
    with rasterio.open(float32file, "r+") as dst:
        dst.nodata = -3.4028230607370965e+38

    with rasterio.open(float32file) as src, WarpedVRT(src, src_crs="EPSG:4326", dtype="float32") as vrt:
        assert src.dtypes == vrt.dtypes == ("float32",)


def test_warpedvrt_float32_override_nodata(data):
    """Override GDAL defaults for working data type"""
    float32file = str(data.join("float32.tif"))
    with rasterio.open(float32file, "r+") as dst:
        dst.nodata = -3.4028230607370965e+38

    with rasterio.open(float32file) as src, WarpedVRT(src, src_crs="EPSG:4326", nodata=0.0001, dtype="float32") as vrt:
        assert src.dtypes == vrt.dtypes == ("float32",)


@pytest.mark.xfail(reason="GDAL's output defaults to float64")
def test_warpedvrt_issue1744(data):
    """Reproduce the bug reported in 1744"""
    float32file = str(data.join("float32.tif"))
    with rasterio.open(float32file, "r+") as dst:
        dst.nodata = -3.4028230607370965e+38

    with rasterio.open(float32file) as src, WarpedVRT(src, src_crs="EPSG:4326") as vrt:
        assert src.dtypes == vrt.dtypes == ("float32",)


def test_open_datasets(capfd, path_rgb_byte_tif):
    """Number of open datasets is expected"""
    with rasterio.Env() as env:
        with rasterio.open(path_rgb_byte_tif) as src:
            env._dump_open_datasets()
            captured = capfd.readouterr()
            assert "1 N GTiff" in captured.err
            assert "1 S GTiff" not in captured.err

            with WarpedVRT(src):
                env._dump_open_datasets()
                captured = capfd.readouterr()
                assert "2 N GTiff" in captured.err

        env._dump_open_datasets()
        captured = capfd.readouterr()
        assert "1 N GTiff" not in captured.err


def test_warp_warp(dsrec, path_rgb_byte_tif):
    """Vincent! :P"""
    with rasterio.Env() as env:

        with rasterio.open(path_rgb_byte_tif) as src:
            # We should have one open dataset with a refcount of 1.
            records = dsrec(env)
            assert len(records) == 1
            assert "1 N GTiff" in records[0]

            with WarpedVRT(src) as vrt:
                # The VRT increments the refcount of the source by 1.
                records = dsrec(env)
                assert len(records) == 1
                assert "2 N GTiff" in records[0]

                with WarpedVRT(vrt) as vrtvrt:
                    assert vrtvrt.profile
                    # Apparently VRTs are tracked in the same way.
                    records = dsrec(env)
                    assert len(records) == 1
                    assert "2 N GTiff" in records[0]

                # Inner VRT is closed.
                records = dsrec(env)
                assert len(records) == 1
                assert "2 N GTiff" in records[0]

            # VRTs are closed, we have one open dataset.
            records = dsrec(env)
            assert len(records) == 1
            assert "1 N GTiff" in records[0]


def test_out_dtype(red_green):
    """Read as float"""
    with rasterio.Env(), rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(
        src,
        transform=affine.Affine.translation(-src.width / 4, src.height / 4) * src.transform,
        width=2 * src.width,
        height=2 * src.height
    ) as vrt:
        data = vrt.read(out_dtype="float32")
        image = numpy.moveaxis(data, 0, -1)
        assert image[31, 31, 0] == 0.0
        assert image[32, 32, 0] == 204.0
        assert image[32, 32, 1] == 17.0


def test_sample(red_green):
    """See https://github.com/rasterio/rasterio/issues/1833."""
    with rasterio.Env(), rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(
        src,
        transform=affine.Affine.translation(-src.width / 4, src.height / 4) * src.transform,
        width=2 * src.width,
        height=2 * src.height
    ) as vrt:
        sample = next(vrt.sample([(-20, -50)]))
        assert not sample.any()


@pytest.fixture
def dsrec(capfd):
    """GDAL's open dataset records as a pytest fixture"""
    def func(env):
        """Get records of GDAL's open datasets

        Parameters
        ----------
        env : Env
            A rasterio environment.

        Returns
        -------
        list of str
            Each string record represents an open dataset and tells the
            filename, the driver used to open the dataset, the reference
            count, and other information.

        """
        env._dump_open_datasets()
        captured = capfd.readouterr()
        records = captured.err.strip("\n").split("\n")[1:]
        return records
    return func


def test_warped_vrt_resizing():
    """Confirm fix of #1921"""
    with rasterio.open("tests/data/RGB.byte.tif") as rgb, WarpedVRT(rgb, height=10, width=10) as vrt:
        assert vrt.height == 10
        assert vrt.width == 10


def test_warped_vrt_resizing_repro():
    """Confirm fix of #1921"""
    with rasterio.open("tests/data/RGB.byte.tif") as rgb, WarpedVRT(rgb, crs="EPSG:3857", height=10, width=10) as vrt:
        assert vrt.height == 10
        assert vrt.width == 10



def test_vrt_src_mode(path_rgb_byte_tif):
    """VRT source dataset must be opened in read mode"""

    with rasterio.open(path_rgb_byte_tif) as src:
        profile = src.profile
        bands = src.read()

    with MemoryFile() as memfile:

        with memfile.open(**profile) as dst:
            dst.write(bands)

            with pytest.warns(FutureWarning):
                with WarpedVRT(dst, crs="EPSG:3857"):
                    pass


def test_vrt_src_kept_alive(path_rgb_byte_tif):
    """VRT source dataset is kept alive, preventing crashes"""

    with rasterio.open(path_rgb_byte_tif) as dst, WarpedVRT(dst, crs="EPSG:3857") as vrt:
        assert (vrt.read() != 0).any()

def test_vrt_mem_src_kept_alive(path_rgb_byte_tif):
    """VRT in-memory source dataset is kept alive, preventing crashes"""

    with open(path_rgb_byte_tif, "rb") as fp:
        bands = fp.read()

    with MemoryFile(bands) as memfile, memfile.open() as dst, WarpedVRT(dst, crs="EPSG:3857") as vrt:
        assert (vrt.read() != 0).any()

def test_warped_vrt_is_closed(path_rgb_byte_tif):
    """A VirtualVRT should be set as closed on exit."""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src, crs=DST_CRS) as vrt:
        assert not vrt.closed
    assert vrt.closed


def test_issue2086():
    """Create a WarpedVRT from a dataset with GCPs"""
    with rasterio.open("tests/data/white-gemini-iv.vrt") as src, WarpedVRT(src, crs=DST_CRS) as vrt:
        assert vrt.shape == (1031, 1146)



def test_gauss_no(path_rgb_byte_tif):
    """Guard against the issue reported in #2190"""
    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.raises(Exception):
            with WarpedVRT(src, resampling=Resampling.gauss):
                pass

@pytest.mark.parametrize(
    "affine_c_param",
    [
        pytest.param(
            115698.25,
            marks=pytest.mark.skipif(
                gdal_version.at_least("3.11"), reason="GDAL 3.10 and earlier used METHOD=GCP_POLYNOMIAL by default"
            ),
        ),
        pytest.param(
            115698.0,
            marks=pytest.mark.skipif(
                not gdal_version.at_least("3.11"), reason="GDAL 3.11+ uses METHOD=GCP_HOMOGRAPHY by default if 4 or 5 GCPs (https://github.com/OSGeo/gdal/pull/11949)"
            ),
        ),
    ],
)
def test_warpedvrt_gcps__width_height(affine_c_param, tmp_path):
    tiffname = tmp_path / "test.tif"
    src_gcps = [
        GroundControlPoint(row=0, col=0, x=156113, y=2818720, z=0),
        GroundControlPoint(row=0, col=800, x=338353, y=2785790, z=0),
        GroundControlPoint(row=800, col=800, x=297939, y=2618518, z=0),
        GroundControlPoint(row=800, col=0, x=115698, y=2651448, z=0),
    ]
    crs = CRS.from_epsg(32618)
    with rasterio.open(tiffname, mode='w', height=800, width=800, count=3, dtype=numpy.uint8) as source:
        source.gcps = (src_gcps, crs)

    with rasterio.open(tiffname) as src, WarpedVRT(src, width=10, height=10) as vrt:
        assert vrt.height == 10
        assert vrt.width == 10
        assert vrt.crs == crs
        assert vrt.dst_transform.almost_equals(
            affine.Affine(22271.389322449897, 0.0, affine_c_param, 0.0, -20016.05875815117, 2818720.0)
        )


def test_warpedvrt_rpcs__width_height():
    with rasterio.open('tests/data/RGB.byte.rpc.vrt') as src, WarpedVRT(src, src_crs="EPSG:4326", width=10, height=10) as vrt:
        assert vrt.height == 10
        assert vrt.width == 10
        assert vrt.crs == CRS.from_epsg(4326)
        assert vrt.dst_transform.almost_equals(
            affine.Affine(0.008598908695300157, 0.0, -123.48824818566573, 0.0, -0.0041566403046337285, 49.52797830474037)
        )


def test_warpedvrt_dst_alpha():
    """When using using Uint16 data with Alpha band we should keep the original values"""
    with rasterio.open('tests/data/RGBA.uint16.tif') as src:
        arr = src.read(1)
        assert numpy.unique(arr).tolist() == [10000]

        with WarpedVRT(src, add_alpha=False, init_dest=1) as vrt:
            vrt_arr = vrt.read(1)

            # When using WarpedVRT, the `masked` data will be initialized to the
            # `init_dest` value (1) so the unique values in the array should be
            # 1 and 10000 (the original unique value).
            assert numpy.unique(vrt_arr).tolist() == [1, 10000]
