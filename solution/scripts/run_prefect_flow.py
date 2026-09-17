"""Run the optional Prefect version of the same local pipeline."""

import sys
from pathlib import Path

# The solution is not installed as a package, so this lets Python find src/data_pipeline.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_pipeline.prefect_flow import green_taxi_local_pipeline

if __name__ == "__main__":
    try:
        green_taxi_local_pipeline()
    except RuntimeError as error:
        if "Prefect could not reach the configured API" in str(error):
            raise SystemExit(str(error)) from None
        raise
