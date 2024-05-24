import asyncio
import os
import signal

from flask import Flask
from settings import RESULTS_PATH
from tasks import (
    MyParallelTask1,
    MyParallelTask2,
    MySerialTask1,
    MySerialTask2,
)

app = Flask(__name__)

tasks = {}  # List to keep track of all Task instances

def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    for task in tasks.values():
        try:
            task.terminate()
        except Exception:
            ...
    # Perform any other cleanup here if necessary
    os._exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

tasks["task1"] = MySerialTask1(result_path=RESULTS_PATH)
tasks["task2"] = MyParallelTask1(result_path=RESULTS_PATH)


@app.route("/")
def api():
    menu = """
    Select an endpoint for your request:

    * serial
    * parallel
    * status
    * result
    """

    return menu


@app.route("/serial/<int:a>/<int:b>")
def serial(a: int, b: int):
    task1 = tasks["task1"]
    key = task1.request(a=a, b=b)
    return f"your task ({key}) is running now, please wait until it is done."


@app.route("/parallel/<int:a>/<int:b>")
def parallel(a: int, b: int):
    task2 = tasks["task2"]
    key = task2.request(a=a, b=b)
    return f"your task ({key}) is running now, please wait until it is done."


@app.route("/serial/status/<string:task_id>")
def serial_status(task_id: str):
    task1 = tasks["task1"]
    _status = task1.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/parallel/status/<string:task_id>")
def parallel_status(task_id: str):
    task2 = tasks["task2"]
    _status = task2.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/serial/result/<string:task_id>")
def serial_result(task_id: str):
    task1 = tasks["task1"]
    return task1.get_result(task_id)


@app.route("/parallel/result/<string:task_id>")
def parallel_result(task_id: str):
    task2 = tasks["task2"]
    return task2.get_result(task_id)


if __name__ == "__main__":
    try:
        app.run()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
