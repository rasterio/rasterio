#!/bin/bash

echo "1. gdal_calc.py mult: 0.95 * a"
echo "------------------------------"
time gdal_calc.py --calc "0.95*A" -A tests/data/RGB.byte.tif --allBands A --overwrite --outfile out_gdal.tif
echo ""

echo "2. rio calc mult: 0.95 * a"
echo "--------------------------"
time rio calc "(* 0.95 (read 1))" tests/data/RGB.byte.tif out_rio.tif
echo ""

echo "3. gdal_calc.py mult add: 0.95 * a + 10"
echo "---------------------------------------"
time gdal_calc.py --calc "0.95*A + 10" -A tests/data/RGB.byte.tif --allBands A --overwrite --outfile out_gdal.tif
echo ""

echo "4. rio calc mult add: 0.95 * a + 10"
echo "-----------------------------------"
time rio calc "(+ (* 0.95 (read 1)) 10)" tests/data/RGB.byte.tif out_rio.tif
echo ""
