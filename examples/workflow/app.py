"""Example of using Retsu with a Flask app."""

import logging
import os
import signal
import time

from typing import Any, Optional

import redis

from flask import Flask
from tasks import MyTaskManager

# Setup Redis connection
redis_client = redis.Redis(host="localhost", port=6379, db=0)
log = logging.getLogger(__name__)
task_manager = MyTaskManager()
task_manager.start()
app = Flask(__name__)


def add_to_queue(queue_name: str, item: str):
    """Add an item to the Redis queue."""
    redis_client.rpush(queue_name, item)
    log.info(f"Added {item} to queue {queue_name}")


def get_from_queue(queue_name: str) -> Optional[str]:
    """Get an item from the Redis queue."""
    item = redis_client.lpop(queue_name)
    if item:
        item_decoded = item.decode("utf-8")
        log.info(f"Removed {item_decoded} from queue {queue_name}")
        return item_decoded
    log.info(f"Queue {queue_name} is empty")
    return None


def signal_handler(signum: int, frame: Optional[int]) -> None:
    """Define signal handler."""
    log.info(f"Received signal {signum}, shutting down...")
    task_manager.stop()
    os._exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.route("/")
def api() -> str:
    """Define the root endpoint."""
    return (
        "Select an endpoint for your request:<br>"
        "Remember to replace `[TASK_ID]` by the desired task id."
    )


@app.route("/research/<research>")
def research_name(research: str) -> dict[str, Any]:
    """Endpoint to process research tasks sequentially."""
    research_steps = [
        "article",
        "preparing",
        "preprocessing",
        "clustering",
        "plotting",
        "cleaning",
    ]
    queue_name = f"research_tasks:{research}"

    for step in research_steps:
        task = task_manager.get_task(step)
        task_id = task.request(research)
        add_to_queue(queue_name, f"{step}:{task_id}")

    message_details = []
    while True:
        task_detail = get_from_queue(queue_name)
        if not task_detail:
            break
        step, task_id = task_detail.split(":")
        task = task_manager.get_task(step)
        start_time = time.time()
        timeout = 25
        extended_timeout = 50

        while time.time() - start_time < timeout + extended_timeout:
            try:
                result = task.result.get(task_id, timeout=timeout)
                status = task.result.status(task_id)
                message_details.append(
                    f"{step} task {task_id} completed with result: {result}, status: {status}"
                )
                break
            except TimeoutError:
                log.info(
                    f"Task {task_id} not completed within {timeout} seconds, extending timeout."
                )
                timeout = extended_timeout
            except Exception as e:
                log.error(
                    f"Failed to get result for task {task_id} due to {e}."
                )
                message_details.append(
                    f"{step} task {task_id} failed with error: {e}"
                )
                break
            time.sleep(5)

    return {"message": " ".join(message_details)}


if __name__ == "__main__":
    try:
        app.run(
            debug=True,
            passthrough_errors=True,
            use_debugger=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
