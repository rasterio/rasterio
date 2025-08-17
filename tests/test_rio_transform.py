import subprocess

def test_transform_with_subprocess():
    input_coords = b"[-78.0, 23.0]\n"
    expected_output = "[192457.13, 2546667.68]"

    proc = subprocess.run(
        ["rio", "transform", "--dst-crs=EPSG:32618", "--precision=2"],
        input=input_coords,
        capture_output=True
    )

    output = proc.stdout.decode("utf-8").strip()
    assert proc.returncode == 0, f"CLI exited with code {proc.returncode}"
    assert output == expected_output, f"Unexpected output: {repr(output)}"
