from celery import Celery
from flask import Flask

app = Flask(__name__)
celery = Celery(
    "tasks", broker="redis://redis:6379", backend="redis://redis:6379"
)


@app.route("/")
def hello():
    result = celery.send_task("tasks.hello")
    return f"Hello, World! Celery task result: {result.get()}"


def run_dev():
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
