"""Build a star-schema dimensional model on top of the raw green_taxi table,
then compute and save revenue reports.

Refactored from setup/03_data_modeling.ipynb.
"""

from pathlib import Path

import click
import pandas as pd
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Engine


def check_source_table(engine: Engine, source_table: str) -> None:
    """Fail fast if the raw source table hasn't been loaded yet."""
    inspector = inspect(engine)
    if not inspector.has_table(source_table):
        raise RuntimeError(
            f"The {source_table} table was not found. "
            "Run data_load.py first, then run this script again."
        )

    source_count = pd.read_sql(
        text(f"SELECT COUNT(*) AS trip_count FROM {source_table}"), engine
    )
    click.echo(
        f"Prerequisite check passed: {source_table} contains "
        f"{int(source_count.loc[0, 'trip_count']):,} rows."
    )


def create_staging_view(engine: Engine, source_table: str, view_name: str) -> None:
    """Create (or refresh) the cleaned staging view on top of the raw table."""
    create_stage_view_sql = text(
        f"""
        CREATE OR REPLACE VIEW {view_name} AS
        SELECT
            "VendorID" AS vendor_key,
            CASE
                WHEN "RatecodeID" IS NULL THEN NULL
                ELSE "RatecodeID"::INTEGER
            END AS rate_code_key,
            payment_type AS payment_type_key,
            "PULocationID" AS pickup_location_key,
            "DOLocationID" AS dropoff_location_key,
            lpep_pickup_datetime AS pickup_at,
            lpep_dropoff_datetime AS dropoff_at,
            DATE(lpep_pickup_datetime) AS pickup_date,
            DATE(lpep_dropoff_datetime) AS dropoff_date,
            store_and_fwd_flag,
            passenger_count,
            trip_distance,
            fare_amount,
            extra AS extra_amount,
            mta_tax,
            tip_amount,
            tolls_amount,
            ehail_fee,
            improvement_surcharge,
            trip_type,
            congestion_surcharge,
            cbd_congestion_fee,
            total_amount,
            EXTRACT(EPOCH FROM (lpep_dropoff_datetime - lpep_pickup_datetime)) / 60.0
                AS trip_duration_minutes
        FROM {source_table}
        """
    )

    with engine.begin() as connection:
        connection.execute(create_stage_view_sql)

    click.echo(f"Created or refreshed {view_name}.")


