import logging
import os
import signal
import time

from typing import Any, Optional

import redis

from flask import Flask
from tasks import MyTaskManager

# Setup Redis connection and logging
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
    """Retrieve an item from the Redis queue."""
    item = redis_client.lpop(queue_name)
    if item:
        log.info(f"Removed {item.decode('utf-8')} from queue {queue_name}")
        return item.decode("utf-8")
    log.info(f"Queue {queue_name} is empty")
    return None


def signal_handler(signum: int, frame: Optional[int]):
    """Signal handler to ensure clean shutdown."""
    log.info(f"Received signal {signum}, shutting down...")
    task_manager.stop()
    os._exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.route("/")
def api() -> str:
    return "Select an endpoint for your request:<br>Remember to replace `[TASK_ID]` by the desired task id."


@app.route("/research/<research>")
def research_name(research: str) -> dict[str, Any]:
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
        timeout = 25
        max_timeout = 300  # Maximum timeout limit to prevent infinite loops

        while timeout <= max_timeout:
            try:
                result = task.result.get(task_id, timeout=timeout)
                status = task.result.status(task_id)
                message_details.append(
                    f"{step} task {task_id} completed with result: {result}, status: {status}"
                )
                break
            except TimeoutError:
                log.info(
                    f"Task {task_id} timed out. Retrying with increased timeout..."
                )
                timeout *= 2  # Double the timeout for the next retry
            except Exception as e:
                message_details.append(
                    f"{step} task {task_id} failed with error: {e}"
                )
                break

    return {"message": " ".join(message_details)}


def check_task_completion(
    task, task_id, initial_timeout=25, extended_timeout=300
):
    """Check the completion of a task with extended timeout if needed."""
    start_time = time.time()
    timeout = initial_timeout
    while time.time() - start_time < extended_timeout:
        try:
            result = task.result.get(task_id, timeout=timeout)
            return result, task.result.status(task_id)
        except TimeoutError:
            log.info(f"Extending timeout for task {task_id}.")
            timeout = min(
                timeout * 2, extended_timeout - (time.time() - start_time)
            )
        except Exception as e:
            log.error(f"Failed to get result for task {task_id} due to: {e}")
            return None, "FAILURE"
    return None, "TIMEOUT"


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
