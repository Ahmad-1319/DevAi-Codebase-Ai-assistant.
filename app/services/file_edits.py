"""Prepare reviewed file-edit proposals without modifying project files."""

import difflib
import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import FileTooLargeError, ToolExecutionError
from app.services.codebase import (
    MAX_PROJECT_FILE_SIZE_BYTES,
    read_project_text_file,
    resolve_project_file,
)


@dataclass(frozen=True)
class FileEditProposal:
    """An immutable proposed replacement and its review information."""

    file_path: str
    summary: str
    original_sha256: str
    proposed_content: str
    diff: str


def create_file_edit_proposal(
    project_root: Path,
    file_path: Path | str,
    proposed_content: str,
    summary: str,
) -> FileEditProposal:
    """Prepare a bounded diff for an eligible file without writing it."""
    resolved_path = resolve_project_file(project_root, file_path)
    original_content = read_project_text_file(resolved_path)
    proposed_bytes = proposed_content.encode("utf-8")

    if len(proposed_bytes) > MAX_PROJECT_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"Proposed content exceeds the {MAX_PROJECT_FILE_SIZE_BYTES}-byte limit."
        )
    if "\0" in proposed_content:
        raise ToolExecutionError("Proposed content cannot contain binary data.")
    if not summary.strip():
        raise ToolExecutionError("An edit summary cannot be empty.")
    if proposed_content == original_content:
        raise ToolExecutionError("The proposed content does not change the file.")

    relative_path = resolved_path.relative_to(project_root.resolve()).as_posix()
    diff = "".join(
        difflib.unified_diff(
            original_content.splitlines(keepends=True),
            proposed_content.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )

    return FileEditProposal(
        file_path=relative_path,
        summary=summary.strip(),
        original_sha256=hashlib.sha256(original_content.encode("utf-8")).hexdigest(),
        proposed_content=proposed_content,
        diff=diff,
    )


def apply_file_edit_proposal(
    project_root: Path,
    proposal: FileEditProposal,
    *,
    approved: bool,
) -> bool:
    """Apply an approved proposal if the original file has not changed."""
    if approved is not True:
        return False

    proposed_bytes = proposal.proposed_content.encode("utf-8")
    if len(proposed_bytes) > MAX_PROJECT_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"Proposed content exceeds the {MAX_PROJECT_FILE_SIZE_BYTES}-byte limit."
        )
    if b"\0" in proposed_bytes:
        raise ToolExecutionError("Proposed content cannot contain binary data.")

    resolved_path = resolve_project_file(project_root, proposal.file_path)
    current_content = read_project_text_file(resolved_path)
    current_sha256 = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
    if current_sha256 != proposal.original_sha256:
        raise ToolExecutionError(
            f"{proposal.file_path} changed after the edit was proposed. "
            "Create a new proposal before applying an edit."
        )

    original_mode = stat.S_IMODE(resolved_path.stat().st_mode)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=resolved_path.parent,
            prefix=f".{resolved_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(proposed_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.chmod(temporary_path, original_mode)
        latest_path = resolve_project_file(project_root, proposal.file_path)
        latest_content = read_project_text_file(latest_path)
        latest_sha256 = hashlib.sha256(latest_content.encode("utf-8")).hexdigest()
        if latest_sha256 != proposal.original_sha256:
            raise ToolExecutionError(
                f"{proposal.file_path} changed while the edit was being prepared. "
                "Create a new proposal before applying an edit."
            )

        os.replace(temporary_path, latest_path)
        temporary_path = None

        written_content = read_project_text_file(latest_path)
        if written_content != proposal.proposed_content:
            raise ToolExecutionError(
                f"Could not verify the approved edit to {proposal.file_path}."
            )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return True
