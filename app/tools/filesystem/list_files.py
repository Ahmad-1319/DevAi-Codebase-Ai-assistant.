"""List eligible files in the project folder selected by the user."""

import os
from collections import Counter
from pathlib import Path

from langchain.tools import ToolRuntime, tool

from app.core.context import ProjectContext
from app.services.codebase import IGNORED_DIRECTORIES, is_ignored_file_name

MAX_PATHS_TO_RETURN = 100


def _raise_walk_error(error: OSError) -> None:
    raise error


def _collect_file_summary(
    project_root: Path,
) -> tuple[int, Counter[str], list[str]]:
    root = project_root.resolve(strict=True)

    if not root.is_dir():
        raise NotADirectoryError(f"Not a project folder: {root}")

    total_files = 0
    files_by_extension: Counter[str] = Counter()
    returned_paths: list[str] = []

    for current_folder, folder_names, file_names in os.walk(
        root,
        topdown=True,
        onerror=_raise_walk_error,
        followlinks=False,
    ):
        current_path = Path(current_folder)
        folder_names[:] = sorted(
            folder_name
            for folder_name in folder_names
            if folder_name.casefold() not in IGNORED_DIRECTORIES
            and not (current_path / folder_name).is_symlink()
        )

        for file_name in sorted(file_names):
            file_path = current_path / file_name

            if is_ignored_file_name(file_name) or file_path.is_symlink():
                continue

            total_files += 1
            extension = file_path.suffix.casefold() or "[no extension]"
            files_by_extension[extension] += 1

            if len(returned_paths) < MAX_PATHS_TO_RETURN:
                returned_paths.append(file_path.relative_to(root).as_posix())

    return total_files, files_by_extension, returned_paths


@tool
def list_project_files(runtime: ToolRuntime[ProjectContext]) -> str:
    """Count files and return up to 100 relative paths in the selected project."""
    root = runtime.context.project_root
    total_files, _, paths = _collect_file_summary(root)
    result = [
        f"Project folder: {root}",
        f"Total eligible files: {total_files}",
        "File paths:",
        *paths,
    ]

    if total_files > len(paths):
        result.append(f"Only the first {len(paths)} paths are shown.")

    return "\n".join(result)


@tool
def count_project_files_by_type(runtime: ToolRuntime[ProjectContext]) -> str:
    """Return eligible file counts grouped by extension."""
    root = runtime.context.project_root
    total_files, files_by_extension, _ = _collect_file_summary(root)
    result = [
        f"Project folder: {root}",
        f"Total eligible files: {total_files}",
        "Files by type:",
    ]

    if not files_by_extension:
        result.append("No eligible files were found.")
    else:
        result.extend(
            f"{extension}: {count}"
            for extension, count in sorted(
                files_by_extension.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )

    return "\n".join(result)
