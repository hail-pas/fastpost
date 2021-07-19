import time

from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware


async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


roster = [
    # Middleware Func
    add_process_time_header,
    # Middleware Class
    [
        CORSMiddleware,
        {"allow_origins": ["*"], "allow_credentials": True, "allow_methods": ["*"], "allow_headers": ["*"]},
    ],
]