def clean_staging_view(engine: Engine, view_name: str) -> None:
    """Fix known NULLs in the staging view: unknown payment_type becomes 0."""
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                UPDATE {view_name}
                SET payment_type_key = 0
                WHERE payment_type_key IS NULL
                """
            )
        )
    click.echo(f"Cleaned NULL payment_type_key values in {view_name}.")


def define_schema() -> MetaData:
    """Define the star schema: five dimension tables plus one fact table."""
    metadata = MetaData()

    dim_date = Table(
        "dim_date",
        metadata,
        Column("date_key", Integer, primary_key=True),
        Column("full_date", Date, nullable=False, unique=True),
        Column("year", Integer, nullable=False),
        Column("quarter", Integer, nullable=False),
        Column("month", Integer, nullable=False),
        Column("month_name", String(20), nullable=False),
        Column("day", Integer, nullable=False),
        Column("day_of_week", Integer, nullable=False),
        Column("day_name", String(20), nullable=False),
        Column("is_weekend", Boolean, nullable=False),
    )

    Table(
        "dim_vendor",
        metadata,
        Column("vendor_key", Integer, primary_key=True),
        Column("vendor_name", String(50), nullable=False),
    )

    Table(
        "dim_rate_code",
        metadata,
        Column("rate_code_key", Integer, primary_key=True),
        Column("rate_code_name", String(50), nullable=False),
    )

    Table(
        "dim_payment_type",
        metadata,
        Column("payment_type_key", Integer, primary_key=True),
        Column("payment_type_name", String(50), nullable=False),
    )

    Table(
        "dim_location",
        metadata,
        Column("location_key", Integer, primary_key=True),
        Column("location_name", String(50), nullable=False),
    )

    Table(
        "fact_trip",
        metadata,
        Column("trip_key", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "vendor_key", Integer, ForeignKey("dim_vendor.vendor_key"), nullable=False
        ),
        Column(
            "rate_code_key",
            Integer,
            ForeignKey("dim_rate_code.rate_code_key"),
            nullable=True,
        ),
        Column(
            "payment_type_key",
            Integer,
            ForeignKey("dim_payment_type.payment_type_key"),
            nullable=False,
        ),
        Column(
            "pickup_location_key",
            Integer,
            ForeignKey("dim_location.location_key"),
            nullable=False,
        ),
        Column(
            "dropoff_location_key",
            Integer,
            ForeignKey("dim_location.location_key"),
            nullable=False,
        ),
        Column(
            "pickup_date_key", Integer, ForeignKey("dim_date.date_key"), nullable=False
        ),
        Column(
            "dropoff_date_key", Integer, ForeignKey("dim_date.date_key"), nullable=False
        ),
        Column("pickup_at", DateTime, nullable=False),
        Column("dropoff_at", DateTime, nullable=False),
        Column("store_and_fwd_flag", String(1), nullable=True),
        Column("passenger_count", Float, nullable=True),
        Column("trip_distance", Float, nullable=True),
        Column("fare_amount", Float, nullable=True),
        Column("extra_amount", Float, nullable=True),
        Column("mta_tax", Float, nullable=True),
        Column("tip_amount", Float, nullable=True),
        Column("tolls_amount", Float, nullable=True),
        Column("ehail_fee", Float, nullable=True),
        Column("improvement_surcharge", Float, nullable=True),
        Column("congestion_surcharge", Float, nullable=True),
        Column("cbd_congestion_fee", Float, nullable=True),
        Column("total_amount", Float, nullable=True),
        Column("trip_type", Integer, nullable=True),
        Column("trip_duration_minutes", Float, nullable=True),
    )

    return metadata


def create_tables(engine: Engine, metadata: MetaData) -> None:
    """Drop and recreate every table defined in `metadata`."""
    with engine.begin() as connection:
        metadata.drop_all(connection, checkfirst=True)
        metadata.create_all(connection)
    click.echo(f"Created {', '.join(metadata.tables.keys())}.")


def build_date_dimension(engine: Engine, view_name: str) -> pd.DataFrame:
    """Build one row per calendar date spanning every pickup/dropoff date in the data."""
    date_bounds = pd.read_sql(
        text(
            f"""
            SELECT
                LEAST(MIN(pickup_date), MIN(dropoff_date)) AS min_date,
                GREATEST(MAX(pickup_date), MAX(dropoff_date)) AS max_date
            FROM {view_name}
            """
        ),
        engine,
    )

    min_date = pd.to_datetime(date_bounds.loc[0, "min_date"])
    max_date = pd.to_datetime(date_bounds.loc[0, "max_date"])
    all_dates = pd.date_range(min_date, max_date, freq="D")

    date_dim_df = pd.DataFrame({"full_date": all_dates})
    date_dim_df["date_key"] = date_dim_df["full_date"].dt.strftime("%Y%m%d").astype(int)
    date_dim_df["year"] = date_dim_df["full_date"].dt.year
    date_dim_df["quarter"] = date_dim_df["full_date"].dt.quarter
    date_dim_df["month"] = date_dim_df["full_date"].dt.month
    date_dim_df["month_name"] = date_dim_df["full_date"].dt.strftime("%B")
    date_dim_df["day"] = date_dim_df["full_date"].dt.day
    date_dim_df["day_of_week"] = date_dim_df["full_date"].dt.dayofweek
    date_dim_df["day_name"] = date_dim_df["full_date"].dt.strftime("%A")
    date_dim_df["is_weekend"] = date_dim_df["day_of_week"].isin([5, 6])
    date_dim_df["full_date"] = date_dim_df["full_date"].dt.date

    click.echo(f"Built date_dim_df with {len(date_dim_df):,} rows.")
    return date_dim_df


def build_code_dimensions(engine: Engine, view_name: str) -> dict[str, pd.DataFrame]:
    """Build the small code-lookup dimensions from distinct values in the staging view."""
    dim_vendor_df = pd.read_sql(
        text(f"SELECT DISTINCT vendor_key FROM {view_name} ORDER BY 1"), engine
    )
    dim_vendor_df["vendor_name"] = dim_vendor_df["vendor_key"].map(
        lambda value: f"Vendor {int(value)}"
    )

    dim_rate_code_df = pd.read_sql(
        text(
            f"SELECT DISTINCT rate_code_key FROM {view_name} "
            "WHERE rate_code_key IS NOT NULL ORDER BY 1"
        ),
        engine,
    )
    dim_rate_code_df["rate_code_name"] = dim_rate_code_df["rate_code_key"].map(
        lambda value: f"Rate code {int(value)}"
    )

    dim_payment_type_df = pd.read_sql(
        text(f"SELECT DISTINCT payment_type_key FROM {view_name} ORDER BY 1"), engine
    )
    dim_payment_type_df["payment_type_name"] = dim_payment_type_df[
        "payment_type_key"
    ].map(lambda value: f"Payment type {int(value)}")

    dim_location_df = pd.read_sql(
        text(
            f"""
            SELECT DISTINCT location_key
            FROM (
                SELECT pickup_location_key AS location_key FROM {view_name}
                UNION
                SELECT dropoff_location_key AS location_key FROM {view_name}
            ) AS locations
            ORDER BY 1
            """
        ),
        engine,
    )
    dim_location_df["location_name"] = dim_location_df["location_key"].map(
        lambda value: f"Location {int(value)}"
    )

    return {
        "dim_vendor": dim_vendor_df,
        "dim_rate_code": dim_rate_code_df,
        "dim_payment_type": dim_payment_type_df,
        "dim_location": dim_location_df,
    }


def load_dimensions(
    engine: Engine, date_dim_df: pd.DataFrame, code_dims: dict[str, pd.DataFrame]
) -> None:
    """Append every dimension DataFrame into its matching table."""
    date_dim_df.to_sql("dim_date", engine, if_exists="append", index=False)
    for table_name, dim_df in code_dims.items():
        dim_df.to_sql(table_name, engine, if_exists="append", index=False)

    dimension_counts = pd.DataFrame(
        {
            "table_name": ["dim_date", *code_dims.keys()],
            "row_count": [len(date_dim_df), *(len(df) for df in code_dims.values())],
        }
    )
    click.echo("Loaded dimension tables:")
    click.echo(dimension_counts.to_string(index=False))


def load_fact_table(engine: Engine, view_name: str) -> int:
    """Populate fact_trip from the staging view, mapping dates to dim_date's surrogate keys."""
    fact_insert_sql = text(
        f"""
        INSERT INTO fact_trip (
            vendor_key,
            rate_code_key,
            payment_type_key,
            pickup_location_key,
            dropoff_location_key,
            pickup_date_key,
            dropoff_date_key,
            pickup_at,
            dropoff_at,
            store_and_fwd_flag,
            passenger_count,
            trip_distance,
            fare_amount,
            extra_amount,
            mta_tax,
            tip_amount,
            tolls_amount,
            ehail_fee,
            improvement_surcharge,
            congestion_surcharge,
            cbd_congestion_fee,
            total_amount,
            trip_type,
            trip_duration_minutes
        )
        SELECT
            vendor_key,
            rate_code_key,
            payment_type_key,
            pickup_location_key,
            dropoff_location_key,
            CAST(TO_CHAR(pickup_date, 'YYYYMMDD') AS INTEGER) AS pickup_date_key,
            CAST(TO_CHAR(dropoff_date, 'YYYYMMDD') AS INTEGER) AS dropoff_date_key,
            pickup_at,
            dropoff_at,
            store_and_fwd_flag,
            passenger_count,
            trip_distance,
            fare_amount,
            extra_amount,
            mta_tax,
            tip_amount,
            tolls_amount,
            ehail_fee,
            improvement_surcharge,
            congestion_surcharge,
            cbd_congestion_fee,
            total_amount,
            trip_type,
            trip_duration_minutes
        FROM {view_name}
        """
    )

    with engine.begin() as connection:
        connection.execute(fact_insert_sql)

    fact_row_count = pd.read_sql(
        text("SELECT COUNT(*) AS row_count FROM fact_trip"), engine
    )
    row_count = int(fact_row_count.loc[0, "row_count"])
    click.echo(f"fact_trip loaded with {row_count:,} rows.")
    return row_count


