"""Application service for streaming answers from the agent."""

import re
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from app.core.context import ProjectContext
from app.core.exceptions import AmbiguousFileReferenceError, ToolExecutionError
from app.services.codebase import find_project_files_by_name, resolve_project_file

_EXPLICIT_FILE_MENTION_PATTERN = re.compile(r"""@(?:"([^"]+)"|'([^']+)'|([^\s]+))""")
_QUOTED_PATH_PATTERN = re.compile(r"""(?:"([^"]+)"|'([^']+)')""")
_UNQUOTED_PATH_PATTERN = re.compile(
    r"(?<![\w@])(?:[A-Za-z]:[\\/]|[\\/])?"
    r"(?:[\w.-]+[\\/])+[\w.-]+(?![\w.-])"
    r"|(?<![\w@])[A-Za-z_][\w.-]*\.[A-Za-z0-9]{1,12}(?![\w.-])"
)


@dataclass(frozen=True)
class FileEditReview:
    """The safe-to-display details of a proposed file edit."""

    file_path: str
    summary: str
    diff: str


def _review_from_interrupt(value: Any) -> FileEditReview:
    """Validate the interrupt payload before showing it to the user."""
    if (
        not isinstance(value, dict)
        or value.get("type") != "file_edit_review"
        or not isinstance(value.get("file_path"), str)
        or not isinstance(value.get("summary"), str)
        or not isinstance(value.get("diff"), str)
    ):
        raise ToolExecutionError("The agent requested an unsupported review action.")

    return FileEditReview(
        file_path=value["file_path"],
        summary=value["summary"],
        diff=value["diff"],
    )


def _file_mentions(user_input: str) -> list[str]:
    """Extract explicit and recognizable unmarked file paths from a request."""
    references: list[tuple[int, str]] = []
    occupied_spans: list[tuple[int, int]] = []

    for match in _EXPLICIT_FILE_MENTION_PATTERN.finditer(user_input):
        path = next(group for group in match.groups() if group is not None)
        references.append((match.start(), path.rstrip(".,;:!?")))
        occupied_spans.append(match.span())

    for match in _QUOTED_PATH_PATTERN.finditer(user_input):
        if any(
            match.start() < end and start < match.end() for start, end in occupied_spans
        ):
            continue

        path = next(group for group in match.groups() if group is not None)
        if "/" in path or "\\" in path or Path(path).suffix:
            references.append((match.start(), path))
            occupied_spans.append(match.span())

    for match in _UNQUOTED_PATH_PATTERN.finditer(user_input):
        if any(
            match.start() < end and start < match.end() for start, end in occupied_spans
        ):
            continue
        references.append((match.start(), match.group()))

    unique_paths: dict[str, None] = {}
    for _, path in sorted(references):
        unique_paths.setdefault(path, None)
    return list(unique_paths)


async def stream_agent_response(
    agent: Any,
    user_input: str,
    config: RunnableConfig,
    context: ProjectContext,
    file_choices: Mapping[str, str] | None = None,
    edit_review: Callable[[FileEditReview], bool] | None = None,
) -> AsyncIterator[str]:
    """Stream agent text and resume approved file-edit reviews."""
    mentions = _file_mentions(user_input)
    if mentions:
        validated_paths: list[Path] = []
        for mention in mentions:
            selected_path = file_choices.get(mention) if file_choices else None
            if selected_path is not None:
                validated_paths.append(
                    resolve_project_file(context.project_root, selected_path)
                )
                continue

            try:
                validated_paths.append(
                    resolve_project_file(context.project_root, mention)
                )
            except FileNotFoundError as error:
                if Path(mention).name != mention:
                    raise
                candidates = find_project_files_by_name(
                    context.project_root,
                    mention,
                )
                if not candidates:
                    raise
                if len(candidates) > 1:
                    raise AmbiguousFileReferenceError(mention, candidates) from error
                validated_paths.append(
                    resolve_project_file(context.project_root, candidates[0])
                )

        relative_paths = [
            path.relative_to(context.project_root.resolve()).as_posix()
            for path in validated_paths
        ]
        mention_list = "\n".join(f"- {path}" for path in relative_paths)
        user_input = (
            f"{user_input}\n\n"
            "The user referenced these files in the selected project:\n"
            f"{mention_list}\n"
            "Read each exact path with read_project_file before answering. "
            "If a path is invalid or unavailable, explain that; do not guess "
            "a substitute."
        )

    agent_input: Any = {"messages": [{"role": "user", "content": user_input}]}
    while True:
        interrupts: list[Any] = []
        async for mode, chunk in agent.astream(
            agent_input,
            config=config,
            context=context,
            stream_mode=["messages", "updates"],
        ):
            if mode == "updates" and isinstance(chunk, dict):
                if "__interrupt__" in chunk:
                    interrupt_values = chunk["__interrupt__"]
                    if not isinstance(interrupt_values, tuple) or not interrupt_values:
                        raise ToolExecutionError(
                            "The agent returned an invalid review interruption."
                        )
                    interrupts.extend(interrupt_values)
                continue

            if mode != "messages":
                continue
            message = chunk[0]
            if not isinstance(message, (AIMessage, AIMessageChunk)):
                continue

            content = message.content
            if isinstance(content, str):
                if content:
                    yield content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        yield block
                    elif isinstance(block, dict):
                        text = block.get("text")
                        if isinstance(text, str):
                            yield text

        if not interrupts:
            return

        decisions: dict[str, dict[str, bool]] = {}
        for interruption in interrupts:
            review = _review_from_interrupt(interruption.value)
            approved = edit_review(review) if edit_review is not None else False
            decisions[interruption.id] = {"approved": approved is True}

        if len(decisions) == 1:
            agent_input = Command(resume=next(iter(decisions.values())))
        else:
            agent_input = Command(resume=decisions)
