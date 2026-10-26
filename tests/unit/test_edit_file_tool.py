"""End-to-end tests for the approval-gated file-edit agent tool."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.cli.interface import _review_file_edit
from app.core.context import ProjectContext
from app.services.agent_service import FileEditReview, stream_agent_response
from app.tools.filesystem.edit_file import propose_file_edit


class ToolCallingFake(GenericFakeChatModel):
    """Fake model that emits a known call without contacting a provider."""

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> Any:
        del tools, kwargs
        return self


def _create_agent() -> Any:
    model = ToolCallingFake(
        disable_streaming=True,
        messages=iter(
            [
                AIMessage(
                    content="Propose the update.",
                    tool_calls=[
                        {
                            "name": "propose_file_edit",
                            "args": {
                                "file_path": "notes.txt",
                                "proposed_content": "After\n",
                                "summary": "Clarify the note",
                            },
                            "id": "edit-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="Finished."),
            ]
        ),
    )
    return create_agent(
        model=model,
        tools=[propose_file_edit],
        context_schema=ProjectContext,
        checkpointer=InMemorySaver(),
    )


@pytest.mark.parametrize(
    ("answer", "expected_content"),
    [("y", "After\n"), ("n", "Before\n")],
)
def test_file_edit_tool_waits_for_human_review_before_writing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    answer: str,
    expected_content: str,
) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Before\n", encoding="utf-8")
    agent = _create_agent()
    reviews: list[FileEditReview] = []

    def review_edit(review: FileEditReview) -> bool:
        assert file_path.read_text(encoding="utf-8") == "Before\n"
        reviews.append(review)
        monkeypatch.setattr("builtins.input", lambda _prompt: answer)
        return _review_file_edit(review)

    async def run_request() -> list[str]:
        return [
            text
            async for text in stream_agent_response(
                agent,
                "Update the note",
                {"configurable": {"thread_id": "edit-review"}},
                ProjectContext(project_root=tmp_path),
                edit_review=review_edit,
            )
        ]

    response = asyncio.run(run_request())

    assert file_path.read_text(encoding="utf-8") == expected_content
    assert len(reviews) == 1
    assert reviews[0].file_path == "notes.txt"
    assert reviews[0].summary == "Clarify the note"
    assert "-Before" in reviews[0].diff
    assert "+After" in reviews[0].diff
    assert response == ["Propose the update.", "Finished."]