def validate_model(engine: Engine, source_table: str) -> None:
    """Confirm fact_trip has exactly as many rows as the raw source table."""
    validation_counts = pd.read_sql(
        text(
            f"""
            SELECT '{source_table}' AS table_name, COUNT(*) AS row_count
                FROM {source_table}
            UNION ALL
            SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM dim_date
            UNION ALL
            SELECT 'dim_vendor' AS table_name, COUNT(*) AS row_count FROM dim_vendor
            UNION ALL
            SELECT 'dim_rate_code' AS table_name, COUNT(*) AS row_count
                FROM dim_rate_code
            UNION ALL
            SELECT 'dim_payment_type' AS table_name, COUNT(*) AS row_count
                FROM dim_payment_type
            UNION ALL
            SELECT 'dim_location' AS table_name, COUNT(*) AS row_count FROM dim_location
            UNION ALL
            SELECT 'fact_trip' AS table_name, COUNT(*) AS row_count FROM fact_trip
            ORDER BY table_name
            """
        ),
        engine,
    )
    click.echo(validation_counts.to_string(index=False))

    source_rows = int(
        validation_counts.loc[
            validation_counts["table_name"] == source_table, "row_count"
        ].iloc[0]
    )
    fact_rows = int(
        validation_counts.loc[
            validation_counts["table_name"] == "fact_trip", "row_count"
        ].iloc[0]
    )
    assert source_rows == fact_rows, (
        f"Expected fact_trip to match {source_table} ({source_rows:,}), "
        f"but found {fact_rows:,}."
    )
    click.echo(
        f"Row-count validation passed: fact_trip matches {source_table} exactly."
    )


