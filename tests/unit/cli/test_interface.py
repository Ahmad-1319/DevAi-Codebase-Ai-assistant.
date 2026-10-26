"""Tests for CLI handling of ambiguous file references."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ConnectError
from langchain_core.exceptions import (
    ModelAPIError,
    ModelAuthenticationError,
    ModelConnectionError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from langchain_core.messages import AIMessage

from app.cli import interface
from app.core.exceptions import ConfigurationError, ToolExecutionError
from app.services.agent_service import FileEditReview


class FakeAgent:
    """Agent substitute that records calls without contacting a provider."""

    def __init__(self, failure: Exception | None = None) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.failure = failure

    async def astream(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        self.calls.append((args, kwargs))
        if self.failure is not None:
            raise self.failure
        yield "messages", (AIMessage(content="Read the selected file."), {})


def test_cli_prompts_for_duplicate_basename_then_resumes_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = tmp_path / "project"
    for folder in ("src", "tests"):
        directory = project_root / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "main.py").write_text(folder, encoding="utf-8")

    agent = FakeAgent()
    answers = iter(("Explain @main.py", "2", "exit"))

    def fake_input(prompt: str) -> str:
        assert prompt
        return next(answers)

    monkeypatch.setattr(interface, "choose_project_root", lambda: project_root)

    def return_agent(_project_root: Path) -> FakeAgent:
        return agent

    monkeypatch.setattr(
        interface,
        "create_codebase_agent",
        return_agent,
    )
    monkeypatch.setattr("builtins.input", fake_input)

    asyncio.run(interface.start_cli())

    assert len(agent.calls) == 1
    args, kwargs = agent.calls[0]
    assert "- tests/main.py" in args[0]["messages"][0]["content"]
    assert kwargs["context"].project_root == project_root
    output = capsys.readouterr().out
    assert "1. src/main.py" in output
    assert "2. tests/main.py" in output
    assert "Read the selected file." in output
    assert "Goodbye!" in output


@pytest.mark.parametrize(
    ("answer", "approved"),
    [("y", True), ("yes", True), ("n", False), ("", False)],
)
def test_cli_file_edit_review_requires_explicit_approval(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    answer: str,
    approved: bool,
) -> None:
    def fake_input(prompt: str) -> str:
        assert prompt
        return answer

    monkeypatch.setattr("builtins.input", fake_input)

    result = interface._review_file_edit(
        FileEditReview(
            file_path="notes.txt",
            summary="Clarify the note",
            diff="--- a/notes.txt\n+++ b/notes.txt\n",
        )
    )

    assert result is approved
    output = capsys.readouterr().out
    assert "notes.txt" in output
    assert "Clarify the note" in output
    assert "--- a/notes.txt" in output
    if not approved:
        assert "DevAI did not apply this proposal." in output


@pytest.mark.parametrize(
    ("failure", "expected_message"),
    [
        (
            ModelAuthenticationError("invalid credentials"),
            "Check GOOGLE_API_KEY in .env",
        ),
        (ModelRateLimitError("quota exceeded"), "rate limit or quota"),
        (ModelConnectionError("provider unavailable"), "could not reach"),
        (ModelTimeoutError("request timed out"), "could not reach"),
        (ModelAPIError("provider error"), "could not complete the request"),
        (ConnectError("network unavailable"), "could not reach"),
        (ToolExecutionError("edit was rejected by validation"), "could not complete"),
        (FileNotFoundError("missing.py"), "could not find the requested project file"),
        (PermissionError("access denied"), "does not have permission"),
        (OSError("disk unavailable"), "file-system operation failed"),
    ],
)
def test_cli_reports_request_failures_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    failure: Exception,
    expected_message: str,
) -> None:
    agent = FakeAgent(failure)
    answers = iter(("Please answer", "exit"))

    monkeypatch.setattr(interface, "choose_project_root", lambda: tmp_path)

    def return_agent(_project_root: Path) -> FakeAgent:
        return agent

    monkeypatch.setattr(interface, "create_codebase_agent", return_agent)

    def fake_input(prompt: str) -> str:
        assert prompt
        return next(answers)

    monkeypatch.setattr("builtins.input", fake_input)

    asyncio.run(interface.start_cli())

    output = capsys.readouterr().out
    assert expected_message in output
    assert "Goodbye!" in output
    assert "Traceback" not in output


def test_cli_reports_invalid_configuration_without_starting_chat(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_agent_creation(_project_root: Path) -> None:
        raise ConfigurationError("GOOGLE_API_KEY is not configured")

    monkeypatch.setattr(interface, "choose_project_root", lambda: tmp_path)
    monkeypatch.setattr(interface, "create_codebase_agent", fail_agent_creation)

    asyncio.run(interface.start_cli())

    output = capsys.readouterr().out
    assert "DevAI configuration error" in output
    assert "GOOGLE_API_KEY is not configured" in output
    assert "Ask a question" not in output
