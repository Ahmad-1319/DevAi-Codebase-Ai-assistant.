
"""Run an explicitly selected command in a project directory."""

from pathlib import Path


def run_command(command: list[str], working_directory: Path) -> str:
    """Run ``command`` and return its output.

    TODO: Add timeouts, capture errors, and restrict which commands may run.
    Never pass untrusted user text to a shell as a command.
    """
    raise NotImplementedError("Add guarded command execution here.")
