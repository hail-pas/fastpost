import logging

from fastapi import FastAPI, APIRouter
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from tortoise.contrib.starlette import register_tortoise
from sentry_sdk.integrations.redis import RedisIntegration

from db.redis import AsyncRedisUtil
from core.globals import GlobalsMiddleware
from core.response import AesResponse
from core.settings import Settings, settings
from core.exceptions import ApiException

logger = logging.getLogger(__name__)


class MainApp(FastAPI):
    plugins = {}

    @property
    def settings(self) -> Settings:
        return settings


def amount_apps(main_app: FastAPI):
    from apps import roster

    for app_or_router, prefix_path, name in roster:
        assert prefix_path == "" or prefix_path.startswith("/"), "Routed paths must start with '/'"
        if isinstance(app_or_router, FastAPI):
            main_app.mount(prefix_path, app_or_router, name)
        elif isinstance(app_or_router, APIRouter):
            main_app.include_router(app_or_router)


def setup_exception_handlers(main_app: FastAPI):
    main_app.add_exception_handler(ApiException, lambda request, err: err.to_result())
    from core.exceptions import roster

    for handler in roster:
        main_app.add_exception_handler(HTTPException, handler)


def setup_middleware(main_app: FastAPI):
    """
    ./middlewares 文件中的定义中间件
    :param main_app:
    :return:
    """
    from inspect import isclass, isfunction

    from core.middlewares import roster

    for middle_fc in roster:
        try:
            if isfunction(middle_fc):
                main_app.add_middleware(BaseHTTPMiddleware, dispatch=middle_fc)
            elif isinstance(middle_fc, list):
                if isclass(middle_fc[0]):
                    if isinstance(middle_fc[1], dict):
                        main_app.add_middleware(middle_fc[0], **middle_fc[1])
                    else:
                        raise Exception(f"Require Dict as kwargs for middleware class, Got {type(middle_fc[1])}")
                else:
                    raise Exception(f"Require Class， But Got {type(middle_fc[0])}")
        except Exception as e:
            logger.exception(f"Set Middleware Failed: {middle_fc}, Encounter {e}")


def setup_static_app(main_app: FastAPI, current_settings: Settings):
    """
    init static app
    :param main_app:
    :param current_settings:
    :return:
    """
    static_files_app = StaticFiles(directory=current_settings.STATIC_DIR)
    main_app.mount(path=settings.STATIC_PATH, app=static_files_app, name="static")


def setup_sentry(current_settings: Settings):
    """
    init sentry
    :param current_settings:
    :return:
    """
    import sentry_sdk

    sentry_sdk.init(
        dsn=current_settings.SENTRY_DSN, environment=current_settings.ENVIRONMENT, integrations=[RedisIntegration()]
    )


def init_apps(main_app: FastAPI):
    @main_app.on_event("startup")
    async def init() -> None:
        # 初始化redis
        await AsyncRedisUtil.init()

    @main_app.on_event("shutdown")
    async def close() -> None:
        # 关闭redis
        await AsyncRedisUtil.close()


def create_app(current_settings: Settings):
    main_app = MainApp(
        debug=current_settings.DEBUG,
        title=current_settings.PROJECT_NAME,
        description=current_settings.DESCRIPTION,
        default_response_class=AesResponse,
        docs_url="/docs" if current_settings.DEBUG else None,
        redoc_url="/redoc",
        version="0.1.0",
    )
    # thread local just flask like g
    main_app.add_middleware(GlobalsMiddleware)
    # 挂载apps下的路由 以及 静态资源路由
    amount_apps(main_app)
    setup_static_app(main_app, current_settings)
    # 初始化全局 middleware
    setup_middleware(main_app)
    # 初始化全局 error handling
    setup_exception_handlers(main_app)
    # 注册 tortoise ORM
    register_tortoise(main_app, config=current_settings.TORTOISE_ORM_CONFIG)
    # 启停配置
    init_apps(main_app)
    # 初始化 sentry
    if settings.SENTRY_DSN:
        setup_sentry(current_settings)

    return main_app


current_app = create_app(current_settings=settings)
