"""Read chat input and select the project folder from the terminal."""

import os
import stat
from pathlib import Path


def get_input() -> str:
    """Ask for one line of chat input."""
    return input("> ")


def choose_file_candidate(file_name: str, candidates: list[str]) -> str | None:
    """Ask the user to choose a matching project file, or cancel selection."""
    print(f"More than one project file is named {file_name!r}:")
    for index, candidate in enumerate(candidates, start=1):
        print(f"{index}. {candidate}")

    while True:
        choice = input("Choose a number, or type 'cancel': ").strip().casefold()
        if choice in {"cancel", "exit", "quit"}:
            return None

        try:
            selected_index = int(choice)
        except ValueError:
            print("Enter one of the listed numbers, or type 'cancel'.")
            continue

        if 1 <= selected_index <= len(candidates):
            return candidates[selected_index - 1]

        print("Choose a number from the list, or type 'cancel'.")


def _readable_directory(path: Path) -> Path:
    """Return a resolved, readable directory or raise a specific error."""
    resolved_path = path.resolve(strict=True)
    path_info = resolved_path.stat()

    if not stat.S_ISDIR(path_info.st_mode):
        raise NotADirectoryError(f"Not a folder: {resolved_path}")

    with os.scandir(resolved_path):
        pass

    return resolved_path


def choose_project_root() -> Path | None:
    """Return the selected readable project folder, or None if canceled."""
    default_path = Path.cwd()

    while True:
        choice = (
            input(
                f"Current project folder:\n{default_path}\n"
                "Press Enter or Y to use it, N to choose another, or type exit: "
            )
            .strip()
            .casefold()
        )

        if choice in {"", "y", "yes"}:
            candidate = default_path
        elif choice in {"n", "no"}:
            entered_path = input("Enter the project folder path: ").strip()

            if entered_path.casefold() in {"exit", "quit"}:
                return None

            if (
                len(entered_path) >= 2
                and entered_path[0] == entered_path[-1]
                and entered_path[0] in {"'", '"'}
            ):
                entered_path = entered_path[1:-1].strip()

            if not entered_path:
                print("Please enter a folder path.")
                continue

            candidate = Path(entered_path).expanduser()
        elif choice in {"exit", "quit"}:
            return None
        else:
            print("Choose Enter, Y, N, or exit.")
            continue

        try:
            return _readable_directory(candidate)
        except FileNotFoundError:
            print("That path does not exist. Try again.")
        except NotADirectoryError:
            print("That path is a file, not a folder. Try again.")
        except PermissionError:
            print("You do not have permission to read that folder.")
        except (OSError, RuntimeError, ValueError) as error:
            print(f"That folder could not be checked: {error}")
