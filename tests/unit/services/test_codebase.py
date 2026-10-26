"""Tests for shared project file-path validation."""

from pathlib import Path

import pytest

from app.services.codebase import resolve_project_file


def test_resolve_project_file_accepts_relative_and_absolute_paths(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    file_path = project_root / "src" / "main.py"
    file_path.parent.mkdir()
    file_path.write_text("print('hello')", encoding="utf-8")

    assert resolve_project_file(project_root, Path("src") / "main.py") == file_path
    assert resolve_project_file(project_root, file_path) == file_path


@pytest.mark.parametrize(
    "requested_path",
    [
        Path("..") / "outside.txt",
        Path("nested") / ".." / "outside.txt",
    ],
)
def test_resolve_project_file_rejects_parent_traversal(
    tmp_path: Path,
    requested_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(PermissionError, match="inside the selected project"):
        resolve_project_file(project_root, requested_path)


def test_resolve_project_file_rejects_absolute_path_outside_project(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("private", encoding="utf-8")

    with pytest.raises(PermissionError, match="inside the selected project"):
        resolve_project_file(project_root, outside_file)


@pytest.mark.parametrize(
    "relative_path",
    [
        Path(".git") / "config",
        Path("NoDe_MoDuLeS") / "package.json",
        Path(".env"),
        Path(".env.local"),
        Path("secret.pyc"),
    ],
)
def test_resolve_project_file_rejects_excluded_paths(
    tmp_path: Path,
    relative_path: Path,
) -> None:
    project_root = tmp_path / "project"
    excluded_file = project_root / relative_path
    excluded_file.parent.mkdir(parents=True, exist_ok=True)
    excluded_file.write_text("excluded", encoding="utf-8")

    with pytest.raises(PermissionError):
        resolve_project_file(project_root, relative_path)


def test_resolve_project_file_allows_env_example(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    example_file = project_root / ".env.example"
    example_file.write_text("EXAMPLE=value", encoding="utf-8")

    assert resolve_project_file(project_root, ".env.example") == example_file


def test_resolve_project_file_reports_missing_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(FileNotFoundError):
        resolve_project_file(project_root, "missing.txt")


def test_resolve_project_file_rejects_directory_target(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "folder").mkdir()

    with pytest.raises(IsADirectoryError, match="Not a regular file"):
        resolve_project_file(project_root, "folder")


def test_resolve_project_file_rejects_symlink_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    link = project_root / "link.txt"
    link.write_text("content", encoding="utf-8")
    original_is_symlink = Path.is_symlink

    def is_symlink(path: Path) -> bool:
        return path == link or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)

    with pytest.raises(PermissionError, match="Symbolic links"):
        resolve_project_file(project_root, "link.txt")
