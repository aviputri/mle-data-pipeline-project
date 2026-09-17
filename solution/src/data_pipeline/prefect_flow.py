"""Optional Prefect orchestration wrapper around the local data pipeline."""

import importlib
from pathlib import Path

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_MONTHS,
    PROCESSED_DIR,
    RAW_DIR,
    build_dataset_filename,
)
from .download import download_months
from .transform import run_pipeline


def download_step(months: list[str], raw_dir: Path, base_url: str, force: bool) -> None:
    """Prefect task body for downloading all requested monthly source files."""
    download_months(months, raw_dir, base_url=base_url, force=force)


def transform_step(
    months: list[str], raw_dir: Path, output_dir: Path
) -> dict[str, object]:
    """Prefect task body for transforming local Parquet files into outputs."""
    input_paths = [raw_dir / build_dataset_filename(month) for month in months]
    _, metadata = run_pipeline(input_paths, output_dir)
    return metadata


def green_taxi_local_pipeline(
    months: list[str] | None = None,
    raw_dir: Path = RAW_DIR,
    output_dir: Path = PROCESSED_DIR,
    base_url: str = DEFAULT_BASE_URL,
    force: bool = False,
) -> dict[str, object]:
    """Build and run the optional Prefect flow."""
    try:
        # Prefect flow is optional, so the core solution works without installing it.
        prefect = importlib.import_module("prefect")
    except (
        ImportError
    ) as error:  # pragma: no cover - exercised only when Prefect is missing
        raise ImportError(
            "Prefect is not installed. Install the project dependencies with "
            "'uv sync' from the repository root."
        ) from error

    flow = prefect.flow
    task = prefect.task

    selected_months = months or list(DEFAULT_MONTHS)

    # The decorators are applied inside this function so importing the module does
    # not require Prefect to be installed.
    @task
    def download_task(
        task_months: list[str],
        task_raw_dir: Path,
        task_base_url: str,
        task_force: bool,
    ) -> None:
        download_step(task_months, task_raw_dir, task_base_url, task_force)

    @task
    def transform_task(
        task_months: list[str],
        task_raw_dir: Path,
        task_output_dir: Path,
    ) -> dict[str, object]:
        return transform_step(task_months, task_raw_dir, task_output_dir)

    @flow(name="green-taxi-local-pipeline")
    def pipeline_flow() -> dict[str, object]:
        download_task(selected_months, raw_dir, base_url, force)
        return transform_task(selected_months, raw_dir, output_dir)

    try:
        return pipeline_flow()
    except RuntimeError as error:
        if "Failed to reach API" in str(error):
            raise RuntimeError(
                "Prefect could not reach the configured API. If you stopped a previous "
                "local Prefect server, clear the stale API setting with "
                "'uv run prefect config unset PREFECT_API_URL --yes' and unset the "
                "PREFECT_API_URL environment variable before rerunning this script."
            ) from error
        raise
