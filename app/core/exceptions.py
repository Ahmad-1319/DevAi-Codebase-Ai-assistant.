"""Named errors that make application failures easier to understand."""


class DevAIError(Exception):
    """Base class for expected errors raised by the DevAI application."""


class ConfigurationError(DevAIError):
    """Raised when required application configuration is missing or invalid."""


class ToolExecutionError(DevAIError):
    """Raised when a codebase tool cannot complete its requested operation."""


class FileTooLargeError(ToolExecutionError):
    """Raised when a requested file exceeds the supported reading limit."""


class NonTextFileError(ToolExecutionError):
    """Raised when a requested file cannot be treated as UTF-8 text."""


class AmbiguousFileReferenceError(ToolExecutionError):
    """Raised when a file name matches multiple eligible project files."""

    def __init__(self, file_name: str, candidates: list[str]) -> None:
        self.file_name = file_name
        self.candidates = candidates
        super().__init__(f"More than one project file is named {file_name!r}.")
