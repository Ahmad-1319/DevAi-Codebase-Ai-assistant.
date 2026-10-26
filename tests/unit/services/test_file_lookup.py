"""Tests for resolving project files by basename."""

from pathlib import Path

import pytest

from app.services.codebase import find_project_files_by_name


def test_find_project_files_by_name_finds_nested_files_case_insensitively(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    source_folder = project_root / "src"
    source_folder.mkdir(parents=True)
    (source_folder / "Main.py").write_text("main", encoding="utf-8")

    assert find_project_files_by_name(project_root, "main.py") == ["src/Main.py"]


def test_find_project_files_by_name_returns_all_sorted_matches(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "tests").mkdir()
    (project_root / "tests" / "main.py").write_text("", encoding="utf-8")
    (project_root / "src" / "main.py").write_text("", encoding="utf-8")

    assert find_project_files_by_name(project_root, "main.py") == [
        "src/main.py",
        "tests/main.py",
    ]


def test_find_project_files_by_name_ignores_excluded_files_and_directories(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / ".venv").mkdir(parents=True)
    (project_root / ".venv" / "main.py").write_text("", encoding="utf-8")
    (project_root / ".git").mkdir()
    (project_root / ".git" / "main.py").write_text("", encoding="utf-8")
    (project_root / "src").mkdir()
    (project_root / "src" / ".env").write_text("", encoding="utf-8")

    assert find_project_files_by_name(project_root, "main.py") == []
    assert find_project_files_by_name(project_root, ".env") == []


def test_find_project_files_by_name_rejects_directory_components(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="without directory components"):
        find_project_files_by_name(project_root, "src/main.py")


def test_find_project_files_by_name_reports_missing_project_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        find_project_files_by_name(tmp_path / "missing", "main.py")
