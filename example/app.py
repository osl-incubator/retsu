import os
import signal

from flask import Flask
from tasks import MyTaskManager

app = Flask(__name__)

task_manager = MyTaskManager()
task_manager.start()


def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    task_manager.stop()
    # Perform any other cleanup here if necessary
    os._exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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
    task1 = task_manager.get_task("serial")
    key = task1.request(a=a, b=b)
    return f"your task ({key}) is running now, please wait until it is done."


@app.route("/parallel/<int:a>/<int:b>")
def parallel(a: int, b: int):
    task2 = task_manager.get_task("parallel")
    key = task2.request(a=a, b=b)
    return f"your task ({key}) is running now, please wait until it is done."


@app.route("/serial/status/<string:task_id>")
def serial_status(task_id: str):
    task1 = task_manager.get_task("serial")
    _status = task1.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/parallel/status/<string:task_id>")
def parallel_status(task_id: str):
    task2 = task_manager.get_task("parallel")
    _status = task2.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/serial/result/<string:task_id>")
def serial_result(task_id: str):
    task1 = task_manager.get_task("serial")
    return task1.get_result(task_id)


@app.route("/parallel/result/<string:task_id>")
def parallel_result(task_id: str):
    task2 = task_manager.get_task("parallel")
    return task2.get_result(task_id)


if __name__ == "__main__":
    try:
        app.run()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
