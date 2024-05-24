import asyncio
import os
import signal

from flask import Flask
from settings import RESULTS_PATH
from tasks import TaskA1

app = Flask(__name__)

tasks = []  # List to keep track of all Task instances

def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    for task in tasks:
        task.terminate()
    # Perform any other cleanup here if necessary
    os._exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

task1 = TaskA1(result_path=RESULTS_PATH)
tasks.append(task1)


@app.route("/<int:a>/<int:b>")
def api():
    key = task1.request(a=1, b=1)
    return f"your task ({key}) is running now, please wait until it is done."


@app.route("/status/<string:task_id>")
def status(task_id: str):
    _status = task1.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/result/<string:task_id>")
def result(task_id: str):
    return task1.get_result(task_id)


if __name__ == "__main__":
    try:
        app.run()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
