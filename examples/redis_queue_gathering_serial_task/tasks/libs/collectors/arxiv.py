from datetime import datetime


class ArXivCollector:
    """ArXivCollector."""

    def get_max_articles(
        self, search: str, begin: datetime.date, end: datetime.date
    ) -> int:
        """Get max number of articles."""
        return 750
