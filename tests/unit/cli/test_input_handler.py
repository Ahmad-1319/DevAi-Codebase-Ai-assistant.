"""Tests for terminal input and project-folder selection."""

from pathlib import Path

import pytest

from app.cli.input_handler import (
    choose_file_candidate,
    choose_project_root,
    get_input,
)


def test_get_input_displays_prompt_and_returns_user_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return "  explain this  "

    monkeypatch.setattr("builtins.input", fake_input)

    assert get_input() == "  explain this  "
    assert prompts == ["> "]


def test_choose_file_candidate_returns_selected_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")

    selected = choose_file_candidate("main.py", ["src/main.py", "tests/main.py"])

    assert selected == "tests/main.py"
    output = capsys.readouterr().out
    assert "1. src/main.py" in output
    assert "2. tests/main.py" in output


def test_choose_file_candidate_retries_invalid_choices(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("not a number", "3", "1"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    selected = choose_file_candidate("main.py", ["src/main.py", "tests/main.py"])

    assert selected == "src/main.py"
    output = capsys.readouterr().out
    assert "Enter one of the listed numbers" in output
    assert "Choose a number from the list" in output


@pytest.mark.parametrize("answer", ["cancel", "EXIT", "quit"])
def test_choose_file_candidate_can_be_canceled(
    monkeypatch: pytest.MonkeyPatch,
    answer: str,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)

    assert choose_file_candidate("main.py", ["src/main.py"]) is None


def test_choose_project_root_accepts_current_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    assert choose_project_root() == tmp_path.resolve()


def test_choose_project_root_resolves_quoted_custom_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project with spaces"
    project_root.mkdir()
    answers = iter(("n", f'"{project_root}"'))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert choose_project_root() == project_root.resolve()


@pytest.mark.parametrize("answer", ["exit", "QUIT"])
def test_choose_project_root_can_be_canceled(
    monkeypatch: pytest.MonkeyPatch,
    answer: str,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)

    assert choose_project_root() is None


def test_choose_project_root_retries_invalid_choices_and_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    file_path = tmp_path / "not-a-folder.txt"
    file_path.write_text("text", encoding="utf-8")
    project_root = tmp_path / "valid-folder"
    project_root.mkdir()
    missing_path = tmp_path / "missing-folder"
    answers = iter(
        (
            "maybe",
            "n",
            str(missing_path),
            "n",
            str(file_path),
            "n",
            str(project_root),
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert choose_project_root() == project_root.resolve()
    output = capsys.readouterr().out
    assert "Choose Enter, Y, N, or exit." in output
    assert "That path does not exist. Try again." in output
    assert "That path is a file, not a folder. Try again." in output


def test_choose_project_root_retries_an_empty_custom_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("n", "  ", "n", str(tmp_path)))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert choose_project_root() == tmp_path.resolve()
    assert "Please enter a folder path." in capsys.readouterr().out
