"""Tests for bounded project-file inventory."""

from pathlib import Path

import pytest

from app.tools.filesystem.list_files import _collect_file_summary


def test_collect_file_summary_counts_only_eligible_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    (tmp_path / "UTIL.PY").write_text("", encoding="utf-8")
    (tmp_path / "README").write_text("", encoding="utf-8")
    (tmp_path / ".env").write_text("", encoding="utf-8")
    (tmp_path / ".env.local").write_text("", encoding="utf-8")
    (tmp_path / ".env.example").write_text("", encoding="utf-8")
    (tmp_path / "cache.pyc").write_text("", encoding="utf-8")
    ignored_directory = tmp_path / "NoDe_MoDuLeS"
    ignored_directory.mkdir()
    (ignored_directory / "hidden.py").write_text("", encoding="utf-8")

    total, counts, paths = _collect_file_summary(tmp_path)

    assert total == 4
    assert counts == {".py": 2, "[no extension]": 1, ".example": 1}
    assert set(paths) == {"main.py", "UTIL.PY", "README", ".env.example"}


def test_collect_file_summary_returns_no_paths_for_empty_folder(
    tmp_path: Path,
) -> None:
    assert _collect_file_summary(tmp_path) == (0, {}, [])


def test_collect_file_summary_caps_returned_paths_but_counts_all_files(
    tmp_path: Path,
) -> None:
    for index in range(101):
        (tmp_path / f"file-{index:03}.txt").write_text("", encoding="utf-8")

    total, counts, paths = _collect_file_summary(tmp_path)

    assert total == 101
    assert counts == {".txt": 101}
    assert len(paths) == 100
    assert paths[0] == "file-000.txt"
    assert paths[-1] == "file-099.txt"


def test_collect_file_summary_rejects_missing_project_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        _collect_file_summary(tmp_path / "missing")


def test_collect_file_summary_rejects_file_as_project_root(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="Not a project folder"):
        _collect_file_summary(file_path)
