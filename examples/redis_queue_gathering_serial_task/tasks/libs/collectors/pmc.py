from datetime import datetime


class PMCCollector:
    """PMCCollector."""

    def __init__(self) -> None:
        """Initialize EmBaseCollector."""
        pass

    def get_max_articles(
        self, search: str, begin: datetime.date, end: datetime.date
    ) -> int:
        """Get max number of articles."""
        return 800
