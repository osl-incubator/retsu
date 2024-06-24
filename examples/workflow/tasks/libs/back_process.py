from time import sleep
from typing import Any


def back_process_articles(research: Any) -> Any:
    """Extract articles for a given research."""
    sleep(15)
    return f"Extracting articles for {research}"
