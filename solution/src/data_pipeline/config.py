"""Shared configuration values for the local data pipeline solution."""

from pathlib import Path

DEFAULT_MONTHS = ("2025-01", "2025-02", "2025-03")

DEFAULT_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
DEFAULT_FILENAME_TEMPLATE = "green_tripdata_{month}.parquet"
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 60

# Resolve paths from this file so commands work from any current directory.
SOLUTION_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = SOLUTION_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def build_dataset_filename(month: str) -> str:
    """Return the expected Green Taxi Parquet filename for one month."""
    return DEFAULT_FILENAME_TEMPLATE.format(month=month)


def build_dataset_url(month: str, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the public download URL for one Green Taxi Parquet file."""
    return f"{base_url.rstrip('/')}/{build_dataset_filename(month)}"
