"""parallel.py

Operate on a raster dataset window-by-window using a pool of parallel
processes.

This example isn't the most efficient way to copy a small image, but
does illustrate a pattern that becomes efficient for large images
when the work done in the ``process_window()`` function is intensive.
"""

from multiprocessing import Pool

import rasterio

# Using a rasterio window, copy from source to destination.
# Returns None on success or returns the input on failure
# so that they can be re-tried.
#
# GDAL IO and Runtime errors occur in practice, so we
# catch those and signal that the window should be re-tried.
def process_window(args):
    infile, outfile, ji, window = args
    try:
        with rasterio.open(outfile, 'r+') as dst:
            with rasterio.open(infile) as src:
                bands = [(k, src.read_band(k, window=window)) 
                            for k in src.indexes]
                for k, arr in bands:
                    dst.write_band(k, arr, window=window)
    except (IOError, RuntimeError):
        return ji, window

def main(infile, outfile, num_workers=4, max_iterations=3):

    with rasterio.open(infile) as src:
        meta = src.meta
        
        # We want an destination image with the same blocksize as
        # the source.
        block_shapes = set(src.block_shapes)
        assert len(block_shapes) == 1
        block_height, block_width = block_shapes.pop()
        meta.update(blockxsize=block_width, blockysize=block_height)
        
        # Create an empty destination file on disk.
        with rasterio.open(outfile, 'w', **meta) as dst:
            pass
        
        # Make a list of windows to process.
        with rasterio.open(outfile) as dst:
            block_shapes = set(dst.block_shapes)
            assert len(block_shapes) == 1
            windows = list(dst.block_windows(1))

    # Make a pool of worker processes and task them, retrying if there
    # are failed windows.
    p = Pool(num_workers)
    for i in range(max_iterations):
        if len(windows) > 0:
            windows = filter(None, 
                    p.imap_unordered(
                        process_window, 
                        ((infile, outfile, ij, window) 
                            for ij, window in windows), 
                        chunksize=10))
            print len(windows)
    if len(windows) > 0:
        raise ValueError(
            "Maximum iterations reached with %d jobs remaining" % len(windows))
        return 1
    else:
        return 0

if __name__ == '__main__':
    import subprocess
    
    infile = 'rasterio/tests/data/RGB.byte.tif'
    outfile = '/tmp/multiprocessed-RGB.byte.tif'
    main(infile, outfile)
    subprocess.call(['open', outfile])

