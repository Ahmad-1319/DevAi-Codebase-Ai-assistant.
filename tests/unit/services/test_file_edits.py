"""Tests for preparing non-destructive file-edit proposals."""

import hashlib
import os
from pathlib import Path

import pytest

from app.core.exceptions import FileTooLargeError, ToolExecutionError
from app.services.file_edits import (
    apply_file_edit_proposal,
    create_file_edit_proposal,
)
from app.tools.filesystem.read_file import MAX_FILE_SIZE_BYTES


def test_create_file_edit_proposal_returns_diff_and_original_fingerprint(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    original_content = "Before\n"
    proposed_content = "After\n"
    file_path.write_bytes(original_content.encode("utf-8"))
    original_bytes = file_path.read_bytes()

    proposal = create_file_edit_proposal(
        project_root,
        "notes.txt",
        proposed_content,
        "Clarify the note",
    )

    assert proposal.file_path == "notes.txt"
    assert proposal.summary == "Clarify the note"
    assert proposal.original_sha256 == hashlib.sha256(original_bytes).hexdigest()
    assert proposal.proposed_content == proposed_content
    assert "--- a/notes.txt" in proposal.diff
    assert "+++ b/notes.txt" in proposal.diff
    assert "-Before" in proposal.diff
    assert "+After" in proposal.diff
    assert file_path.read_bytes() == original_bytes


def test_create_file_edit_proposal_does_not_modify_original_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    original_bytes = b"original text\r\n"
    file_path.write_bytes(original_bytes)

    create_file_edit_proposal(
        project_root,
        "notes.txt",
        "replacement text\r\n",
        "Replace wording",
    )

    assert file_path.read_bytes() == original_bytes


def test_create_file_edit_proposal_rejects_paths_outside_project(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("original", encoding="utf-8")

    with pytest.raises(PermissionError, match="inside the selected project"):
        create_file_edit_proposal(
            project_root,
            outside_file,
            "changed",
            "Change content",
        )


def test_create_file_edit_proposal_rejects_oversized_proposed_content(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    file_path.write_text("original", encoding="utf-8")
    original_bytes = file_path.read_bytes()

    with pytest.raises(FileTooLargeError, match="Proposed content"):
        create_file_edit_proposal(
            project_root,
            "notes.txt",
            "x" * (MAX_FILE_SIZE_BYTES + 1),
            "Make file large",
        )

    assert file_path.read_bytes() == original_bytes


@pytest.mark.parametrize(
    ("proposed_content", "summary", "error_type", "message"),
    [
        ("original", "Change content", ToolExecutionError, "does not change"),
        ("updated", "  ", ToolExecutionError, "summary cannot be empty"),
        ("updated\0data", "Change content", ToolExecutionError, "binary data"),
    ],
)
def test_create_file_edit_proposal_rejects_invalid_proposals(
    tmp_path: Path,
    proposed_content: str,
    summary: str,
    error_type: type[Exception],
    message: str,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    file_path.write_text("original", encoding="utf-8")
    original_bytes = file_path.read_bytes()

    with pytest.raises(error_type, match=message):
        create_file_edit_proposal(
            project_root,
            "notes.txt",
            proposed_content,
            summary,
        )

    assert file_path.read_bytes() == original_bytes


def test_create_file_edit_proposal_rejects_ineligible_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    secret_file = project_root / ".env"
    secret_file.write_text("secret", encoding="utf-8")

    with pytest.raises(PermissionError, match="excluded"):
        create_file_edit_proposal(
            project_root,
            ".env",
            "changed",
            "Edit environment file",
        )


def test_apply_file_edit_proposal_writes_approved_content_atomically(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    file_path.write_text("Before\n", encoding="utf-8")
    proposal = create_file_edit_proposal(
        project_root,
        "notes.txt",
        "After\n",
        "Clarify the note",
    )

    applied = apply_file_edit_proposal(project_root, proposal, approved=True)

    assert applied is True
    assert file_path.read_text(encoding="utf-8") == "After\n"
    assert not list(project_root.glob(".notes.txt.*.tmp"))


def test_apply_file_edit_proposal_rejection_does_not_write(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    file_path.write_text("Before\n", encoding="utf-8")
    proposal = create_file_edit_proposal(
        project_root,
        "notes.txt",
        "After\n",
        "Clarify the note",
    )

    applied = apply_file_edit_proposal(project_root, proposal, approved=False)

    assert applied is False
    assert file_path.read_text(encoding="utf-8") == "Before\n"


def test_apply_file_edit_proposal_rejects_stale_original(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    file_path.write_text("Before\n", encoding="utf-8")
    proposal = create_file_edit_proposal(
        project_root,
        "notes.txt",
        "Agent's version\n",
        "Clarify the note",
    )
    file_path.write_text("Another user's change\n", encoding="utf-8")

    with pytest.raises(ToolExecutionError, match="changed after the edit was proposed"):
        apply_file_edit_proposal(project_root, proposal, approved=True)

    assert file_path.read_text(encoding="utf-8") == "Another user's change\n"


def test_apply_file_edit_proposal_preserves_original_on_replace_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    file_path.write_text("Before\n", encoding="utf-8")
    proposal = create_file_edit_proposal(
        project_root,
        "notes.txt",
        "After\n",
        "Clarify the note",
    )

    def fail_replace(_source: str | os.PathLike[str], _target: Path) -> None:
        del _source, _target
        raise OSError("replacement failed")

    monkeypatch.setattr("app.services.file_edits.os.replace", fail_replace)

    with pytest.raises(OSError, match="replacement failed"):
        apply_file_edit_proposal(project_root, proposal, approved=True)

    assert file_path.read_text(encoding="utf-8") == "Before\n"
    assert not list(project_root.glob(".notes.txt.*.tmp"))
