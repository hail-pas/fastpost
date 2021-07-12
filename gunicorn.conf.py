import json
import os
from fastpost.settings import settings

host = "0.0.0.0"
port = "8000"
debug = settings.DEBUG
workers = settings.WORKERS
worker_class = 'uvicorn.workers.UvicornWorker'

# Gunicorn config variables
loglevel = os.getenv("LOG_LEVEL", "info")
bind = f"{host}:{port}"
errorlog = os.getenv("ERROR_LOG_DIR", "-")
accesslog = os.getenv("ACCESS_LOG_DIR", "-")
graceful_timeout = int(os.getenv("GRACEFUL_TIMEOUT", "120"))
timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = int(os.getenv("KEEP_ALIVE", "5"))

# For debugging and testing
log_data = {
    "loglevel": loglevel,
    "workers": workers,
    "bind": bind,
    "graceful_timeout": graceful_timeout,
    "timeout": timeout,
    "keepalive": keepalive,
    "errorlog": errorlog,
    "accesslog": accesslog,
    "host": host,
    "port": port,
}
print(json.dumps(log_data))
