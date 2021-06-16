from fastpost.factory import create_app
from fastpost.settings import get_settings

settings = get_settings()
main_app = create_app(settings)
