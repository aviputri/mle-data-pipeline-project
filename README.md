# Data Pipeline Project

Use this repository as a **template** for your data pipeline project. You will build a pipeline that takes raw NYC taxi trip records and turns them into a processed result. The project is open-ended: the brief sets the goal, and the structure, tools, and implementation choices are yours to make. Create pull requests in your own copy even if you are working alone, and use them to track your progress.

## Learning Objectives

By the end of this repository, you should be able to:

- Write a script that downloads a public dataset into a local staging directory.
- Build a pipeline that reads staged Parquet files and aggregates them into daily metrics.
- Separate a pipeline into distinct extract, transform, and load stages.
- Explain the difference between ETL and ELT, and justify which one your pipeline uses.
- Orchestrate a pipeline with Prefect (stretch goal).

## Project Brief

In this project you are going to build a data pipeline that processes the `Green Taxi Trips` portion of the [NYC Taxi Trip dataset](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

1. Write a script that downloads the data for the first three months of 2025 and stores it in a local staging directory.
2. Write an ETL or ELT pipeline that reads the locally staged files, processes the data, and calculates revenue per day.

Bonus task, if you have time:

1. Use Prefect for workflow orchestration.

## Learning Path

### Additional Folders and Files

| File / Folder | Description |
|---|---|
| [**solution**](solution/) | A complete local ETL implementation with its own README, scripts, package, and tests. |
| [**pyproject.toml**](pyproject.toml) | Project configuration and dependencies. |
| [**uv.lock**](uv.lock) | Dependency lock file. |

## Setup

> [!NOTE]
> Throughout these steps, text in angle brackets like `<repo-name>` is a **placeholder**. Replace it, including the `< >` brackets, with your own value. For example, `cd <repo-name>` becomes `cd mle-data-pipeline-project`.

### 1. Create the Repository from the Template

Click **Use this template** on GitHub.

When creating the repository:

- Set yourself as the **Owner**
- Choose a repository name
- Disable **Include all branches**
- Click **Create repository**

> [!IMPORTANT]
> If you are working in pairs or groups, only **one person** should complete this step.

---

### 2. Add Collaborators (Pairs/Groups Only)

If working with teammates:

1. Open the repository on GitHub
2. Go to **Settings → Collaborators**
3. Add your teammates as collaborators
4. Share the repository link with your team

Teammates should accept the invitation before continuing.

---

### 3. Clone the Repository

Copy the SSH URL from the **Code** button on GitHub, then run:

```bash
git clone <copied-ssh-url>
```

The copied SSH URL will look like `git@github.com:<your-username>/<repo-name>.git`.

---

### 4. Move into the Project Folder and Install Dependencies

This installs all dependencies and creates a virtual environment in `.venv/`.

```bash
cd <repo-name>
uv sync
```

> [!TIP]
> The environment includes more than the reference solution uses. SQLAlchemy, a Postgres driver, dbt and Prefect are all installed, so you can extend the project without additional installs.

---

### 5. Open the Project in VS Code

> [!NOTE]
> Make sure you open VS Code from the project root so it automatically detects the environment created by `uv sync`.

Launch VS Code in the project root folder:

```bash
code .
```

If you create a notebook to explore the data, select the Python environment created by `uv sync` as the kernel.

## Reference Solution

This repository includes a complete local reference implementation in [solution/](solution/).
Use it to compare implementation choices and expected outputs. It is one way to solve the project, not the required structure for yours.

See [solution/README.md](solution/README.md) for how to run it and how its files fit together.

## Answer the Following Questions

1. What are the steps you took to complete the project?
2. What challenges did you face?
3. What would you do differently if you had more time?
