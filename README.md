# DevAI

DevAI is a terminal-based AI assistant for understanding and editing a
user-selected codebase. It can list files, read and search project text, and
propose a single-file edit for human review. The assistant never runs project
commands.

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Install and run from source](#install-and-run-from-source)
- [Install the `devai` command for use from any folder](#install-the-devai-command-for-use-from-any-folder)
- [Configure Gemini](#configure-gemini)
- [Use DevAI](#use-devai)
- [Safety, privacy, and limitations](#safety-privacy-and-limitations)
- [Development and validation](#development-and-validation)
- [Project documentation](#project-documentation)

## Features

- Choose a project folder in the terminal.
- List up to 100 eligible project file paths and count them by extension.
- Read eligible UTF-8 text files up to 1 MiB.
- Search eligible UTF-8 project files with case-insensitive literal matching.
  Results include project-relative paths and line numbers, and are capped at
  100 matches.
- Reference files by project-relative path, with or without `@`, or by
  filename. When a filename is ambiguous, choose a matching path in the
  terminal. Quote paths containing spaces.
- Ask for a change to one file at a time. DevAI prepares a complete-file
  replacement and shows a unified diff. Only `y` or `yes` approves the write;
  other responses reject it. The file is checked for intervening changes
  before writing, and the result is verified afterward.
- Report common configuration, provider, filesystem, and edit failures in the
  terminal.

## Requirements

- Python 3.11 or newer.
- [`uv`](https://docs.astral.sh/uv/) for setup, source installation, and
  dependency management.
- A Google Gemini API key. Model requests are sent to Google Gemini.

## Install and run from source

Clone or download this repository and open a terminal in its project folder:

```powershell
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
uv sync --locked
```

Replace `OWNER` and `REPOSITORY` with the actual GitHub account and
repository name.

Create a `.env` file in the project folder you intend to inspect, using
`.env.example` as a template. On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux:

```sh
cp .env.example .env
```

Edit the copy and add your own key without sharing it:

```dotenv
GOOGLE_API_KEY=your_google_gemini_api_key
DEVAI_MODEL=google_genai:gemini-2.5-flash-lite
DEVAI_TEMPERATURE=0
```

Start DevAI from the repository:

```powershell
uv run python -m app.main
```

When asked, select the folder you want DevAI to inspect. The `.env` file is
loaded from the selected folder; an already-set environment variable takes
precedence over values in that file.

## Install the `devai` command for use from any folder

`uv tool install` installs DevAI into an isolated tool environment and exposes
the `devai` command on your user `PATH`. The command can then be run while your
terminal is in any directory; select the codebase to inspect when prompted.

### Install a local checkout

After cloning the repository, run this from the repository folder:

```powershell
uv tool install .
```

If the `devai` command is not found afterward, follow the PATH instructions
printed by `uv`, reopen the terminal, or run:

```powershell
uv tool update-shell
```

### Install from GitHub

Once this repository is published under your GitHub account, replace the
`OWNER` and `REPOSITORY` values with their actual names:

```powershell
uv tool install --from "git+https://github.com/OWNER/REPOSITORY.git" devai
```

This GitHub install route requires the repository to be publicly accessible
from the computer, or appropriate Git authentication for a private repository.
It cannot work until the repository has been published.

### Configure credentials for an installed command

The recommended option is a `.env` file in the **project folder you select**
when DevAI starts. Alternatively, set `GOOGLE_API_KEY` in your operating
system's environment before starting DevAI. Do not place API keys in source
code, commit them, or share them. Google may charge for API usage; check your
Gemini plan and provider terms.

The model defaults to `google_genai:gemini-2.5-flash-lite`. You can override
the selected project's default using `DEVAI_MODEL`, but the value must use the
`google_genai:<model-name>` format. `DEVAI_TEMPERATURE` must be between `0`
and `2`; the default is `0`.

### Run from another folder

For example, after installing DevAI, move to any project and start it:

```powershell
cd D:\work\sample-project
devai
```

Choose the current folder at the prompt, or choose another folder. To remove
the isolated installation:

```powershell
uv tool uninstall devai
```

## Use DevAI

After startup, type questions or requests in the terminal. Type `exit` or
`quit` to finish.

Read and explain a file:

```text
Explain @app/main.py
```

The `@` is optional. Paths with spaces should be quoted:

```text
Summarize "docs/getting started.md"
```

Search for code:

```text
Find where the application creates its agent
```

Request an edit:

```text
Update @app/main.py to print a friendly startup message
```

DevAI reads the target, prepares a complete replacement, shows the diff, and
asks for approval. Inspect the diff. Enter `y` or `yes` to apply it; entering
`n`, pressing Enter, or any other response rejects that proposal.

## Safety, privacy, and limitations

- File inspection and editing are confined to the selected project and follow
  shared path exclusions. Symbolic links and secret environment files are not
  eligible targets.
- File reads and edits are limited to UTF-8 text no larger than 1 MiB. Search
  skips binary, invalid UTF-8, and oversized files.
- File contents are sent to the configured model only when needed to answer or
  prepare an edit. Review the [security policy](docs/security.md) before using
  DevAI with private code.
- File contents are treated as untrusted data, not as instructions to the
  assistant.
- Conversation memory is in-process only and is lost when DevAI exits.
- DevAI does **not** run shell commands, scripts, tests, or other project
  commands.
- Placeholder graph modules are not part of the active request flow.

## Development and validation

Install runtime and development dependencies:

```powershell
uv sync --locked --all-groups
```

Run tests, lint, and a package build:

```powershell
uv run pytest
uv run ruff check .
uv build
```

Tests use temporary projects and fake model behavior. They do not require a
live Gemini API key. GitHub Actions runs tests and builds distributions on
Windows and Ubuntu with Python 3.11 and 3.13.

## Project documentation

- [Architecture and request flow](docs/architecture.md)
- [Development setup and conventions](docs/development.md)
- [Security and data-handling policy](docs/security.md)
- [Troubleshooting common issues](docs/troubleshooting.md)
- [Release checklist and current release blockers](docs/release.md)

The project is versioned as `0.1.0`. A public release also requires publishing
the repository under its final GitHub URL and choosing a software license.
