import uvicorn

from core.factory import current_app
from core.settings import settings

app = current_app

if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000, debug=settings.DEBUG, reload=settings.DEBUG,
    )
