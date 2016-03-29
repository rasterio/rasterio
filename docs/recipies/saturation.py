import rasterio
import numpy as np
from skimage.color import rgb2lab, lab2lch, lch2lab, lab2rgb

path = "tests/data/RGB.byte.tif"
output = "/tmp/saturation.tif"


def saturation(arr, sat):
    """Multiple saturation/chroma in LCH color space
    Input and output are 3-band RGB scaled 0 to 255
    """
    # scale image 0 to 1
    arr_norm = arr / 255.0
    # Convert colorspace
    lch = rgb2lch(arr_norm)
    # Adjust chroma, band at index=1
    lch[1] = lch[1] * sat
    # Convert colorspace and rescale
    return (lch2rgb(lch) * 255).astype('uint8')


def rgb2lch(rgb):
    """Convert RBG to LCH colorspace (via LAB)
    Input and output are in (bands, cols, rows) order
    """
    # reshape for skimage (bands, cols, rows) -> (cols, rows, bands)
    srgb = np.swapaxes(rgb, 0, 2)
    # convert colorspace
    lch = lab2lch(rgb2lab(srgb))
    # return in (bands, cols, rows) order
    return np.swapaxes(lch, 2, 0)


def lch2rgb(lch):
    """Convert LCH to RGB colorspace (via LAB)
    Input and output are in (bands, cols, rows) order
    """
    # reshape for skimage (bands, cols, rows) -> (cols, rows, bands)
    slch = np.swapaxes(lch, 0, 2)
    # convert colorspace
    rgb = lab2rgb(lch2lab(slch))
    # return in (bands, cols, rows) order
    return np.swapaxes(rgb, 2, 0)


with rasterio.open(path) as src:
    array = src.read()
    profile = src.profile

# Increase color saturation by 60%
array_sat = saturation(array, 1.6)

with rasterio.open(output, 'w', **profile) as dst:
    dst.write(array_sat)
