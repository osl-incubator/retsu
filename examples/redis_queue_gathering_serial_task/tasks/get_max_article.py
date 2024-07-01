"""Example of usage retsu with a celery app."""

import logging
from datetime import datetime
from typing import Any, Optional

import celery

from celery_app import app  # type: ignore

from retsu.celery import SingleCeleryProcess, MultiCeleryProcess

from .libs.collectors.arxiv import ArXivCollector


from .libs.collectors.biorxiv import BiorXivCollector
from .libs.collectors.embase import EmbaseRISCollector
from .libs.collectors.medrxiv import MedrXivCollector
from .libs.collectors.pubmed import PubMedCollector
from .libs.collectors.pmc import PMCCollector
from .libs.collectors.wos import WoSRISCollector


logger = logging.getLogger(__name__)


@app.task  # type: ignore
def task_arxiv_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = ArXivCollector()
    return collector.get_max_articles(search, begin, end)

@app.task  # type: ignore
def task_biorxiv_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = BiorXivCollector()
    return collector.get_max_articles(search, begin, end)

@app.task  # type: ignore
def task_embase_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = EmbaseRISCollector()
    return collector.get_max_articles(search, begin, end)

@app.task  # type: ignore
def task_medrxiv_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = MedrXivCollector()
    return collector.get_max_articles(search, begin, end)

@app.task  # type: ignore
def task_pubmed_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = PubMedCollector()
    return collector.get_max_articles(search, begin, end)

@app.task  # type: ignore
def task_pmc_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = PMCCollector()
    return collector.get_max_articles(search, begin, end)

@app.task  # type: ignore
def task_wos_get_max_articles(
    search: str, begin: datetime.date, end: datetime.date, task_id: str
) -> int:
    """Define the task for getting the max number of articles."""
    collector = WoSRISCollector()
    return collector.get_max_articles(search, begin, end)


class WebOfScienceGetMaxArticlesTask(SingleCeleryProcess):
    """Task for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")
        return [task_wos_get_max_articles.s(search, dt_begin, dt_end, task_id)]


class PubMedCentralGetMaxArticlesTask(SingleCeleryProcess):
    """Task for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")
        return [task_pmc_get_max_articles.s(search, dt_begin, dt_end, task_id)]


class PubMedGetMaxArticlesTask(SingleCeleryProcess):
    """Task for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")
        return [
                task_pubmed_get_max_articles.s(
                    search, dt_begin, dt_end, task_id
                )
            ]


class MedrXivGetMaxArticlesTask(SingleCeleryProcess):
    """Task for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")
        return [
                task_medrxiv_get_max_articles.s(
                    search, dt_begin, dt_end, task_id
                )
            ]


class EmbaseGetMaxArticlesTask(SingleCeleryProcess):
    """Task for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")
        return [
                task_embase_get_max_articles.s(
                    search, dt_begin, dt_end, task_id
                )
            ]


class BiorXivGetMaxArticlesTask(SingleCeleryProcess):
    """Task for the test."""

    def get_group_tasks(  # type: ignore
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")
        return [
                task_biorxiv_get_max_articles.s(
                    search, dt_begin, dt_end, task_id
                )
            ]


class ArXivGetMaxArticlesTask(SingleCeleryProcess):
    """Task to handle articles processing."""

    def get_group_tasks(
        self, *args, **kwargs
    ) -> list[celery.Signature]:
        """Define the list of tasks for celery chord."""
        search = kwargs.get("search")
        dt_begin = kwargs.get("begin")
        dt_end = kwargs.get("end")
        task_id = kwargs.get("task_id")

        return [task_arxiv_get_max_articles.s(search, dt_begin, dt_end, task_id)]

