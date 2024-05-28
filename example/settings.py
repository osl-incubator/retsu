"""Settings used by the example."""

import os

from pathlib import Path

RESULTS_PATH = Path(__file__).parent / "results"
os.makedirs(RESULTS_PATH, exist_ok=True)
