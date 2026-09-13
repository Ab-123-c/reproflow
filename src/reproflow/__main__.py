"""Allow ``python -m reproflow`` to invoke the CLI."""

from .cli import app


if __name__ == "__main__":
    app()
