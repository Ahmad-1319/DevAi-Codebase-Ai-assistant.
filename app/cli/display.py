"""Functions for displaying messages to the person using the CLI."""


def display_welcome() -> None:
    """Show the initial greeting and basic usage hint."""
    print("\nDevAI Codebase Assistant")
    print("Ask something about your project, or type 'exit' to quit.\n")


def display_response(question: str, response: str) -> None:
    """Show a question and the assistant's response."""
    print(f"You asked: {question}\nResponse: {response}")


def display_goodbye() -> None:
    """Show a friendly message before the program exits."""
    print("Goodbye!")