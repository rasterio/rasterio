import subprocess


def test_cli_bounds_obj_bbox():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --bbox --precision 6',
        shell=True)
    assert result.decode('utf-8').strip() == '[-78.898133, 23.564991, -76.599438, 25.550874]'


def test_cli_bounds_obj_bbox_mercator():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --bbox --mercator --precision 3',
        shell=True)
    assert result.decode('utf-8').strip() == '[-8782900.033, 2700489.278, -8527010.472, 2943560.235]'


def test_cli_bounds_obj_feature():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --feature --precision 6',
        shell=True)
    assert result.decode('utf-8').strip() == '{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "geometry": {"coordinates": [[[-78.898133, 23.564991], [-76.599438, 23.564991], [-76.599438, 25.550874], [-78.898133, 25.550874], [-78.898133, 23.564991]]], "type": "Polygon"}, "properties": {"id": "0", "title": "tests/data/RGB.byte.tif"}, "type": "Feature"}'


def test_cli_bounds_obj_collection():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --precision 6',
        shell=True)
    assert result.decode('utf-8').strip() == '{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "features": [{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "geometry": {"coordinates": [[[-78.898133, 23.564991], [-76.599438, 23.564991], [-76.599438, 25.550874], [-78.898133, 25.550874], [-78.898133, 23.564991]]], "type": "Polygon"}, "properties": {"id": "0", "title": "tests/data/RGB.byte.tif"}, "type": "Feature"}], "type": "FeatureCollection"}'


def test_cli_bounds_seq_feature_rs():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --x-json-seq --x-json-seq-rs --feature --precision 6',
        shell=True)
    assert result.decode('utf-8').startswith(u'\x1e')
    assert result.decode('utf-8').strip() == '{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "geometry": {"coordinates": [[[-78.898133, 23.564991], [-76.599438, 23.564991], [-76.599438, 25.550874], [-78.898133, 25.550874], [-78.898133, 23.564991]]], "type": "Polygon"}, "properties": {"id": "0", "title": "tests/data/RGB.byte.tif"}, "type": "Feature"}'


def test_cli_bounds_seq_collection():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --x-json-seq --x-json-seq-rs --precision 6',
        shell=True)
    assert result.decode('utf-8').startswith(u'\x1e')
    assert result.decode('utf-8').strip() == '{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "features": [{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "geometry": {"coordinates": [[[-78.898133, 23.564991], [-76.599438, 23.564991], [-76.599438, 25.550874], [-78.898133, 25.550874], [-78.898133, 23.564991]]], "type": "Polygon"}, "properties": {"id": "0", "title": "tests/data/RGB.byte.tif"}, "type": "Feature"}], "type": "FeatureCollection"}'


def test_cli_bounds_seq_bbox():
    result = subprocess.check_output(
        'rio bounds tests/data/RGB.byte.tif --x-json-seq --x-json-seq-rs --bbox --precision 6',
        shell=True)
    assert result.decode('utf-8').startswith(u'\x1e')
    assert result.decode('utf-8').strip() == '[-78.898133, 23.564991, -76.599438, 25.550874]'


def test_cli_bounds_seq_collection_multi(tmpdir):
    filename = str(tmpdir.join("test.json"))
    tmp = open(filename, 'w')

    subprocess.check_call(
        'rio bounds tests/data/RGB.byte.tif tests/data/RGB.byte.tif --x-json-seq --x-json-seq-rs --precision 6',
        stdout=tmp,
        shell=True)

    tmp.close()
    tmp = open(filename, 'r')
    json_texts = []
    text = ""
    for line in tmp:
        rs_idx = line.find(u'\x1e')
        if rs_idx >= 0:
            if text:
                text += line[:rs_idx]
                json_texts.append(text)
            text = line[rs_idx+1:]
        else:
            text += line
    else:
        json_texts.append(text)

    assert len(json_texts) == 2
    assert json_texts[0].strip() == '{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "features": [{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "geometry": {"coordinates": [[[-78.898133, 23.564991], [-76.599438, 23.564991], [-76.599438, 25.550874], [-78.898133, 25.550874], [-78.898133, 23.564991]]], "type": "Polygon"}, "properties": {"id": "0", "title": "tests/data/RGB.byte.tif"}, "type": "Feature"}], "type": "FeatureCollection"}'
    assert json_texts[1].strip() == '{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "features": [{"bbox": [-78.898133, 23.564991, -76.599438, 25.550874], "geometry": {"coordinates": [[[-78.898133, 23.564991], [-76.599438, 23.564991], [-76.599438, 25.550874], [-78.898133, 25.550874], [-78.898133, 23.564991]]], "type": "Polygon"}, "properties": {"id": "1", "title": "tests/data/RGB.byte.tif"}, "type": "Feature"}], "type": "FeatureCollection"}'


def test_cli_info_count():
    result = subprocess.check_output(
        'if [ `rio info tests/data/RGB.byte.tif --count` -eq 3 ]; '
        'then echo "True"; fi',
        shell=True)
    assert result.decode('utf-8').strip() == 'True'


def test_cli_info_nodata():
    result = subprocess.check_output(
        'if [ `rio info tests/data/RGB.byte.tif --nodata` = "0.0" ]; '
        'then echo "True"; fi',
        shell=True)
    assert result.decode('utf-8').strip() == 'True'


def test_cli_info_dtype():
    result = subprocess.check_output(
        'if [ `rio info tests/data/RGB.byte.tif --dtype` = "uint8" ]; '
        'then echo "True"; fi',
        shell=True)
    assert result.decode('utf-8').strip() == 'True'


def test_cli_info_shape():
    result = subprocess.check_output(
        'if [[ `rio info tests/data/RGB.byte.tif --shape` == "718 791" ]]; '
        'then echo "True"; fi',
        shell=True, executable='/bin/bash')
    assert result.decode('utf-8').strip() == 'True'
