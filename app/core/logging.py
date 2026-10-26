
"""Central place to configure application logging."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Set a simple logging format for the application.

    Call this once near startup. Modules should normally use
    ``logging.getLogger(__name__)`` instead of configuring logging themselves.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
