"""Create the AI agent and register its codebase tools."""

from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.config import AgentConfig
from app.agent.prompts import SYSTEM_PROMPT
from app.core.context import ProjectContext
from app.tools.filesystem.edit_file import propose_file_edit
from app.tools.filesystem.list_files import (
    count_project_files_by_type,
    list_project_files,
)
from app.tools.filesystem.read_file import read_project_file
from app.tools.search.search_code import search_project_code


def create_codebase_agent(project_root: Path):
    """Create the agent with file-listing access and conversation memory."""
    config = AgentConfig.from_environment(project_root)
    model = init_chat_model(
        config.model_name,
        temperature=config.temperature,
    )
    return create_agent(
        model=model,
        tools=[
            list_project_files,
            count_project_files_by_type,
            read_project_file,
            search_project_code,
            propose_file_edit,
        ],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
        context_schema=ProjectContext,
    )
