"""Tests for translating agent message streams into text."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from app.core.context import ProjectContext
from app.core.exceptions import AmbiguousFileReferenceError, ToolExecutionError
from app.services.agent_service import FileEditReview, stream_agent_response


class FakeAgent:
    """Small agent substitute that records the service call."""

    def __init__(self) -> None:
        self.call: tuple[tuple[Any, ...], dict[str, Any]] | None = None
        self.events: list[list[tuple[str, Any]]] = [
            [
                ("messages", (AIMessage(content="Hello"), {})),
                ("messages", (HumanMessage(content="Ignore this message"), {})),
                ("messages", (AIMessageChunk(content=" world"), {})),
                (
                    "messages",
                    (AIMessage(content=[{"type": "text", "text": "!"}]), {}),
                ),
            ]
        ]
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def astream(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        self.call = (args, kwargs)
        self.calls.append((args, kwargs))
        for event in self.events.pop(0):
            yield event


def test_stream_agent_response_yields_ai_text_and_passes_request_context() -> None:
    agent = FakeAgent()
    config: RunnableConfig = {"configurable": {"thread_id": "test-thread"}}
    context = ProjectContext(project_root=Path("."))

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Say hello",
                config,
                context,
            )
        ]

    chunks = asyncio.run(collect_chunks())

    assert chunks == ["Hello", " world", "!"]
    assert agent.call is not None
    args, kwargs = agent.call
    assert args == ({"messages": [{"role": "user", "content": "Say hello"}]},)
    assert kwargs == {
        "config": config,
        "context": context,
        "stream_mode": ["messages", "updates"],
    }


@pytest.mark.parametrize("approved", [True, False])
def test_stream_agent_response_reviews_and_resumes_file_edit(
    approved: bool,
) -> None:
    review = {
        "type": "file_edit_review",
        "file_path": "notes.txt",
        "summary": "Clarify the note",
        "diff": "--- a/notes.txt\n+++ b/notes.txt\n",
    }
    agent = FakeAgent()
    agent.events = [
        [("updates", {"__interrupt__": (SimpleNamespace(value=review, id="edit-1"),)})],
        [("messages", (AIMessage(content="Edit handled."), {}))],
    ]
    reviews: list[FileEditReview] = []

    def review_edit(request: FileEditReview) -> bool:
        reviews.append(request)
        return approved

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Update the file",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=Path(".")),
                edit_review=review_edit,
            )
        ]

    chunks = asyncio.run(collect_chunks())

    assert chunks == ["Edit handled."]
    assert reviews == [FileEditReview("notes.txt", "Clarify the note", review["diff"])]
    assert len(agent.calls) == 2
    resume_args, _ = agent.calls[1]
    assert isinstance(resume_args[0], Command)
    assert resume_args[0].resume == {"approved": approved}


def test_stream_agent_response_rejects_invalid_interrupt_payload() -> None:
    agent = FakeAgent()
    agent.events = [[("updates", {"__interrupt__": "invalid"})]]

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Update the file",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=Path(".")),
            )
        ]

    with pytest.raises(ToolExecutionError, match="invalid review interruption"):
        asyncio.run(collect_chunks())


def test_stream_agent_response_directs_agent_to_read_explicit_file_mentions(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    config: RunnableConfig = {"configurable": {"thread_id": "test-thread"}}
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app").mkdir()
    (project_root / "app" / "main.py").write_text("main", encoding="utf-8")
    docs = project_root / "docs"
    docs.mkdir()
    (docs / "getting started.md").write_text("guide", encoding="utf-8")
    context = ProjectContext(project_root=project_root)
    user_input = 'Explain @app/main.py and @"docs/getting started.md"'

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                user_input,
                config,
                context,
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    message = args[0]["messages"][0]["content"]
    assert user_input in message
    assert "- app/main.py" in message
    assert "- docs/getting started.md" in message
    assert "Read each exact path with read_project_file" in message


def test_stream_agent_response_deduplicates_repeated_file_mentions(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app").mkdir()
    (project_root / "app" / "main.py").write_text("main", encoding="utf-8")
    context = ProjectContext(project_root=project_root)

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Compare @app/main.py with @app/main.py",
                {"configurable": {"thread_id": "test-thread"}},
                context,
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    message = args[0]["messages"][0]["content"]
    assert message.count("- app/main.py") == 1


def test_stream_agent_response_validates_unmarked_file_paths(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app").mkdir()
    (project_root / "app" / "main.py").write_text("main", encoding="utf-8")
    context = ProjectContext(project_root=project_root)

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Explain app/main.py, please.",
                {"configurable": {"thread_id": "test-thread"}},
                context,
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    message = args[0]["messages"][0]["content"]
    assert "- app/main.py" in message


def test_stream_agent_response_validates_quoted_unmarked_paths_with_spaces(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    project_root.mkdir()
    docs = project_root / "docs"
    docs.mkdir()
    (docs / "getting started.md").write_text("guide", encoding="utf-8")
    context = ProjectContext(project_root=project_root)

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                'Summarize "docs/getting started.md"',
                {"configurable": {"thread_id": "test-thread"}},
                context,
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    assert "- docs/getting started.md" in args[0]["messages"][0]["content"]


def test_stream_agent_response_rejects_missing_unmarked_path_before_agent_call(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    project_root.mkdir()

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Explain app/missing.py",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=project_root),
            )
        ]

    with pytest.raises(FileNotFoundError):
        asyncio.run(collect_chunks())

    assert agent.call is None


@pytest.mark.parametrize(
    ("user_text", "error_type"),
    [
        ("Read @.env", PermissionError),
        ("Read app/.env", PermissionError),
        ("Read @missing/file.py", FileNotFoundError),
    ],
)
def test_stream_agent_response_rejects_invalid_file_mentions(
    tmp_path: Path,
    user_text: str,
    error_type: type[OSError],
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    project_root.mkdir()

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                user_text,
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=project_root),
            )
        ]

    with pytest.raises(error_type):
        asyncio.run(collect_chunks())

    assert agent.call is None


def test_stream_agent_response_rejects_absolute_path_outside_project(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("private", encoding="utf-8")

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                f"Read @{outside_file}",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=project_root),
            )
        ]

    with pytest.raises(PermissionError, match="inside the selected project"):
        asyncio.run(collect_chunks())

    assert agent.call is None


def test_stream_agent_response_resolves_unique_basename(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    source_folder = project_root / "src"
    source_folder.mkdir(parents=True)
    (source_folder / "main.py").write_text("main", encoding="utf-8")

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Explain main.py",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=project_root),
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    assert "- src/main.py" in args[0]["messages"][0]["content"]


def test_stream_agent_response_requires_choice_for_duplicate_basename(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    for folder in ("src", "tests"):
        directory = project_root / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "main.py").write_text(folder, encoding="utf-8")

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Explain @main.py",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=project_root),
            )
        ]

    with pytest.raises(AmbiguousFileReferenceError) as error:
        asyncio.run(collect_chunks())

    assert error.value.file_name == "main.py"
    assert error.value.candidates == ["src/main.py", "tests/main.py"]
    assert agent.call is None


def test_stream_agent_response_uses_user_selected_duplicate_match(
    tmp_path: Path,
) -> None:
    agent = FakeAgent()
    project_root = tmp_path / "project"
    for folder in ("src", "tests"):
        directory = project_root / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "main.py").write_text(folder, encoding="utf-8")

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                "Explain @main.py",
                {"configurable": {"thread_id": "test-thread"}},
                ProjectContext(project_root=project_root),
                {"main.py": "tests/main.py"},
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    assert "- tests/main.py" in args[0]["messages"][0]["content"]


def test_stream_agent_response_leaves_plain_conversation_untouched() -> None:
    agent = FakeAgent()
    context = ProjectContext(project_root=Path("."))
    user_input = "What is dependency injection?"

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                user_input,
                {"configurable": {"thread_id": "test-thread"}},
                context,
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    assert args == ({"messages": [{"role": "user", "content": user_input}]},)


def test_stream_agent_response_does_not_treat_version_number_as_a_file() -> None:
    agent = FakeAgent()
    context = ProjectContext(project_root=Path("."))
    user_input = "What changed in Python 3.13?"

    async def collect_chunks() -> list[str]:
        return [
            chunk
            async for chunk in stream_agent_response(
                agent,
                user_input,
                {"configurable": {"thread_id": "test-thread"}},
                context,
            )
        ]

    asyncio.run(collect_chunks())

    assert agent.call is not None
    args, _ = agent.call
    assert args == ({"messages": [{"role": "user", "content": user_input}]},)
