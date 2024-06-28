from typing import Any
import datetime


class EmbaseRISCollector:
    """EmbaseRISCollector."""

    def __init__(self) -> None:
        """Initialize EmBaseCollector."""
        pass

    def get_max_articles(
        self, search: str, begin: datetime.date, end: datetime.date
    ) -> int:
        """Get the max number of articles."""
        return 250