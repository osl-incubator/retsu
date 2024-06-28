"""Tasks for the example."""

from retsu import TaskManager

from .parallel import ArXivGetMaxArticlesTask

# from .parallel import MyParallelTask1
from .serial import (
    ArticleTask,
    CleaningTask,
    ClusteringTask,
    PlottingTask,
    PreparingTask,
    PreprocessingTask,
)


class MyTaskManager(TaskManager):
    """MyTaskManager."""

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks = {
            "article": ArticleTask(),
            "cleaning": CleaningTask(),
            "clustering": ClusteringTask(),
            "plotting": PlottingTask(),
            "preparing": PreparingTask(),
            "preprocessing": PreprocessingTask(),
            "ArXivGetMaxArticle": ArXivGetMaxArticlesTask(),
        }
