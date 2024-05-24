import asyncio

from flask import Flask
from settings import RESULTS_PATH
from tasks import TaskA1

app = Flask(__name__)

task1 = TaskA1(result_path=RESULTS_PATH)

@app.route("/")
def api():
    key = task1.request(a=1, b=1)
    return f"your task ({key}) is running now, please wait until it is done."


@app.route("/status/<task_id>")
def status(task_id: str):
    _status = task1.status(task_id)
    return {"status": _status, "task_id": task_id}


@app.route("/result/<task_id>")
def result(task_id: str):
    return task1.get_result(task_id)


if __name__ == "__main__":
    app.run()
