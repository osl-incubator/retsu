"""Example of usage retsu with a flask app."""

import os
import signal

from time import sleep
from typing import Any, Optional

from flask import Flask
from tasks import MyProcessManager

app = Flask(__name__)

task_manager = MyProcessManager()
task_manager.start()


def signal_handler(signum: int, frame: Optional[int]) -> None:
    """Define signal handler."""
    print(f"Received signal {signum}, shutting down...")
    try:
        task_manager.stop()
    except Exception:
        ...
    # Perform any other cleanup here if necessary
    os._exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@app.route("/")
def api() -> str:
    """Define the root endpoint."""
    menu = """
    Select an endpoint for your request:

    * serial
    * parallel
    * status
    * result

    Example of endpoints:

    - http://127.0.0.1:5000/serial/1/2
    - http://127.0.0.1:5000/parallel/1/2
    - http://127.0.0.1:5000/serial/result/[TASK_ID]
    - http://127.0.0.1:5000/serial/status/[TASK_ID]
    - http://127.0.0.1:5000/parallel/result/[TASK_ID]
    - http://127.0.0.1:5000/parallel/status/[TASK_ID]

    Remember to replace `[TASK_ID]` by the desired process id.
    """.replace("\n", "<br/>")

    return menu


@app.route("/serial/<int:a>/<int:b>")
def serial(a: int, b: int) -> dict[str, Any]:
    """Define the serial endpoint."""
    task1 = task_manager.get_process("serial")
    key = task1.request(a=a, b=b)
    return {"message": f"Your process ({key}) is running now"}


@app.route("/parallel/<int:a>/<int:b>")
def parallel(a: int, b: int) -> dict[str, Any]:
    """Define the parallel endpoint."""
    task2 = task_manager.get_process("parallel")
    key = task2.request(a=a, b=b)
    return {"message": f"Your process ({key}) is running now"}


@app.route("/serial/status/<string:task_id>")
def serial_status(task_id: str) -> dict[str, Any]:
    """Define serial/status endpoint."""
    task1 = task_manager.get_process("serial")
    _status = task1.result.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/parallel/status/<string:task_id>")
def parallel_status(task_id: str) -> dict[str, Any]:
    """Define parallel/status endpoint."""
    task2 = task_manager.get_process("parallel")
    _status = task2.result.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/serial/result/<string:task_id>")
def serial_result(task_id: str) -> dict[str, Any]:
    """Define serial/result endpoint."""
    task1 = task_manager.get_process("serial")
    result = None
    for _ in range(10):
        try:
            # note: with no timeout
            result = task1.result.get(task_id)
            break
        except Exception:
            sleep(1)

    if result is None:
        return {"Error": "Result is not ready yet."}
    return {"result": result[0]}


@app.route("/parallel/result/<string:task_id>")
def parallel_result(task_id: str) -> dict[str, Any]:
    """Define parallel/result endpoint."""
    task2 = task_manager.get_process("parallel")

    try:
        # note: with timeout
        result = task2.result.get(task_id, timeout=10)
    except Exception:
        return {"Error": "Result is not ready yet."}

    return {"result": result[-1]}


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
