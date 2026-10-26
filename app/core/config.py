
"""Application-wide settings.

Add settings here when they are shared by multiple parts of the application.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Basic settings shared by the application."""

    project_root: Path = field(default_factory=Path.cwd)
    log_level: str = "INFO"
