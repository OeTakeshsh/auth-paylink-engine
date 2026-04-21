import os
import sys

print("=== BOOT START ===")
print("PYTHON:", sys.version)
print("CWD:", os.getcwd())

try:
    print("Importing celery app...")
    from app.workers.celery_app import celery_app
    print("Celery app imported OK")

    print("Registered tasks:", celery_app.tasks.keys())

except Exception as e:
    print("IMPORT ERROR:", repr(e))
    raise

print("=== STARTING WORKER ===")

celery_app.worker_main([
    "worker",
    "--loglevel=debug",
    "--concurrency=1",
])
