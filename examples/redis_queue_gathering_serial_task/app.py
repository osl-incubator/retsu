import logging
import os
import signal
import time

from datetime import datetime
from typing import Any, Optional

import redis

from flask import Flask
from tasks import MyTaskManager

# Setup Redis connection and logging
redis_client = redis.Redis(host="localhost", port=6379, db=0)
log = logging.getLogger(__name__)
# logging.basicConfig(level=logging.ERROR)]

# Configure logging to display errors and custom formatted warnings
logging.basicConfig(level=logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s: %(levelname)s/MainProcess] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)

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
        item_decoded = item.decode("utf-8")
        log.info(f"Removed {item_decoded} from queue {queue_name}")
        return item_decoded
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
    """Provide API information."""
    return "Select an endpoint for your request:<br>Remember to replace `[TASK_ID]` by the desired task id."


@app.route("/research/<research>")
def research_name(research: str) -> dict[str, Any]:
    """Handle research requests by processing a series of tasks sequentially."""
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
        result, status = check_task_completion(
            task_manager.get_task(step), task_id
        )
        if status != "completed":
            log.info(
                f"Re-enqueueing {step} task {task_id} due to non-completion."
            )
            add_to_queue(queue_name, f"{step}:{task_id}")  # Re-enqueue task
        else:
            message_details.append(
                f"{step} task {task_id} completed with result: {result}, status: {status}"
            )

    return {"message": " ".join(message_details)}


def check_task_completion(
    task, task_id, initial_timeout=25, extended_timeout=300
):
    """Check task completion with extended timeout."""
    timeout = initial_timeout
    start_time = time.time()

    while time.time() - start_time < extended_timeout:
        try:
            result = task.result.get(task_id, timeout=timeout)
            return result, task.result.status(task_id)
        except TimeoutError:
            timeout = min(
                extended_timeout - (time.time() - start_time), timeout * 2
            )
            log.info(
                f"Extended timeout for task {task_id} to {timeout} seconds."
            )
        except Exception as e:
            log.warning(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {e}: {task_id}"
            )
            return None, "failed"

    return None, "timeout"


if __name__ == "__main__":
    try:
        app.run(
            debug=False,
            passthrough_errors=True,
            use_debugger=False,
            use_reloader=False,
        )

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
