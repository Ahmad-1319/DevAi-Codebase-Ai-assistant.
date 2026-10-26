"""Application-controlled context supplied to agent tools."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectContext:
    """The project folder that tools are allowed to inspect."""

    project_root: Path
