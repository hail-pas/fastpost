import typer

from command.db import db_typer

banner = """
-------  -----  ------- ------- ------- ------- ------- -------
|______ |_____| |______    |    |_____] |     | |______    |   
|       |     | ______|    |    |       |_____| ______|    | 
"""

cli = typer.Typer()

cli.add_typer(db_typer, name="db")

from command.shell import *  # noqa
