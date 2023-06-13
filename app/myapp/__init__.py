from flask import Flask
from celery import Celery
from celery.contrib.abortable import AbortableTask

from time import sleep

def make_celery(app):
    celery = Celery(app.name)
    celery.conf.update(app.config["CELERY_CONFIG"])

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

def create_app():
    app = Flask(__name__)
    app.config.update(CELERY_CONFIG={
        'broker_url': 'redis://localhost:6379',
        'result_backend': 'redis://localhost:6379'
    })

    celery = make_celery(app)

    @celery.task(bind=True, base=AbortableTask)
    def count(self, count):
        for i in range(count):
            print(i)
            print(self.is_aborted())
            if self.is_aborted():
                return "task revoke"
            sleep(0.1)

        return "done"


    @app.route("/")
    def start():
        task = count.delay(100)
        return {
            "task_id": task.task_id,
            "cancel": f"http://localhost:5000/cancel/{task.task_id}"
        }
    
    @app.route("/cancel/<task_id>")
    def cancel(task_id):
        task = count.AsyncResult(task_id)
        # task.revoke(terminate=True)
        task.abort()
        return {
            "status": "task cancel"
        }
    

    return app, celery

