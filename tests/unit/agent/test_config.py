"""Tests for model and credential configuration."""

import os
from pathlib import Path

import pytest

from app.agent.config import DEFAULT_MODEL_NAME, AgentConfig
from app.core.exceptions import ConfigurationError


def test_agent_config_uses_default_model_and_temperature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("DEVAI_MODEL", raising=False)
    monkeypatch.delenv("DEVAI_TEMPERATURE", raising=False)

    config = AgentConfig.from_environment(tmp_path)

    assert config == AgentConfig(DEFAULT_MODEL_NAME, 0.0)


def test_agent_config_loads_credentials_and_model_from_selected_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "GOOGLE_API_KEY=project-key\n"
        "DEVAI_MODEL=google_genai:gemini-project-model\n"
        "DEVAI_TEMPERATURE=0.6\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("DEVAI_MODEL", raising=False)
    monkeypatch.delenv("DEVAI_TEMPERATURE", raising=False)

    config = AgentConfig.from_environment(tmp_path)

    assert config == AgentConfig("google_genai:gemini-project-model", 0.6)
    assert os.environ["GOOGLE_API_KEY"] == "project-key"


def test_agent_config_does_not_override_environment_with_project_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("GOOGLE_API_KEY=project-key\n", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_API_KEY", "existing-key")

    AgentConfig.from_environment(tmp_path)

    assert os.environ["GOOGLE_API_KEY"] == "existing-key"


def test_agent_config_requires_google_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="GOOGLE_API_KEY"):
        AgentConfig.from_environment(tmp_path)


@pytest.mark.parametrize(
    "model_name",
    ["", "gemini-unqualified", "openai:gpt-test"],
)
def test_agent_config_rejects_unsupported_model_identifiers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    model_name: str,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("DEVAI_MODEL", model_name)

    with pytest.raises(ConfigurationError, match="google_genai"):
        AgentConfig.from_environment(tmp_path)


@pytest.mark.parametrize("temperature", ["not-a-number", "-0.1", "2.1"])
def test_agent_config_rejects_invalid_temperature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    temperature: str,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("DEVAI_TEMPERATURE", temperature)

    with pytest.raises(ConfigurationError, match="between 0 and 2"):
        AgentConfig.from_environment(tmp_path)
