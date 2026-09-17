"""Download the raw Green Taxi Parquet files without running the transformation."""

import sys
from pathlib import Path

# The solution is not installed as a package, so this lets Python find src/data_pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_pipeline.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["download", *sys.argv[1:]]))
