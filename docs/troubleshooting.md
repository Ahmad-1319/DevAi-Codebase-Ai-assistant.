# Troubleshooting

Run commands from a terminal. Do not share API keys, `.env` files, or private
source code when asking for help.

## `devai` is not recognized

Confirm that `uv tool install .` completed successfully. Close and reopen the
terminal so it reloads `PATH`. If needed, run:

```powershell
uv tool update-shell
```

Check that the uv tool executable directory is included in your user `PATH`.
As an alternative, run from a source checkout with `uv run python -m app.main`.

## DevAI says `GOOGLE_API_KEY` is not configured

Create `.env` in the project folder selected at startup, or set
`GOOGLE_API_KEY` in your operating-system environment. The selected project's
`.env` file is loaded after folder selection; an environment variable already
set takes precedence.

Confirm the variable name is exactly `GOOGLE_API_KEY`, and do not include
quotes around the key unless your dotenv format requires them. Never paste the
key into chat, a source file, or a GitHub issue.

## Model configuration is invalid

`DEVAI_MODEL` must use the `google_genai:<model-name>` form. If it is omitted,
the default is `google_genai:gemini-2.5-flash-lite`.
`DEVAI_TEMPERATURE` must be numeric and between `0` and `2`; the default is
`0`.

## Authentication, quota, or connection errors

- For authentication errors, verify the selected project, environment, or
  operating-system configuration contains a valid Gemini API key.
- For quota/rate-limit errors, check the Google AI account's limits and billing
  status before retrying.
- For network errors, check connectivity and retry when the provider is
  available.

DevAI does not run project commands or automatically retry a failed request.

## A file cannot be read or edited

The path must refer to an eligible regular file inside the selected project.
Configured excluded folders, symbolic links, secret environment files, binary
files, invalid UTF-8 files, and files above the 1 MiB size limit cannot be
read or edited. If a file changed after an edit proposal was created, ask
DevAI to generate a new proposal and review its diff again.

## Tests or package build fail

From the source checkout, synchronize dependencies and run the checks:

```powershell
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv build
```

For a report, include the command and relevant error text, but remove API keys,
environment values, and private source content first.
