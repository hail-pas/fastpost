import asyncio
import importlib

from command import cli


@cli.command("shell", short_help="命令行模式")
def shell():
    from IPython import embed
    import cProfile
    import pdb
    from db import BaseModel, db

    models = {cls.__name__: cls for cls in BaseModel.__subclasses__()}
    main = importlib.import_module("__main__")
    ctx = main.__dict__
    ctx.update(
        {
            **models,
            # "session": session,
            "db": db,
            "ipdb": pdb,
            "cProfile": cProfile,
        }
    )
    embed(user_ns=ctx, banner2="", using="asyncio", colors="neutral")
