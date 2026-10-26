"""Tests for agent tool registration."""

from pathlib import Path
from typing import Any

import pytest

from app.agent import agent as agent_module
from app.agent.config import DEFAULT_MODEL_NAME
from app.tools.filesystem.edit_file import propose_file_edit
from app.tools.filesystem.list_files import (
    count_project_files_by_type,
    list_project_files,
)
from app.tools.filesystem.read_file import read_project_file
from app.tools.search.search_code import search_project_code


def test_create_codebase_agent_registers_project_read_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_create_agent(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(agent_module, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_module,
        "init_chat_model",
        lambda model_name, temperature: (model_name, temperature),
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    result = agent_module.create_codebase_agent(tmp_path)

    assert result == captured
    assert captured["model"] == (DEFAULT_MODEL_NAME, 0.0)
    assert captured["tools"] == [
        list_project_files,
        count_project_files_by_type,
        read_project_file,
        search_project_code,
        propose_file_edit,
    ]


def test_create_codebase_agent_uses_model_from_project_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("DEVAI_MODEL", "google_genai:gemini-test")
    monkeypatch.setenv("DEVAI_TEMPERATURE", "0.4")
    captured: dict[str, Any] = {}

    def fake_create_agent(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(agent_module, "create_agent", fake_create_agent)
    monkeypatch.setattr(
        agent_module,
        "init_chat_model",
        lambda model_name, temperature: (model_name, temperature),
    )

    agent_module.create_codebase_agent(tmp_path)

    assert captured["model"] == ("google_genai:gemini-test", 0.4)
