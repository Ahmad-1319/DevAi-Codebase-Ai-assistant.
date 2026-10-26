"""Prepare and apply a file edit only after explicit human approval."""

from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from app.core.context import ProjectContext
from app.core.exceptions import ToolExecutionError
from app.services.file_edits import (
    apply_file_edit_proposal,
    create_file_edit_proposal,
)


@tool
def propose_file_edit(
    runtime: ToolRuntime[ProjectContext],
    file_path: str,
    proposed_content: str,
    summary: str,
) -> str:
    """Propose one complete-file edit and pause for the user to review its diff."""
    proposal = create_file_edit_proposal(
        runtime.context.project_root,
        file_path,
        proposed_content,
        summary,
    )
    decision = interrupt(
        {
            "type": "file_edit_review",
            "file_path": proposal.file_path,
            "summary": proposal.summary,
            "diff": proposal.diff,
        }
    )
    if not isinstance(decision, dict) or type(decision.get("approved")) is not bool:
        raise ToolExecutionError(
            "The file-edit approval response must include a boolean."
        )
    if not decision["approved"]:
        return f"Edit rejected. {proposal.file_path} was not changed."

    apply_file_edit_proposal(
        runtime.context.project_root,
        proposal,
        approved=True,
    )
    return f"Approved edit applied to {proposal.file_path}."
