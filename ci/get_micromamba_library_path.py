"""On Windows, this script runs `micromamba.exe` from LOCALAPPDATA to find its Library path and prints it to stdout."""

import argparse
import json
import subprocess
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--name", "-n", help="Conda prefix/environment to examine", required=True
    )
    args = parser.parse_args()
    prefix_name: str = args.name
    assert isinstance(prefix_name, str)

    try:
        result = subprocess.run(
            ["micromamba", "info", "-n", prefix_name, "--json"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise FileNotFoundError("Did not find micromamba") from error
    parsed_info = json.loads(result.stdout)
    environment = Path(parsed_info["env location"])
    library_path = environment / "Library"
    if not library_path.is_dir():
        raise RuntimeError(f"{library_path} is not a directory")
    print(library_path)
