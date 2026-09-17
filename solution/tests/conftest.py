"""Test setup for importing the local solution package without installing it."""

import sys
from pathlib import Path

# The solution is not installed as a package, so this lets pytest find src/data_pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
