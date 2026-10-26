"""Tests for bounded, safe project text-file reading."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.context import ProjectContext
from app.core.exceptions import FileTooLargeError, NonTextFileError
from app.tools.filesystem.read_file import (
    MAX_FILE_SIZE_BYTES,
    read_file,
    read_project_file,
)


def test_read_file_returns_utf8_text_from_project_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "notes.txt"
    expected_text = "Hello, world!\nCaf\u00e9."
    file_path.write_bytes(expected_text.encode("utf-8"))

    assert read_file(project_root, "notes.txt") == expected_text


def test_read_file_accepts_a_file_exactly_at_the_size_limit(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    content = b"x" * MAX_FILE_SIZE_BYTES
    (project_root / "boundary.txt").write_bytes(content)

    assert read_file(project_root, "boundary.txt") == content.decode("utf-8")


def test_read_file_rejects_file_over_the_size_limit(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "large.txt").write_bytes(b"x" * (MAX_FILE_SIZE_BYTES + 1))

    with pytest.raises(FileTooLargeError, match="reading limit"):
        read_file(project_root, "large.txt")


def test_read_file_rejects_binary_content(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "binary.dat").write_bytes(b"header\x00payload")

    with pytest.raises(NonTextFileError, match="Binary files"):
        read_file(project_root, "binary.dat")


def test_read_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "invalid.txt").write_bytes(b"\xff\xfe")

    with pytest.raises(NonTextFileError, match="valid UTF-8"):
        read_file(project_root, "invalid.txt")


def test_read_file_propagates_missing_file_error(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(FileNotFoundError):
        read_file(project_root, "missing.txt")


def test_read_file_cannot_read_outside_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("private", encoding="utf-8")

    with pytest.raises(PermissionError, match="inside the selected project"):
        read_file(project_root, outside_file)


def test_read_file_cannot_read_excluded_secret_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("SECRET=value", encoding="utf-8")

    with pytest.raises(PermissionError, match="excluded"):
        read_file(project_root, ".env")


def test_read_project_file_tool_reads_from_runtime_project_context(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "notes.txt").write_text("A project note.", encoding="utf-8")
    runtime = SimpleNamespace(context=ProjectContext(project_root=project_root))

    result = read_project_file.func(runtime=runtime, file_path="notes.txt")

    assert result == "File: notes.txt\nContent:\nA project note."


def test_read_project_file_tool_schema_only_exposes_file_path() -> None:
    schema = read_project_file.tool_call_schema.model_json_schema()

    assert set(schema["properties"]) == {"file_path"}
    assert schema["required"] == ["file_path"]
