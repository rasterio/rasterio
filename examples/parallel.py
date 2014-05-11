"""parallel.py

Operate on a raster dataset window-by-window using a pool of parallel
processes.

This example isn't the most efficient way to copy a small image, but
does illustrate a pattern that becomes efficient for large images
when the work done in the ``process_window()`` function is intensive.
"""

from multiprocessing import Pool

import rasterio

# process_window() is the function that the pool's workers will call
# with a tuple of args from the pool's queue.
def process_window(task):
    """Using a rasterio window, copy from source to destination.
    Returns None on success or returns the input task on failure so
    that the task can be re-tried.

    GDAL IO and Runtime errors occur in practice, so we catch those
    and signal that the window should be re-tried.
    """
    infile, outfile, ji, window = task
    try:
        with rasterio.open(outfile, 'r+') as dst:
            with rasterio.open(infile) as src:
                bands = [(k, src.read_band(k, window=window)) 
                            for k in src.indexes]
                for k, arr in bands:
                    dst.write_band(k, arr, window=window)
    except (IOError, RuntimeError):
        return task

def main(infile, outfile, num_workers=4, max_iterations=3):
    """Use process_window() to process a file in parallel."""
    with rasterio.open(infile) as src:
        meta = src.meta
        
        # We want a destination image with the same blocksize as the
        # source.
        block_shapes = set(src.block_shapes)
        assert len(block_shapes) == 1
        block_height, block_width = block_shapes.pop()
        meta.update(blockxsize=block_width, blockysize=block_height)
        
        if block_width != src.shape[1]:
          meta.update(tiled = 'yes')
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
    tasks = ((infile, outfile, ij, window) for ij, window in windows)
    i = 0
    while len(windows) > 0 and i < max_iterations:
        results = p.imap_unordered(process_window, tasks, chunksize=10)
        tasks = filter(None, results)
        i += 1
    
    if len(tasks) > 0:
        raise ValueError(
            "Maximum iterations reached with %d tasks remaining" % len(tasks))
        return 1
    else:
        return 0

if __name__ == '__main__':
    infile = 'rasterio/tests/data/RGB.byte.tif'
    outfile = '/tmp/multiprocessed-RGB.byte.tif'
    main(infile, outfile)

