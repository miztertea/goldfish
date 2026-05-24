import typer
from goldfish import hook, drain

app = typer.Typer(no_args_is_help=True)


@app.command(name="hook")
def hook_cmd() -> None:
    """Read a Claude Code hook event from stdin and enqueue it."""
    hook.main()


@app.command(name="drain")
def drain_cmd() -> None:
    """Process queued events."""
    drain.main()


@app.command()
def init() -> None:
    """Install and configure all goldfish dependencies."""
    typer.echo("init: not yet implemented")


@app.command()
def status() -> None:
    """Show queue depth and tool health."""
    typer.echo("status: not yet implemented")


@app.command()
def doctor() -> None:
    """Check goldfish configuration and fix instructions."""
    typer.echo("doctor: not yet implemented")


@app.command()
def replay() -> None:
    """Rebuild vault from Claude Code JSONL transcripts."""
    typer.echo("replay: not yet implemented")
