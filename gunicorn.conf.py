"""
Gunicorn config for multi-worker production deployment (Linux / Mac).
Usage: gunicorn -c gunicorn.conf.py troubleir.api.main:app
"""
import multiprocessing
import os

# Each request is async (uvicorn worker class), not blocking threads
worker_class = "uvicorn.workers.UvicornWorker"

# Default: (2 * CPU cores) + 1, capped at 8. Override with WORKERS env var.
workers = int(os.environ.get("WORKERS", min((2 * multiprocessing.cpu_count()) + 1, 8)))

# Load the app in the master process BEFORE forking workers.
# Sentence Transformers model and all indexes are loaded once here,
# then inherited by all workers via copy-on-write, no redundant downloads.
preload_app = True

bind = os.environ.get("BIND", "0.0.0.0:8000")
timeout = 120        # Groq calls can take up to ~30s; give headroom
keepalive = 5
accesslog = "-"      # stdout
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
