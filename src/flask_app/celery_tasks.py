from celery import Celery

celery = Celery(
    "tasks", broker="redis://redis:6379", backend="redis://redis:6379"
)
