"""Coordinate folder selection and the command-line conversation."""

from httpx import HTTPError
from langchain_core.exceptions import (
    ModelAuthenticationError,
    ModelConnectionError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from langchain_core.runnables import RunnableConfig

from app.agent.agent import create_codebase_agent
from app.cli.input_handler import (
    choose_file_candidate,
    choose_project_root,
    get_input,
)
from app.core.context import ProjectContext
from app.core.exceptions import (
    AmbiguousFileReferenceError,
    ConfigurationError,
    DevAIError,
)
from app.services.agent_service import FileEditReview, stream_agent_response


def _report_request_error(message: str) -> None:
    """Print a failure on a fresh line when streamed output may be in progress."""
    print(f"\n{message}")


def _review_file_edit(review: FileEditReview) -> bool:
    """Show a proposed diff and require an explicit yes before applying it."""
    print(f"\nProposed edit: {review.file_path}")
    print(f"Summary: {review.summary}")
    print(review.diff, end="" if review.diff.endswith("\n") else "\n")
    answer = input("Apply this edit? [y/N]: ").strip().casefold()
    approved = answer in {"y", "yes"}
    if not approved:
        print("Edit rejected. DevAI did not apply this proposal.")
    return approved


async def start_cli() -> None:
    """Start a conversation using the project folder selected at startup."""
    print("\nDevAI Codebase Assistant")
    project_root = choose_project_root()

    if project_root is None:
        print("Folder selection canceled.")
        return

    context = ProjectContext(project_root=project_root)
    try:
        agent = create_codebase_agent(project_root)
    except ConfigurationError as error:
        _report_request_error(f"DevAI configuration error: {error}")
        return
    config: RunnableConfig = {"configurable": {"thread_id": "user-1"}}

    print(f"Project folder: {project_root}")
    print("Ask a question, or type 'exit' to quit.\n")

    while True:
        question = get_input().strip()

        if question.casefold() in {"exit", "quit"}:
            print("Goodbye!")
            return

        if not question:
            print("Please enter a question.")
            continue

        file_choices: dict[str, str] = {}
        while True:
            try:
                async for text_chunk in stream_agent_response(
                    agent,
                    question,
                    config,
                    context,
                    file_choices,
                    _review_file_edit,
                ):
                    print(text_chunk, end="", flush=True)
                print()
                break
            except AmbiguousFileReferenceError as error:
                selected_path = choose_file_candidate(
                    error.file_name,
                    error.candidates,
                )
                if selected_path is None:
                    print("File selection canceled.")
                    break
                file_choices[error.file_name] = selected_path
            except ModelAuthenticationError as error:
                _report_request_error(
                    "DevAI could not authenticate with the model provider. "
                    "Check GOOGLE_API_KEY in .env and confirm the key is valid. "
                    f"Details: {error}"
                )
                break
            except ModelRateLimitError as error:
                _report_request_error(
                    "The model provider rate limit or quota was reached. "
                    f"Wait and try again, or check your provider account. Details: {error}"
                )
                break
            except (
                HTTPError,
                ModelConnectionError,
                ModelTimeoutError,
                TimeoutError,
            ) as error:
                _report_request_error(
                    "DevAI could not reach the model provider in time. "
                    f"Check your connection and try again. Details: {error}"
                )
                break
            except ModelError as error:
                _report_request_error(
                    f"The model provider could not complete the request: {error}"
                )
                break
            except FileNotFoundError as error:
                _report_request_error(
                    f"DevAI could not find the requested project file: {error}"
                )
                break
            except PermissionError as error:
                _report_request_error(
                    f"DevAI does not have permission to access that project file: {error}"
                )
                break
            except DevAIError as error:
                _report_request_error(f"DevAI could not complete the request: {error}")
                break
            except OSError as error:
                _report_request_error(
                    "A file-system operation failed while handling the request. "
                    "Check the project files and permissions before retrying. "
                    f"Details: {error}"
                )
                break
