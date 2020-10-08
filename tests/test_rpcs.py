import rasterio
from rasterio.compat import text_type
from rasterio.rpc import RPC

TEST_RPCS = {
    'ERR_BIAS': 0.5,
    'ERR_RAND': 0.5,
    'HEIGHT_OFF': 89.0,
    'HEIGHT_SCALE': 701.0,
    'LAT_OFF': 49.2199,
    'LAT_SCALE': 0.3093,
    'LINE_DEN_COEFF': [1.0,
                        0.0009222511757408093,
                        0.0009437608823165506,
                        0.0,
                        3.227813186168402e-07,
                        0.0,
                        -1.209023819818124e-08,
                        1.847595567040099e-06,
                        5.799102000140301e-07,
                        -4.460833665210641e-07,
                        0.0,
                        0.0,
                        -6.034797295293836e-08,
                        0.0,
                        1.667569505660956e-07,
                        -2.974442475526043e-08,
                        0.0,
                        0.0,
                        0.0,
                        0.0],
    'LINE_NUM_COEFF': [0.002001303029283497,
                        -0.1860717345625879,
                        -1.127856422682348,
                        -4.632230551975493e-05,
                        0.001019881908582774,
                        5.673855447822687e-08,
                        -8.698433522294479e-08,
                        -0.00322675985508854,
                        -0.001332756784778704,
                        0.0,
                        1.215249975522747e-08,
                        -7.132377372126199e-07,
                        2.017197679474549e-06,
                        8.275158167048898e-08,
                        -1.210585983708413e-06,
                        -1.07835388717073e-06,
                        5.032973521799926e-07,
                        0.0,
                        1.716128319528072e-08,
                        0.0],
    'LINE_OFF': 5760.0,
    'LINE_SCALE': 5761.0,
    'LONG_OFF': -123.176,
    'LONG_SCALE': 0.4534,
    'SAMP_DEN_COEFF': [1.0,
                        9.278262976396983e-05,
                        0.001781926782031641,
                        -0.0006510570023623242,
                        -0.0002216055849873611,
                        9.161290674286373e-07,
                        3.126587074446549e-06,
                        0.0003565361629769621,
                        -2.582447705973245e-05,
                        -9.228544337667984e-05,
                        5.29808516621947e-07,
                        1.025006482963347e-05,
                        7.478466127324454e-07,
                        -1.692384939549647e-06,
                        -1.124443674146492e-05,
                        -1.793628425616464e-07,
                        -2.791740249303018e-07,
                        -2.820306656137878e-07,
                        4.593502012060843e-08,
                        1.035174961061441e-07],
    'SAMP_NUM_COEFF': [0.02202618393703774,
                        1.185886131197477,
                        -0.2151710781539888,
                        0.03045218075295352,
                        0.002420581655336635,
                        -4.398438360671764e-06,
                        5.871407208028941e-05,
                        -0.02166676957828599,
                        -0.0004180699044156175,
                        -2.753492566174621e-05,
                        -7.124639699900795e-06,
                        -1.101195320211651e-05,
                        -0.0001119110912711932,
                        -0.000109618465373252,
                        0.0001183590823839227,
                        1.382552349641905e-05,
                        1.997075688106731e-05,
                        2.673528192748438e-05,
                        -1.230207121465409e-06,
                        -2.830467933081173e-06],
    'SAMP_OFF': 3724.0,
    'SAMP_SCALE': 3725.0
}

def test_rpcs():
    rpcs = RPC(TEST_RPCS)
    for key, value in rpcs.items():
        assert key in TEST_RPCS.keys()
        assert value == TEST_RPCS[key]
        assert isinstance(value, (float, list))
        if isinstance(value, list):
            assert len(value) == 20
            assert isinstance(value[0], float)

def test_rpcs_extra_kwargs_filtered():
    rpcs = RPC(TEST_RPCS, abc=123)
    assert "abc" not in rpcs

def test_rpcs_to_gdal():
    rpcs = RPC(TEST_RPCS)
    for key, value in rpcs.to_gdal().items():
        assert key in TEST_RPCS.keys()
        assert isinstance(value, text_type)
        if key.endswith("COEFF"):
            for val in TEST_RPCS[key]:
                assert text_type(val) in value
        else:
            assert value == text_type(TEST_RPCS[key])

def test_rpcs_write_read_rpcs(tmpdir):
    tiffname = str(tmpdir.join('test.tif'))
    rpcs = RPC(TEST_RPCS)
    
    with rasterio.open(tiffname, 'w', driver='GTiff', dtype='uint8', count=1,
                       width=7449, height=11522, rpcs=rpcs) as dst:
        pass
        
    with rasterio.open(tiffname, 'r+') as dst:
        rpcs = dst.rpcs.copy()
        assert rpcs
        assert isinstance(rpcs, RPC)
        expected = TEST_RPCS.copy()
        # GDAL doesn't include these metadata items on write
        expected.pop('ERR_BIAS')
        expected.pop('ERR_RAND')
        assert sorted(rpcs.keys()) == sorted(expected.keys())
        
        rpcs.update(LAT_OFF=48, LONG_OFF=-123)
        dst.rpcs = rpcs
        rpcs = dst.rpcs.copy()
        assert rpcs
        assert rpcs["LAT_OFF"] == 48
        assert rpcs["LONG_OFF"] == -123
        
