import uvicorn

from fastpost.factory import current_app
from fastpost.settings import get_settings

settings = get_settings()
app = current_app

if __name__ == "__main__":
    uvicorn.run(
        "main:app", port=8000, debug=settings.DEBUG, reload=settings.DEBUG,
    )
