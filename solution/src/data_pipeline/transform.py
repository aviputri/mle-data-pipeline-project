"""Transform raw Green Taxi trip data into daily revenue outputs."""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pandas as pd

from .config import PROCESSED_DIR

PICKUP_DATETIME_COLUMN = "lpep_pickup_datetime"
FALLBACK_REVENUE_COLUMNS = (
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "congestion_surcharge",
    "airport_fee",
    "ehail_fee",
)


@dataclass(frozen=True)
class PipelineOutputs:
    """Paths written by one successful pipeline run."""

    daily_revenue_csv: Path
    daily_revenue_parquet: Path
    metadata_json: Path


def _build_revenue_series(frame: pd.DataFrame) -> pd.Series:
    """Return one revenue value per trip from the columns available in the data."""
    if "total_amount" in frame.columns:
        return pd.to_numeric(frame["total_amount"], errors="coerce")

    # Some taxi datasets expose fare components instead of total_amount.
    # Summing the components keeps the pipeline useful for those file variants.
    component_columns = [
        column for column in FALLBACK_REVENUE_COLUMNS if column in frame.columns
    ]
    if not component_columns:
        raise ValueError(
            "Could not determine a revenue column. Expected 'total_amount' or known fare components."
        )

    revenue = pd.Series(0.0, index=frame.index, dtype="float64")
    for column in component_columns:
        revenue = revenue.add(
            pd.to_numeric(frame[column], errors="coerce").fillna(0.0),
            fill_value=0.0,
        )

    return revenue


def prepare_trip_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep only valid pickup dates and revenue values needed for aggregation."""
    if PICKUP_DATETIME_COLUMN not in frame.columns:
        raise ValueError(f"Missing expected column: {PICKUP_DATETIME_COLUMN}")

    prepared = frame.copy()
    prepared[PICKUP_DATETIME_COLUMN] = pd.to_datetime(
        prepared[PICKUP_DATETIME_COLUMN],
        errors="coerce",
    )
    prepared = prepared.dropna(subset=[PICKUP_DATETIME_COLUMN])

    # Normalizing timestamps to midnight lets us group all trips by calendar day.
    prepared["service_date"] = prepared[PICKUP_DATETIME_COLUMN].dt.normalize()
    prepared["revenue_amount"] = _build_revenue_series(prepared)
    prepared = prepared.dropna(subset=["revenue_amount"])

    return prepared[["service_date", "revenue_amount"]]


def calculate_daily_revenue(
    input_paths: Iterable[Path],
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Read Parquet files and calculate daily trip counts plus daily revenue."""
    per_file_frames: list[pd.DataFrame] = []
    input_path_list = [Path(path) for path in input_paths]

    if not input_path_list:
        raise ValueError("No input Parquet files were provided.")

    metadata_files = []
    total_rows_read = 0

    for input_path in input_path_list:
        trip_frame = pd.read_parquet(input_path)
        total_rows_read += len(trip_frame)

        prepared = prepare_trip_frame(trip_frame)
        daily_summary = prepared.groupby("service_date", as_index=False).agg(
            trip_count=("revenue_amount", "size"),
            daily_revenue=("revenue_amount", "sum"),
        )
        per_file_frames.append(daily_summary)

        metadata_files.append(
            {
                "file_name": input_path.name,
                "rows_read": len(trip_frame),
                "rows_used": len(prepared),
                "revenue_total": float(round(prepared["revenue_amount"].sum(), 2)),
            }
        )

    # Each file is summarized first, then the summaries are combined in case
    # multiple files contain trips for the same service date.
    daily_revenue = cast(
        pd.DataFrame,
        pd.concat(per_file_frames, ignore_index=True)
        .groupby("service_date", as_index=False)
        .agg(
            trip_count=("trip_count", "sum"),
            daily_revenue=("daily_revenue", "sum"),
        )
        .sort_values("service_date"),
    )
    daily_revenue["daily_revenue"] = daily_revenue["daily_revenue"].round(2)
    daily_revenue["service_date"] = daily_revenue["service_date"].dt.strftime(
        "%Y-%m-%d"
    )

    metadata: dict[str, object] = {
        "source_files": metadata_files,
        "days_in_output": len(daily_revenue),
        "rows_read": int(total_rows_read),
        "trips_in_output": int(daily_revenue["trip_count"].sum()),
        "revenue_total": float(round(daily_revenue["daily_revenue"].sum(), 2)),
    }
    return daily_revenue, metadata


def write_outputs(
    daily_revenue: pd.DataFrame,
    metadata: dict[str, object],
    output_dir: Path = PROCESSED_DIR,
) -> PipelineOutputs:
    """Write the final DataFrame and metadata to the processed data directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "daily_revenue.csv"
    parquet_path = output_dir / "daily_revenue.parquet"
    metadata_path = output_dir / "pipeline_metadata.json"

    daily_revenue.to_csv(csv_path, index=False)
    daily_revenue.to_parquet(parquet_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return PipelineOutputs(
        daily_revenue_csv=csv_path,
        daily_revenue_parquet=parquet_path,
        metadata_json=metadata_path,
    )


def run_pipeline(
    input_paths: Iterable[Path],
    output_dir: Path = PROCESSED_DIR,
) -> tuple[PipelineOutputs, dict[str, object]]:
    """Convenience function used by the CLI and Prefect flow."""
    daily_revenue, metadata = calculate_daily_revenue(input_paths)
    outputs = write_outputs(daily_revenue, metadata, output_dir)
    return outputs, metadata
