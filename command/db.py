import asyncio

import typer
from alembic import command

from db import db
from fastpost.settings import get_settings

db_typer = typer.Typer(short_help="数据库相关")


async def init_models():
    async with db.engine.begin() as conn:
        # await conn.run_sync(db.drop_all)
        await conn.run_sync(db.create_all)


@db_typer.command("migrate", short_help="生成迁移文件")
def db_make_migrations(message: str = typer.Option(default=None, help="迁移文件备注")):
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, autogenerate=True, message=message)


@db_typer.command("upgrade", short_help="执行迁移文件")
def db_upgrade():
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, "head")


def get_alembic_config():
    from alembic.config import Config

    alembic_cfg = Config("./alembic.ini")
    alembic_cfg.set_main_option("script_location", "./migration")
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().POSTGRES_DATABASE_URL_ASYNC)
    return alembic_cfg
