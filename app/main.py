"""Start the DevAI command-line application."""

import asyncio

from app.cli.interface import start_cli


async def main() -> None:
    """Run the asynchronous command-line interface."""
    await start_cli()


def cli() -> None:
    """Run the terminal application as an installed console command."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
