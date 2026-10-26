"""Tests for bounded project text search."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.context import ProjectContext
from app.tools.search.search_code import (
    MAX_SEARCH_FILE_SIZE_BYTES,
    MAX_SEARCH_RESULTS,
    search_code,
    search_project_code,
)


def test_search_code_returns_relative_paths_and_one_based_line_numbers(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    source = project_root / "src" / "main.py"
    source.parent.mkdir(parents=True)
    source.write_text("first line\nFindMe here\nlast line", encoding="utf-8")

    assert search_code(project_root, "findme") == ["src/main.py:2: FindMe here"]


def test_search_code_treats_query_as_literal_text(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "example.txt").write_text(
        "value = a+b\nvalue = aaab\n",
        encoding="utf-8",
    )

    assert search_code(project_root, "a+b") == ["example.txt:1: value = a+b"]


def test_search_code_skips_excluded_files_and_directories(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / ".git").mkdir(parents=True)
    (project_root / ".git" / "secret.txt").write_text("needle", encoding="utf-8")
    (project_root / "node_modules").mkdir()
    (project_root / "node_modules" / "dependency.txt").write_text(
        "needle",
        encoding="utf-8",
    )
    (project_root / "src").mkdir()
    (project_root / "src" / ".env").write_text("needle", encoding="utf-8")
    (project_root / "src" / "visible.txt").write_text("needle", encoding="utf-8")

    assert search_code(project_root, "needle") == ["src/visible.txt:1: needle"]


def test_search_code_skips_oversized_binary_and_invalid_utf8_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "large.txt").write_bytes(
        b"needle" * (MAX_SEARCH_FILE_SIZE_BYTES // 6 + 1)
    )
    (project_root / "binary.dat").write_bytes(b"needle\x00payload")
    (project_root / "invalid.txt").write_bytes(b"needle\xff")
    (project_root / "valid.txt").write_text("needle", encoding="utf-8")

    assert search_code(project_root, "needle") == ["valid.txt:1: needle"]


def test_search_code_limits_matches_and_preview_length(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    long_line = f"needle {'x' * 300}"
    (project_root / "many.txt").write_text(
        "\n".join([long_line] * (MAX_SEARCH_RESULTS + 1)),
        encoding="utf-8",
    )

    results = search_code(project_root, "needle")

    assert len(results) == MAX_SEARCH_RESULTS
    assert len(results[0].split(": ", maxsplit=1)[1]) == 240


def test_search_code_rejects_empty_query(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="cannot be empty"):
        search_code(project_root, "  ")


def test_search_code_rejects_missing_or_non_directory_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        search_code(tmp_path / "missing", "needle")

    file_path = tmp_path / "file.txt"
    file_path.write_text("", encoding="utf-8")
    with pytest.raises(NotADirectoryError, match="Not a project folder"):
        search_code(file_path, "needle")


def test_search_project_code_tool_uses_context_and_reports_search_rules(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "main.py").write_text("needle", encoding="utf-8")
    runtime = SimpleNamespace(context=ProjectContext(project_root=project_root))

    output = search_project_code.func(runtime=runtime, query="needle")

    assert "Found 1 match(es):" in output
    assert "main.py:1: needle" in output
    assert "case-insensitive and literal" in output


def test_search_project_code_tool_schema_only_exposes_query() -> None:
    schema = search_project_code.tool_call_schema.model_json_schema()

    assert set(schema["properties"]) == {"query"}
    assert schema["required"] == ["query"]


def test_search_project_code_tool_reports_no_matches(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "main.py").write_text("nothing here", encoding="utf-8")
    runtime = SimpleNamespace(context=ProjectContext(project_root=project_root))

    output = search_project_code.func(runtime=runtime, query="needle")

    assert output.startswith("No matches found")
    assert "binary files" in output


def test_search_project_code_tool_reports_result_limit(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "many.txt").write_text(
        "\n".join(["needle"] * (MAX_SEARCH_RESULTS + 1)),
        encoding="utf-8",
    )
    runtime = SimpleNamespace(context=ProjectContext(project_root=project_root))

    output = search_project_code.func(runtime=runtime, query="needle")

    assert f"Found {MAX_SEARCH_RESULTS} match(es)" in output
    assert "more may exist" in output
