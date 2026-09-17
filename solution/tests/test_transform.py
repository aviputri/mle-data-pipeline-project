"""Tests for the revenue transformation logic."""

from pathlib import Path

import pandas as pd
from data_pipeline.transform import calculate_daily_revenue


def test_calculate_daily_revenue_uses_total_amount(tmp_path: Path) -> None:
    """Use total_amount directly when the source file includes it."""
    january_path = tmp_path / "green_tripdata_2025-01.parquet"
    pd.DataFrame(
        {
            "lpep_pickup_datetime": [
                "2025-01-01 08:00:00",
                "2025-01-01 09:30:00",
                "2025-01-02 14:00:00",
            ],
            "total_amount": [10.5, 4.5, 15.0],
        }
    ).to_parquet(january_path, index=False)

    daily_revenue, metadata = calculate_daily_revenue([january_path])

    assert daily_revenue.to_dict(orient="records") == [
        {"service_date": "2025-01-01", "trip_count": 2, "daily_revenue": 15.0},
        {"service_date": "2025-01-02", "trip_count": 1, "daily_revenue": 15.0},
    ]
    assert metadata["rows_read"] == 3
    assert metadata["trips_in_output"] == 3
    assert metadata["revenue_total"] == 30.0


def test_calculate_daily_revenue_falls_back_to_component_columns(
    tmp_path: Path,
) -> None:
    """Sum fare components when total_amount is not available."""
    february_path = tmp_path / "green_tripdata_2025-02.parquet"
    pd.DataFrame(
        {
            "lpep_pickup_datetime": ["2025-02-01 08:00:00", "2025-02-01 10:00:00"],
            "fare_amount": [8.0, 12.0],
            "tip_amount": [2.0, 3.0],
            "tolls_amount": [0.0, 1.5],
        }
    ).to_parquet(february_path, index=False)

    daily_revenue, metadata = calculate_daily_revenue([february_path])

    assert daily_revenue.to_dict(orient="records") == [
        {"service_date": "2025-02-01", "trip_count": 2, "daily_revenue": 26.5}
    ]
    assert metadata["revenue_total"] == 26.5
