# Reference Solution

This folder contains a complete local-first reference implementation for an **ETL pipeline**.

## What the solution does

1. Downloads the January, February and March 2025 Green Taxi Parquet files into `data/raw/`.
2. Reads those Parquet files locally.
3. Aggregates `total_amount` by pickup date to produce daily revenue.
4. Writes outputs to `data/processed/` as CSV, Parquet, and JSON metadata.
5. Includes an optional Prefect flow for orchestration.

The load step writes the output files into `data/processed/`, not into a database. This means there is no server to start and no connection to configure, so the focus stays on the pipeline stages themselves. Note that `data/raw/` is a staging area, not the destination.

If you want to extend the exercise and write to a database instead of the local filesystem, swap the file writes in [src/data_pipeline/transform.py](src/data_pipeline/transform.py) for a database write. The extract and transform stages stay exactly as they are.

## Project structure

| File | Description |
| --- | --- |
| [scripts/run_pipeline.py](scripts/run_pipeline.py) | Runs the full pipeline: download, transform, and write. |
| [scripts/download_data.py](scripts/download_data.py) | Downloads the raw files without running the transformation. |
| [scripts/run_prefect_flow.py](scripts/run_prefect_flow.py) | Runs the optional Prefect version of the same pipeline. |
| [src/data_pipeline/cli.py](src/data_pipeline/cli.py) | Exposes the `download`, `run` and `all` commands. |
| [src/data_pipeline/config.py](src/data_pipeline/config.py) | Holds the months, dataset URL and data directory paths. |
| [src/data_pipeline/download.py](src/data_pipeline/download.py) | Handles dataset downloads. |
| [src/data_pipeline/transform.py](src/data_pipeline/transform.py) | Calculates daily revenue and writes outputs. |
| [src/data_pipeline/prefect_flow.py](src/data_pipeline/prefect_flow.py) | Contains the optional Prefect flow. |
| [tests/test_transform.py](tests/test_transform.py) | Covers the revenue aggregation logic. |

## Run the reference solution

Run these commands from the project root, after following the Setup section in the [main README](../README.md):

```bash
uv run python solution/scripts/run_pipeline.py
uv run pytest solution/tests
```

The whole repository shares a single environment defined by the [pyproject.toml](../pyproject.toml) in the project root. `uv run` uses the exact versions locked in [uv.lock](../uv.lock) and installs them on first use, so there is no additional virtual environment to create or activate.

Outputs land in `solution/data/`, because the solution resolves its paths relative to its own source files rather than to the current directory.

## Optional Prefect flow

Prefect is part of the project environment, so the orchestration version of the same local pipeline is ready to run.

This reference solution is meant to let Prefect start a temporary local server for the run.
If you previously ran another Prefect project, an old background server or a saved `PREFECT_API_URL` can cause errors.

Use the cleanup commands below before running the flow.
If Prefect says no server is running or the setting is not set, you can continue.

`macOS` / `Linux` / `Windows Git-Bash`:

```bash
uv run prefect server stop
uv run prefect config set PREFECT_SERVER_ALLOW_EPHEMERAL_MODE=true
uv run prefect config unset PREFECT_API_URL --yes
unset PREFECT_API_URL
uv run python solution/scripts/run_prefect_flow.py
```

`Windows PowerShell`:

```powershell
uv run prefect server stop
uv run prefect config set PREFECT_SERVER_ALLOW_EPHEMERAL_MODE=true
uv run prefect config unset PREFECT_API_URL --yes
Remove-Item Env:PREFECT_API_URL -ErrorAction SilentlyContinue
uv run python solution/scripts/run_prefect_flow.py
```

The helper scripts add the local `src/` directory to `PYTHONPATH` automatically, so you do not need an editable package install.

When you are done with the optional flow, you can stop any background Prefect server with `uv run prefect server stop`.

If you intentionally want to use a dedicated Prefect server instead of the temporary server, start it first with `uv run prefect server start --background`, check it with `uv run prefect server status`, and then run the flow.

## Expected outputs

After a successful run, you should see:

- `data/raw/green_tripdata_2025-01.parquet`
- `data/raw/green_tripdata_2025-02.parquet`
- `data/raw/green_tripdata_2025-03.parquet`
- `data/processed/daily_revenue.csv`
- `data/processed/daily_revenue.parquet`
- `data/processed/pipeline_metadata.json`
