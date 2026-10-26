
# Development guide

## Set up

Open a terminal in the project folder and use the project's virtual
environment. With `uv`, synchronize dependencies with:

```powershell
uv sync
```

Use `uv sync --locked --all-groups` in CI to require the checked-in lockfile
and install development tools.

Select `.venv\Scripts\python.exe` as the Python interpreter in VS Code.

## Run

From the project folder:

```powershell
uv run python -m app.main
```

For a globally available `devai` command, install the project as a uv tool:

```powershell
uv tool install .
```

The console command can then start from any working directory and prompt for
the project to inspect. Configure the API key in the selected project's `.env`
file or in the operating-system environment. See the [README](../README.md)
for local and GitHub installation instructions.

## Work on the project

- Read the module docstrings and `TODO` notes before adding behavior.
- Keep terminal input/output in `app/cli/`.
- Keep codebase operations in `app/tools/` or `app/services/`.
- Add small tests under `tests/unit/` and multi-module tests under
  `tests/integration/`.
- Never commit `.env` or put real API keys in documentation or source code.
- Read [`security.md`](security.md) before adding tools that access project
  files, apply edits, or execute commands.

## Run quality checks

Run the automated tests, linter, and distribution build from the project root:

```powershell
uv run pytest
uv run ruff check .
uv build
```

Tests use temporary files and fakes where possible; they should not require a
live model provider or API key.
