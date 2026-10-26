"""Codebase-level operations used by the assistant."""

import os
import stat
from pathlib import Path

from app.core.exceptions import FileTooLargeError, NonTextFileError

MAX_PROJECT_FILE_SIZE_BYTES = 1_048_576

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
}


def is_ignored_file_name(file_name: str) -> bool:
    """Return whether a file name is excluded from project inspection."""
    if file_name == ".env":
        return True

    if file_name.startswith(".env.") and file_name != ".env.example":
        return True

    return file_name.endswith(".pyc")


def resolve_project_file(project_root: Path, requested_path: Path | str) -> Path:
    """Resolve an existing, eligible regular file inside ``project_root``."""
    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a project folder: {root}")

    requested = Path(requested_path).expanduser()
    if requested.is_absolute():
        try:
            relative_path = requested.relative_to(root)
        except ValueError as error:
            raise PermissionError(
                "The requested file must be inside the selected project folder."
            ) from error
    else:
        relative_path = requested

    if not relative_path.parts or any(part == ".." for part in relative_path.parts):
        raise PermissionError(
            "The requested file must be inside the selected project folder."
        )

    if any(part.casefold() in IGNORED_DIRECTORIES for part in relative_path.parts[:-1]):
        raise PermissionError("Files in excluded project folders cannot be inspected.")

    if is_ignored_file_name(relative_path.name):
        raise PermissionError("This file is excluded from project inspection.")

    candidate = root / relative_path
    current_path = root
    for part in relative_path.parts:
        current_path /= part
        if current_path.is_symlink():
            raise PermissionError("Symbolic links cannot be inspected.")

    resolved_path = candidate.resolve(strict=True)
    try:
        resolved_path.relative_to(root)
    except ValueError as error:
        raise PermissionError(
            "The requested file must be inside the selected project folder."
        ) from error

    if not stat.S_ISREG(resolved_path.stat().st_mode):
        raise IsADirectoryError(f"Not a regular file: {resolved_path}")

    return resolved_path


def read_project_text_file(resolved_path: Path) -> str:
    """Read bounded UTF-8 text from a previously validated project file."""
    with resolved_path.open("rb") as file:
        content = file.read(MAX_PROJECT_FILE_SIZE_BYTES + 1)

    if len(content) > MAX_PROJECT_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File exceeds the {MAX_PROJECT_FILE_SIZE_BYTES}-byte reading limit."
        )

    if b"\0" in content:
        raise NonTextFileError("Binary files cannot be read as text.")

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise NonTextFileError("File is not valid UTF-8 text.") from error


def find_project_files_by_name(project_root: Path, file_name: str) -> list[str]:
    """Return eligible project-relative paths matching a file name."""
    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a project folder: {root}")

    if Path(file_name).name != file_name or not file_name:
        raise ValueError("A file name without directory components is required.")

    matches: list[str] = []

    def raise_walk_error(error: OSError) -> None:
        raise error

    for current_folder, folder_names, file_names in os.walk(
        root,
        topdown=True,
        onerror=raise_walk_error,
        followlinks=False,
    ):
        current_path = Path(current_folder)
        folder_names[:] = sorted(
            folder_name
            for folder_name in folder_names
            if folder_name.casefold() not in IGNORED_DIRECTORIES
            and not (current_path / folder_name).is_symlink()
        )

        for candidate_name in file_names:
            if (
                candidate_name.casefold() == file_name.casefold()
                and not is_ignored_file_name(candidate_name)
            ):
                candidate = current_path / candidate_name
                if not candidate.is_symlink() and candidate.is_file():
                    matches.append(candidate.relative_to(root).as_posix())

    return sorted(matches)