def compute_revenue_reports(engine: Engine) -> dict[str, pd.DataFrame]:
    """Compute revenue summaries by weekday and by calendar date."""
    revenue_by_weekday = pd.read_sql(
        text(
            """
            SELECT
                d.day_name,
                COUNT(*) AS trip_count,
                ROUND(SUM(f.total_amount)::numeric, 2) AS total_revenue,
                ROUND(AVG(f.total_amount)::numeric, 2) AS avg_trip_revenue
            FROM fact_trip AS f
            JOIN dim_date AS d
                ON f.pickup_date_key = d.date_key
            GROUP BY d.day_name, d.day_of_week
            ORDER BY d.day_of_week
            """
        ),
        engine,
    )

    revenue_by_day = pd.read_sql(
        text(
            """
            SELECT
                d.full_date,
                d.day_name,
                COUNT(*) AS trip_count,
                ROUND(SUM(f.total_amount)::numeric, 2) AS total_revenue,
                ROUND(AVG(f.total_amount)::numeric, 2) AS avg_trip_revenue
            FROM fact_trip AS f
            JOIN dim_date AS d
                ON f.pickup_date_key = d.date_key
            GROUP BY d.full_date, d.day_name
            ORDER BY d.full_date
            """
        ),
        engine,
    )

    return {"revenue_by_weekday": revenue_by_weekday, "revenue_by_day": revenue_by_day}


def save_reports(reports: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Save each report DataFrame to its own Parquet file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, report_df in reports.items():
        output_path = output_dir / f"{name}.parquet"
        report_df.to_parquet(output_path, index=False)
        click.echo(f"Saved {name} ({len(report_df):,} rows) to {output_path}")


@click.command()
@click.option("--user", default="postgres", help="Postgres user name.")
@click.option("--password", default="postgres", help="Postgres password.")
@click.option("--host", default="localhost", help="Postgres host name.")
@click.option("--port", default=5432, help="Postgres port number.")
@click.option("--db", default="ny_green_taxi", help="Database name to connect to.")
@click.option("--source-table", default="green_taxi", help="Raw source table name.")
@click.option(
    "--view-name",
    default="green_taxi_clean",
    help="Name of the cleaned staging view to create.",
)
@click.option(
    "--output-dir",
    default="output",
    type=click.Path(path_type=Path),
    help="Directory to save the revenue report Parquet files into.",
)
def data_modeling(
    user: str,
    password: str,
    host: str,
    port: int,
    db: str,
    source_table: str,
    view_name: str,
    output_dir: Path,
) -> None:
    """Build the dimensional model and revenue reports on top of the raw taxi table."""
    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")

    check_source_table(engine, source_table)
    create_staging_view(engine, source_table, view_name)
    clean_staging_view(engine, view_name)

    metadata = define_schema()
    create_tables(engine, metadata)

    date_dim_df = build_date_dimension(engine, view_name)
    code_dims = build_code_dimensions(engine, view_name)
    load_dimensions(engine, date_dim_df, code_dims)

    load_fact_table(engine, view_name)
    validate_model(engine, source_table)

    reports = compute_revenue_reports(engine)
    save_reports(reports, output_dir)


if __name__ == "__main__":
    data_modeling()
