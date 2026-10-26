"""Validated configuration for the model-backed agent."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.core.exceptions import ConfigurationError

DEFAULT_MODEL_NAME = "google_genai:gemini-2.5-flash-lite"
_SUPPORTED_MODEL_PROVIDER = "google_genai:"


@dataclass(frozen=True)
class AgentConfig:
    """Settings that describe which model and behavior the agent should use."""

    model_name: str = DEFAULT_MODEL_NAME
    temperature: float = 0.0

    @classmethod
    def from_environment(cls, project_root: Path) -> "AgentConfig":
        """Load and validate model settings and credentials for a project."""
        load_dotenv(dotenv_path=project_root / ".env", override=False)

        api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError(
                "GOOGLE_API_KEY is not configured. Set it in the selected "
                "project's .env file or in your environment."
            )

        model_name = os.environ.get("DEVAI_MODEL", DEFAULT_MODEL_NAME).strip()
        if (
            not model_name.startswith(_SUPPORTED_MODEL_PROVIDER)
            or not model_name[len(_SUPPORTED_MODEL_PROVIDER) :]
        ):
            raise ConfigurationError(
                "DEVAI_MODEL must use the google_genai:<model-name> format."
            )

        raw_temperature = os.environ.get("DEVAI_TEMPERATURE", "0")
        try:
            temperature = float(raw_temperature)
        except ValueError as error:
            raise ConfigurationError(
                "DEVAI_TEMPERATURE must be a number between 0 and 2."
            ) from error

        if not 0 <= temperature <= 2:
            raise ConfigurationError(
                "DEVAI_TEMPERATURE must be a number between 0 and 2."
            )

        return cls(model_name=model_name, temperature=temperature)
