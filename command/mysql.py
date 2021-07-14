import shlex
import subprocess
from functools import partial

import typer
from fastpost.settings import settings

db_typer = typer.Typer(short_help="MySQL相关")

shell = partial(subprocess.run, shell=True)


@db_typer.command("create", short_help="创建数据库")
def create_db():
    shell(
        'mysql -h {host} --port={port} -u{user} -p{password} -e '
        '"CREATE DATABASE IF NOT EXISTS \\`{database}\\` default character set utf8mb4 collate utf8mb4_general_ci;"'.format(
            **settings.TORTOISE_ORM_CONFIG.get("connections").get("default").get("credentials")
        )
    )


@db_typer.command("drop", short_help="删除数据库")
def drop_db():
    shell(
        'mysql -h {host} --port={port} -u{user} -p{password} -e '
        '"DROP DATABASE \\`{database}\\`;"'.format(
            **settings.TORTOISE_ORM_CONFIG.get("connections").get("default").get("credentials"))
    )


@db_typer.command("init-config", short_help="初始化数据库配置")
def init_config():
    shell("aerich init -t db.mysql.TORTOISE_ORM_CONFIG")


@db_typer.command("init", short_help="初始化数据库")
def init_db():
    shell("aerich init-db")


@db_typer.command("migrate", short_help="生成迁移文件")
def db_make_migrations(message: str = typer.Option(default=None, help="迁移文件备注")):
    proc = subprocess.Popen(shlex.split("aerich migrate --name {remark}".format(remark=message)),
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    print(stdout.decode("utf-8") if stdout else "")


@db_typer.command("upgrade", short_help="执行迁移文件")
def db_upgrade():
    shell("aerich upgrade")


@db_typer.command("head", short_help="最新版本")
def db_migration_head():
    shell("aerich heads")


@db_typer.command("history", short_help="历史版本")
def db_history():
    shell("aerich history")


@db_typer.command("downgrade", short_help="回退版本")
def db_downgrade():
    shell("aerich upgrade")
