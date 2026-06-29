"""DeepDraw entry point.

Forwards to the typer CLI in `deepdraw.cli`.
Equivalent to running `python -m deepdraw` or the installed `deepdraw` script.
"""
from deepdraw.cli import app

if __name__ == "__main__":
    app()
