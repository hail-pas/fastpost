from command import cli


async def init_ctx_db():
    import importlib
    from tortoise import Tortoise
    from tortoise.transactions import get_connection
    from core.settings import settings
    await Tortoise.init(config=settings.TORTOISE_ORM_CONFIG)
    main = importlib.import_module("__main__")
    ctx = main.__dict__
    ctx.update({"db": get_connection("shell")})


@cli.command("shell", short_help="命令行模式")
def shell():
    import importlib
    from IPython import start_ipython
    import cProfile
    import pdb
    from traitlets.config import Config

    # models = {cls.__name__: cls for cls in BaseModel.__subclasses__()}
    main = importlib.import_module("__main__")
    ctx = main.__dict__
    ctx.update(
        {
            # **models,
            "ipdb": pdb,
            "cProfile": cProfile,
        }
    )
    conf = Config()
    conf.InteractiveShellApp.exec_lines = [
        "print('System Ready!')",
        "from command.shell import init_ctx_db",
        "await init_ctx_db()",
    ]
    # DEBUG=10, INFO=20, WARN=30
    conf.InteractiveShellApp.log_level = 30
    conf.TerminalInteractiveShell.loop_runner = "asyncio"
    conf.TerminalInteractiveShell.colors = "neutral"
    conf.TerminalInteractiveShell.autoawait = True
    start_ipython(argv=[], user_ns=ctx, config=conf)
