"""Example of usage retsu with a celery app."""

import logging

from typing import Any

import celery

from celery_app import app  # type: ignore
from retsu.celery import SerialCeleryTask

from .libs.back_cleaning import clean_intermediate_files
from .libs.back_clustering import cluster_preprocessed_corpuses
from .libs.back_plotting import generate_plot
from .libs.back_preparing import prepare_corpuses
from .libs.back_preprocessing import preprocess_prepared_corpuses
from .libs.back_process import back_process_articles

logger = logging.getLogger(__name__)


@app.task
def task_preprocess_prepared_corpuses(research: Any, task_id: str) -> Any:
    """Preprocess corpuses for a given research."""
    return preprocess_prepared_corpuses(research)


@app.task
def task_prepare_corpuses(research: Any, task_id: str) -> Any:
    """Prepare corpuses for a given research."""
    return prepare_corpuses(research)


@app.task
def task_preprocess_prepared_corpuses(research: Any, task_id: str) -> Any:
    """Preprocess corpuses for a given research."""
    return preprocess_prepared_corpuses(research)


@app.task
def task_cluster_preprocessed_corpuses(research: Any, task_id: str) -> Any:
    """Cluster corpuses for a given research."""
    return cluster_preprocessed_corpuses(research)


@app.task
def task_clean_intermediate_files(research: Any, task_id: str) -> Any:
    """Clean intermediate files for a given research."""
    return clean_intermediate_files(research)


@app.task
def task_generate_plot(research: Any, task_id: str) -> Any:
    """Generate plot for a given research."""
    return generate_plot(research)


@app.task
def task_articles(research: Any, task_id: str) -> Any:
    """Extract articles for a given research."""
    return back_process_articles(research)


class ArticleTask(SerialCeleryTask):
    """Task to handle articles processing."""

    def get_group_tasks(
        self, research: Any, task_id: str
    ) -> list[celery.Signature]:
        return [task_articles.s(research, task_id)]


class PreparingTask(SerialCeleryTask):
    """Task to handle corpus preparation."""

    def get_group_tasks(
        self, research: Any, task_id: str
    ) -> list[celery.Signature]:
        return [
            task_prepare_corpuses.s(research, task_id),
        ]


class PreprocessingTask(SerialCeleryTask):
    """Task to handle corpus preprocessing."""

    def get_group_tasks(
        self, research: Any, task_id: str
    ) -> list[celery.Signature]:
        return [
            task_preprocess_prepared_corpuses.s(research, task_id),
        ]


class ClusteringTask(SerialCeleryTask):
    """Task to handle corpus clustering."""

    def get_group_tasks(
        self, research: Any, task_id: str
    ) -> list[celery.Signature]:
        return [
            task_cluster_preprocessed_corpuses.s(research, task_id),
        ]


class PlottingTask(SerialCeleryTask):
    """Task to handle corpus plotting."""

    def get_group_tasks(
        self, research: Any, task_id: str
    ) -> list[celery.Signature]:
        return [
            task_generate_plot.s(research, task_id),
        ]


class CleaningTask(SerialCeleryTask):
    """Task to handle corpus cleaning."""

    def get_group_tasks(
        self, research: Any, task_id: str
    ) -> list[celery.Signature]:
        return [
            task_clean_intermediate_files.s(research, task_id),
        ]
