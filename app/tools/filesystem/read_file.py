"""Read bounded UTF-8 text from one eligible project file."""

from pathlib import Path

from langchain.tools import ToolRuntime, tool

from app.core.context import ProjectContext
from app.services.codebase import (
    MAX_PROJECT_FILE_SIZE_BYTES,
    read_project_text_file,
    resolve_project_file,
)

MAX_FILE_SIZE_BYTES = MAX_PROJECT_FILE_SIZE_BYTES


def read_file(project_root: Path, file_path: Path | str) -> str:
    """Read one eligible UTF-8 text file below ``project_root``.

    Files larger than ``MAX_FILE_SIZE_BYTES`` and binary or invalid UTF-8 files
    are rejected. Missing paths and filesystem access errors are raised to the
    caller.
    """
    resolved_path = resolve_project_file(project_root, file_path)
    return read_project_text_file(resolved_path)


@tool
def read_project_file(
    runtime: ToolRuntime[ProjectContext],
    file_path: str,
) -> str:
    """Read one eligible UTF-8 text file by path inside the selected project."""
    project_root = runtime.context.project_root
    resolved_path = resolve_project_file(project_root, file_path)
    content = read_project_text_file(resolved_path)
    relative_path = resolved_path.relative_to(project_root.resolve()).as_posix()
    return f"File: {relative_path}\nContent:\n{content}"
