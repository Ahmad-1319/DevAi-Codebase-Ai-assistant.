"""Search eligible project text files for a literal text query."""

import os
from pathlib import Path

from langchain.tools import ToolRuntime, tool

from app.core.context import ProjectContext
from app.services.codebase import IGNORED_DIRECTORIES, is_ignored_file_name

MAX_SEARCH_FILE_SIZE_BYTES = 1_048_576
MAX_SEARCH_RESULTS = 100
MAX_MATCH_LINE_LENGTH = 240


def search_code(project_root: Path, query: str) -> list[str]:
    """Return bounded, case-insensitive literal matches with file and line."""
    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a project folder: {root}")

    normalized_query = query.casefold()
    results: list[str] = []

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

        for file_name in sorted(file_names):
            if is_ignored_file_name(file_name):
                continue

            file_path = current_path / file_name
            if file_path.is_symlink():
                continue

            with file_path.open("rb") as file:
                content = file.read(MAX_SEARCH_FILE_SIZE_BYTES + 1)

            if len(content) > MAX_SEARCH_FILE_SIZE_BYTES or b"\0" in content:
                continue

            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                continue

            relative_path = file_path.relative_to(root).as_posix()
            for line_number, line in enumerate(text.splitlines(), start=1):
                if normalized_query not in line.casefold():
                    continue

                preview = line.strip()
                if len(preview) > MAX_MATCH_LINE_LENGTH:
                    preview = preview[: MAX_MATCH_LINE_LENGTH - 3] + "..."
                results.append(f"{relative_path}:{line_number}: {preview}")

                if len(results) >= MAX_SEARCH_RESULTS:
                    return results

    return results


@tool
def search_project_code(
    runtime: ToolRuntime[ProjectContext],
    query: str,
) -> str:
    """Search eligible project text files for a literal, case-insensitive query."""
    results = search_code(runtime.context.project_root, query)
    if not results:
        return (
            "No matches found in eligible UTF-8 text files. Files larger than "
            f"{MAX_SEARCH_FILE_SIZE_BYTES} bytes, binary files, and files with "
            "invalid UTF-8 are skipped."
        )

    output = [
        f"Found {len(results)} match(es):",
        *results,
    ]
    if len(results) == MAX_SEARCH_RESULTS:
        output.append(
            f"Search stopped after {MAX_SEARCH_RESULTS} matches; more may exist."
        )
    output.append(
        "Search is case-insensitive and literal. Files larger than "
        f"{MAX_SEARCH_FILE_SIZE_BYTES} bytes, binary files, and files with "
        "invalid UTF-8 are skipped."
    )
    return "\n".join(output)
