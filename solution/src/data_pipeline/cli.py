"""Command-line interface for running the reference pipeline from scripts."""

from pathlib import Path

import click

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_MONTHS,
    PROCESSED_DIR,
    RAW_DIR,
    build_dataset_filename,
)
from .download import download_months
from .transform import run_pipeline


def parse_months(raw_months: str | None) -> list[str]:
    """Turn a comma-separated month string into the list used by the pipeline."""
    if not raw_months:
        return list(DEFAULT_MONTHS)
    return [month.strip() for month in raw_months.split(",") if month.strip()]


def collect_input_paths(raw_dir: Path, months: list[str]) -> list[Path]:
    """Build the expected local file paths and fail early if any are missing."""
    paths = [raw_dir / build_dataset_filename(month) for month in months]
    missing_paths = [path for path in paths if not path.exists()]
    if missing_paths:
        missing_text = ", ".join(path.name for path in missing_paths)
        raise FileNotFoundError(
            f"Missing expected input files in {raw_dir}: {missing_text}. Run the download step first."
        )
    return paths


def handle_download(
    raw_dir: Path, months: list[str], base_url: str, force: bool
) -> int:
    """Run the download step and print one line per source file."""
    results = download_months(months, raw_dir, base_url=base_url, force=force)
    for result in results:
        action = "downloaded" if result.downloaded else "reused"
        click.echo(f"{action}: {result.destination}")
    return 0


def handle_run(raw_dir: Path, output_dir: Path, months: list[str]) -> int:
    """Run the transformation step and print the generated output paths."""
    input_paths = collect_input_paths(raw_dir, months)
    outputs, metadata = run_pipeline(input_paths, output_dir)
    click.echo(f"wrote: {outputs.daily_revenue_csv}")
    click.echo(f"wrote: {outputs.daily_revenue_parquet}")
    click.echo(f"wrote: {outputs.metadata_json}")
    click.echo(
        "summary:"
        f" days={metadata['days_in_output']}"
        f", trips={metadata['trips_in_output']}"
        f", revenue_total={metadata['revenue_total']}"
    )
    return 0


@click.group()
def cli() -> None:
    """Local-first reference solution for the NYC Green Taxi pipeline project."""


@cli.command()
@click.option("--months", help="Comma-separated list like 2025-01,2025-02,2025-03.")
@click.option(
    "--raw-dir",
    default=str(RAW_DIR),
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
)
@click.option("--base-url", default=DEFAULT_BASE_URL, show_default=True)
@click.option(
    "--force", is_flag=True, help="Download files even when they already exist."
)
def download(months: str | None, raw_dir: Path, base_url: str, force: bool) -> None:
    """Download the source Parquet files."""
    handle_download(raw_dir, parse_months(months), base_url, force)


@cli.command("run")
@click.option("--months", help="Comma-separated list like 2025-01,2025-02,2025-03.")
@click.option(
    "--raw-dir",
    default=str(RAW_DIR),
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    default=str(PROCESSED_DIR),
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
)
def run_command(months: str | None, raw_dir: Path, output_dir: Path) -> None:
    """Transform raw Parquet files into daily revenue outputs."""
    handle_run(raw_dir, output_dir, parse_months(months))


@cli.command("all")
@click.option("--months", help="Comma-separated list like 2025-01,2025-02,2025-03.")
@click.option(
    "--raw-dir",
    default=str(RAW_DIR),
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    default=str(PROCESSED_DIR),
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
)
@click.option("--base-url", default=DEFAULT_BASE_URL, show_default=True)
@click.option(
    "--force", is_flag=True, help="Download files even when they already exist."
)
def all_command(
    months: str | None,
    raw_dir: Path,
    output_dir: Path,
    base_url: str,
    force: bool,
) -> None:
    """Run download and transformation in sequence."""
    selected_months = parse_months(months)
    handle_download(raw_dir, selected_months, base_url, force)
    handle_run(raw_dir, output_dir, selected_months)


def main(argv: list[str] | None = None) -> int:
    """Entry point used by the small scripts in solution/scripts."""
    cli.main(args=argv, prog_name="data-pipeline", standalone_mode=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
