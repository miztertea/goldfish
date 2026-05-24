import os

import typer

from goldfish import drain, hook
from goldfish.config import get_manifest, project_name
from goldfish.drain import QUEUE_PATH

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
    import os
    from goldfish.init import run as _init
    _init(cwd=os.getcwd())


@app.command()
def status() -> None:
    """Show queue depth, manifest state, and sync timestamps."""
    queue = QUEUE_PATH
    depth = len(queue.read_text().splitlines()) if queue.exists() else 0
    project = project_name(os.getcwd())
    manifest = get_manifest(project)

    typer.echo(f"Project:          {project}")
    typer.echo(f"Queue depth:      {depth} events")
    typer.echo(f"Bootstrap:        {'complete' if manifest.get('bootstrap_complete') else 'pending'}")
    typer.echo(f"Semble indexed:   {manifest.get('semble_indexed_at') or 'never'}")
    typer.echo(f"Last JSONL offset: {manifest.get('last_byte_offset', 0)}")


@app.command()
def doctor() -> None:
    """Check goldfish configuration and fix instructions."""
    typer.echo("doctor: not yet implemented")


@app.command()
def replay() -> None:
    """Rebuild vault from Claude Code JSONL transcripts."""
    typer.echo("replay: not yet implemented")
