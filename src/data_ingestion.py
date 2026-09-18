from pathlib import Path
from time import time
from urllib.request import urlretrieve

import click
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text


def download_file(url: str, file_path: Path) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        click.echo(f"Reusing existing Parquet file at {file_path}")
        return file_path

    click.echo(f"Downloading Parquet data from {url}")
    urlretrieve(url, file_path)
    click.echo(f"Saved Parquet file to {file_path}")
    return file_path


def load_parquet_to_postgres(
    file_path: Path, engine, table_name: str, batch_size: int = 100_000
) -> int:
    parquet_file = pq.ParquetFile(file_path)
    total_rows = parquet_file.metadata.num_rows

    first_batch = next(parquet_file.iter_batches(batch_size=1_000))
    first_batch.to_pandas().head(0).to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
    )
    click.echo(f"Created or replaced table '{table_name}'")

    loaded_rows = 0
    parquet_file = pq.ParquetFile(file_path)

    for batch_number, batch in enumerate(
        parquet_file.iter_batches(batch_size=batch_size), start=1
    ):
        start_time = time()
        batch_df = batch.to_pandas()
        batch_df.to_sql(table_name, engine, if_exists="append", index=False)
        loaded_rows += len(batch_df)
        elapsed = time() - start_time
        click.echo(
            f"Loaded batch {batch_number}: {len(batch_df):,} rows "
            f"in {elapsed:.2f}s ({loaded_rows:,}/{total_rows:,} rows total)"
        )

    with engine.connect() as connection:
        db_rows = connection.execute(
            text(f'SELECT COUNT(*) FROM "{table_name}"')
        ).scalar_one()

    click.echo(f"Finished loading {loaded_rows:,} rows into '{table_name}'")
    click.echo(f"Database row count: {db_rows:,}")
    return db_rows


@click.command()
@click.option("--user", default="postgres", help="Postgres user name.")
@click.option("--password", default="postgres", help="Postgres password.")
@click.option("--host", default="localhost", help="Postgres host name.")
@click.option("--port", default=5432, help="Postgres port number.")
@click.option("--table_name", default="yellow_taxi", help="Table name to write to.")
@click.option("--url", help="URL to download Parquet file from.")
@click.option("--file_path", help="Path to save Parquet file to.")
@click.option("--db", default="ny_taxi", help="Database name to write to.")
def data_ingestion(table_name, url, file_path, user, password, host, port, db):
    """Download a Parquet file and load it into PostgreSQL in chunks."""

    if not url:
        raise click.UsageError("--url is required")

    if not file_path:
        raise click.UsageError("--file_path is required")

    parquet_path = download_file(url, Path(file_path))
    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    load_parquet_to_postgres(parquet_path, engine, table_name)


if __name__ == "__main__":
    data_ingestion()
