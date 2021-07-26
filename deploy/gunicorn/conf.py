import os
from core.settings import settings

debug = settings.DEBUG
reload = debug
workers = settings.WORKERS if not debug else 1
worker_class = 'uvicorn.workers.UvicornWorker'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Gunicorn config variables
bind = "0.0.0.0:8000"
graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "120"))
timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = int(os.getenv("KEEP_ALIVE", "5"))
