"""Download NYC green taxi trip data and load it into PostgreSQL.

Refactored from setup/02_data_load.ipynb.
"""

from pathlib import Path
from time import time
from urllib.request import urlretrieve

import click
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
DEFAULT_MONTHS = ["2025-01", "2025-02", "2025-03"]


def download_files(base_url: str, months: list[str], data_dir: Path) -> list[Path]:
    """Download one green taxi Parquet file per month, skipping files that already exist."""
    data_dir.mkdir(parents=True, exist_ok=True)
    parquet_paths = []

    for month in months:
        data_url = f"{base_url}/green_tripdata_{month}.parquet"
        parquet_path = data_dir / f"green_tripdata_{month}.parquet"

        if parquet_path.exists():
            click.echo(f"Reusing existing file: {parquet_path}")
        else:
            click.echo(f"Downloading {data_url}")
            urlretrieve(data_url, parquet_path)
            click.echo(f"Saved file to {parquet_path}")

        parquet_paths.append(parquet_path)

    return parquet_paths


def combine_parquet_files(parquet_paths: list[Path]) -> pd.DataFrame:
    """Read each Parquet file into a DataFrame and concatenate them into one."""
    dfs = [pd.read_parquet(path) for path in parquet_paths]
    combined_df = pd.concat(dfs, ignore_index=True)
    click.echo(
        f"Loaded {len(combined_df):,} rows and {len(combined_df.columns)} columns "
        f"from {len(parquet_paths)} file(s)."
    )
    return combined_df


def check_connection(engine: Engine) -> None:
    """Verify the database is reachable before doing any real work."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            "Could not connect to PostgreSQL. "
            "Start the database container from 01_db_setup.md and try again."
        ) from exc
    click.echo("Database connection succeeded.")


def load_dataframe_to_postgres(
    df: pd.DataFrame,
    engine: Engine,
    table_name: str,
    clean_view_name: str,
    batch_size: int = 100_000,
) -> int:
    """Replace `table_name` with `df`'s schema, then insert `df` in batches."""
    total_rows = len(df)

    with engine.begin() as connection:
        # Drop the downstream staging view first, since it depends on this table's
        # old schema and would otherwise block replacing the table.
        connection.execute(text(f"DROP VIEW IF EXISTS {clean_view_name}"))

    # Create an empty table with the schema inferred from the DataFrame.
    df.head(0).to_sql(name=table_name, con=engine, if_exists="replace", index=False)
    click.echo(f"Created or replaced table '{table_name}'.")

    loaded_rows = 0
    for batch_number, start in enumerate(range(0, total_rows, batch_size), start=1):
        batch_start = time()
        batch_df = df.iloc[start : start + batch_size]
        batch_df.to_sql(table_name, engine, if_exists="append", index=False)
        loaded_rows += len(batch_df)
        elapsed = time() - batch_start
        click.echo(
            f"Batch {batch_number:02d}: loaded {len(batch_df):,} rows "
            f"in {elapsed:.2f}s ({loaded_rows:,}/{total_rows:,} rows total)"
        )

    click.echo("All batches processed.")
    return loaded_rows


def validate_load(engine: Engine, table_name: str, expected_rows: int) -> None:
    """Confirm the table's row count matches the source DataFrame's row count."""
    row_count_df = pd.read_sql(
        text(f'SELECT COUNT(*) AS row_count FROM "{table_name}"'), engine
    )
    loaded_row_count = int(row_count_df.loc[0, "row_count"])

    assert loaded_row_count == expected_rows, (
        f"Row count mismatch: source has {expected_rows:,} rows "
        f"but PostgreSQL has {loaded_row_count:,}."
    )
    click.echo(f"Validation passed: {loaded_row_count:,} rows loaded into {table_name}.")


@click.command()
@click.option("--user", default="postgres", help="Postgres user name.")
@click.option("--password", default="postgres", help="Postgres password.")
@click.option("--host", default="localhost", help="Postgres host name.")
@click.option("--port", default=5432, help="Postgres port number.")
@click.option("--db", default="ny_green_taxi", help="Database name to write to.")
@click.option("--table-name", default="green_taxi", help="Table name to write to.")
@click.option(
    "--clean-view-name",
    default="green_taxi_clean",
    help="Downstream staging view to drop before replacing the raw table.",
)
@click.option(
    "--base-url", default=BASE_URL, help="Base URL that Parquet files are downloaded from."
)
@click.option(
    "--month",
    "months",
    multiple=True,
    default=DEFAULT_MONTHS,
    help="Year-month (YYYY-MM) to download; pass multiple times for multiple months.",
)
@click.option(
    "--data-dir",
    default="data",
    type=click.Path(path_type=Path),
    help="Directory to download Parquet files into.",
)
@click.option("--batch-size", default=100_000, help="Rows per insert batch.")
def data_load(
    user: str,
    password: str,
    host: str,
    port: int,
    db: str,
    table_name: str,
    clean_view_name: str,
    base_url: str,
    months: tuple[str, ...],
    data_dir: Path,
    batch_size: int,
) -> None:
    """Download green taxi Parquet files and load them into PostgreSQL."""
    parquet_paths = download_files(base_url, list(months), data_dir)
    combined_df = combine_parquet_files(parquet_paths)

    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")
    check_connection(engine)

    load_dataframe_to_postgres(
        combined_df, engine, table_name, clean_view_name, batch_size
    )
    validate_load(engine, table_name, len(combined_df))


if __name__ == "__main__":
    data_load()
