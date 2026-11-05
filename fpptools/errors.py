import click


class FppToolsError(click.ClickException):
    """User-facing error: printed as 'Error: ...' with exit code 1, no traceback."""
