"""My retsu tasks."""

from __future__ import annotations

from time import sleep

import celery

from retsu.celery import SerialCeleryTask

from .config import app, redis_client


@app.task
def task_serial_a_plus_b(a: int, b: int, task_id: str) -> int:  # type: ignore
    """Define the task_serial_a_plus_b."""
    sleep(a + b)
    print("running task_serial_a_plus_b")
    result = a + b
    redis_client.set(f"serial-result-a-plus-b-{task_id}", result)
    return result


@app.task
def task_serial_result_plus_10(task_id: str) -> int:  # type: ignore
    """Define the task_serial_result_plus_10."""
    print("running task_serial_result_plus_10")
    previous_result = None
    while previous_result is None:
        previous_result = redis_client.get(f"serial-result-a-plus-b-{task_id}")
        sleep(1)

    previous_result_int = int(previous_result)
    result = previous_result_int + 10
    redis_client.set(f"serial-result-plus-10-{task_id}", result)
    return result


@app.task
def task_serial_result_square(results, task_id: str) -> int:  # type: ignore
    """Define the task_serial_result_square."""
    print("running task_serial_result_square")
    previous_result = None
    while previous_result is None:
        previous_result = redis_client.get(f"serial-result-plus-10-{task_id}")
        sleep(1)

    previous_result_int = int(previous_result)
    result = previous_result_int**2
    return result


class MySerialTask1(SerialCeleryTask):
    """MySerialTask1."""

    def request(self, a: int, b: int) -> str:
        """Receive the request for processing."""
        return super().request(a=a, b=b)

    def get_chord_tasks(
        self, a: int, b: int, task_id: str
    ) -> tuple[list[celery.Signature], celery.Signature]:
        """Define the list of tasks for celery chord."""
        return (
            [
                task_serial_a_plus_b.s(a, b, task_id),
                task_serial_result_plus_10.s(task_id),
            ],
            task_serial_result_square.s(task_id),
        )
"""Example of usage retsu with a celery app."""

import logging
import time

from typing import Any

import celery


# from .config import app, redis_client
from celery_app import app  # type: ignore
from retsu import TaskManager
from retsu.celery import ParallelCeleryTask, SerialCeleryTask

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

