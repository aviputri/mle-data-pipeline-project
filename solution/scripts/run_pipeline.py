"""Run the full local pipeline: download the data, transform it, and write outputs."""

import sys
from pathlib import Path

# The solution is not installed as a package, so this lets Python find src/data_pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_pipeline.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["all", *sys.argv[1:]]))