def test_read_vrt_rpcs(tmpdir):
    vrtfile = tmpdir.join('test.vrt')
    vrtfile.write("""
<VRTDataset rasterXSize="512" rasterYSize="512">
<Metadata domain="RPC">
    <MDI key="ERR_BIAS">5.000000000000000e-01</MDI>
    <MDI key="ERR_RAND">5.000000000000000e-01</MDI>
    <MDI key="HEIGHT_OFF">8.900000000000000e+01</MDI>
    <MDI key="HEIGHT_SCALE">7.010000000000000e+02</MDI>
    <MDI key="LAT_OFF">4.921990000000000e+01</MDI>
    <MDI key="LAT_SCALE">3.093000000000000e-01</MDI>
    <MDI key="LINE_DEN_COEFF">1.000000000000000e+00 9.222511757408093e-04 9.437608823165506e-04 0.000000000000000e+00 3.227813186168402e-07 0.000000000000000e+00 -1.209023819818124e-08 1.847595567040099e-06 5.799102000140301e-07 -4.460833665210641e-07 0.000000000000000e+00 0.000000000000000e+00 -6.034797295293836e-08 0.000000000000000e+00 1.667569505660956e-07 -2.974442475526043e-08 0.000000000000000e+00 0.000000000000000e+00 0.000000000000000e+00 0.000000000000000e+00</MDI>
    <MDI key="LINE_NUM_COEFF">2.001303029283497e-03 -1.860717345625879e-01 -1.127856422682348e+00 -4.632230551975493e-05 1.019881908582774e-03 5.673855447822687e-08 -8.698433522294479e-08 -3.226759855088540e-03 -1.332756784778704e-03 0.000000000000000e+00 1.215249975522747e-08 -7.132377372126199e-07 2.017197679474549e-06 8.275158167048898e-08 -1.210585983708413e-06 -1.078353887170730e-06 5.032973521799926e-07 0.000000000000000e+00 1.716128319528072e-08 0.000000000000000e+00</MDI>
    <MDI key="LINE_OFF">5760</MDI>
    <MDI key="LINE_SCALE">5761</MDI>
    <MDI key="LONG_OFF">-1.231760000000000e+02</MDI>
    <MDI key="LONG_SCALE">4.534000000000000e-01</MDI>
    <MDI key="SAMP_DEN_COEFF">1.000000000000000e+00 9.278262976396983e-05 1.781926782031641e-03 -6.510570023623242e-04 -2.216055849873611e-04 9.161290674286373e-07 3.126587074446549e-06 3.565361629769621e-04 -2.582447705973245e-05 -9.228544337667984e-05 5.298085166219470e-07 1.025006482963347e-05 7.478466127324454e-07 -1.692384939549647e-06 -1.124443674146492e-05 -1.793628425616464e-07 -2.791740249303018e-07 -2.820306656137878e-07 4.593502012060843e-08 1.035174961061441e-07</MDI>
    <MDI key="SAMP_NUM_COEFF">2.202618393703774e-02 1.185886131197477e+00 -2.151710781539888e-01 3.045218075295352e-02 2.420581655336635e-03 -4.398438360671764e-06 5.871407208028941e-05 -2.166676957828599e-02 -4.180699044156175e-04 -2.753492566174621e-05 -7.124639699900795e-06 -1.101195320211651e-05 -1.119110912711932e-04 -1.096184653732520e-04 1.183590823839227e-04 1.382552349641905e-05 1.997075688106731e-05 2.673528192748438e-05 -1.230207121465409e-06 -2.830467933081173e-06</MDI>
    <MDI key="SAMP_OFF">3724</MDI>
    <MDI key="SAMP_SCALE">3725</MDI>
  </Metadata>
<VRTRasterBand dataType="Byte" band="1">
    <ColorInterp>Gray</ColorInterp>
    <SimpleSource>
    <SourceFilename relativeToVRT="0">tests/data/RGB.byte.tif</SourceFilename>
    <SourceBand>1</SourceBand>
    <SrcRect xOff="0" yOff="0" xSize="512" ySize="512"/>
    <DstRect xOff="0" yOff="0" xSize="512" ySize="512"/>
    </SimpleSource>
</VRTRasterBand>
</VRTDataset>
    """)

    with rasterio.open(str(vrtfile)) as src:
        rpcs = src.rpcs
        assert rpcs
    