"""Tasks for the example."""

from retsu import ProcessManager

from .get_max_article import ArXivGetMaxArticlesTask, PubMedGetMaxArticlesTask, MedrXivGetMaxArticlesTask, BiorXivGetMaxArticlesTask, EmbaseGetMaxArticlesTask, WebOfScienceGetMaxArticlesTask

# from .parallel import MyMultiProcess1
from .get_back_process import (
    ArticleTask,
    CleaningTask,
    ClusteringTask,
    PlottingTask,
    PreparingTask,
    PreprocessingTask,
)


class MyProcessManager(ProcessManager):
    """MyProcessManager."""

    def __init__(self) -> None:
        """Create a list of retsu tasks."""
        self.tasks = {
            "article": ArticleTask(),
            "cleaning": CleaningTask(),
            "clustering": ClusteringTask(),
            "plotting": PlottingTask(),
            "preparing": PreparingTask(),
            "preprocessing": PreprocessingTask(),
            # tasks.collectors.CollectorsGatheringTask(list(task_id))
            "ArXivGetMaxArticle": ArXivGetMaxArticlesTask(),
            "PubMedGetMaxArticle": PubMedGetMaxArticlesTask(),
            "MedrXivGetMaxArticle": MedrXivGetMaxArticlesTask(),
            "BiorXivGetMaxArticle": BiorXivGetMaxArticlesTask(),
            "EmbaseGetMaxArticle": EmbaseGetMaxArticlesTask(),
            "WebOfScienceGetMaxArticle": WebOfScienceGetMaxArticlesTask(),
        }
