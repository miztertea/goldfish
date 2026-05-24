import json
import os
import shutil
import subprocess as sp
from pathlib import Path

import typer

from goldfish import drain, hook
from goldfish.claude_md import DEFAULT_SETTINGS
from goldfish.config import get_manifest, project_name, write_manifest
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
    """Check goldfish configuration. Prints fix instructions for failures."""
    ok = True
    cwd = os.getcwd()

    # Node.js check
    if shutil.which("node"):
        typer.echo("✓ Node.js found")
    else:
        typer.echo("✗ Node.js missing — install from https://nodejs.org")
        ok = False

    # GitNexus index check
    gitnexus = Path(cwd) / ".gitnexus"
    if gitnexus.exists():
        typer.echo("✓ GitNexus index found")
    else:
        typer.echo("✗ .gitnexus/ not found — run: npx gitnexus analyze")
        ok = False

    # OMEGA check
    result = sp.run(["omega", "status"], capture_output=True, check=False)
    if result.returncode == 0:
        typer.echo("✓ OMEGA responsive")
    else:
        typer.echo("✗ OMEGA not responding — run: omega setup")
        ok = False

    # Hook registration check
    if DEFAULT_SETTINGS.exists():
        try:
            import json as _json
            data = _json.loads(DEFAULT_SETTINGS.read_text())
            hooks = data.get("hooks", {})
            has_goldfish = any(
                "goldfish" in str(h) and "hook" in str(h)
                for event_hooks in hooks.values()
                for group in event_hooks
                for h in group.get("hooks", [])
            )
            if has_goldfish:
                typer.echo("✓ Hooks registered in settings.json")
            else:
                typer.echo("✗ Hooks not registered — run: goldfish init")
                ok = False
        except Exception:
            typer.echo("✗ settings.json malformed — run: goldfish init")
            ok = False
    else:
        typer.echo("✗ ~/.claude/settings.json not found — run: goldfish init")
        ok = False

    # Queue depth check
    if QUEUE_PATH.exists():
        depth = len(QUEUE_PATH.read_text().splitlines())
        if depth > 100:
            typer.echo(f"⚠ Queue depth {depth} — run: goldfish drain")
        else:
            typer.echo(f"✓ Queue depth {depth}")
    else:
        typer.echo("✓ Queue empty")

    if ok:
        typer.echo("\nAll checks passed.")
    else:
        typer.echo("\nSome checks failed. See above for fix instructions.")
        raise typer.Exit(1)


@app.command(name="register-hooks")
def register_hooks_cmd() -> None:
    """Update Claude Code hook registrations with the correct goldfish binary path."""
    from goldfish.claude_md import register_hooks
    register_hooks(settings_path=DEFAULT_SETTINGS)
    typer.echo(f"Hooks registered in {DEFAULT_SETTINGS}")


@app.command()
def replay() -> None:
    """Rebuild vault from Claude Code JSONL transcripts. Resumable."""
    cwd = os.getcwd()
    project = project_name(cwd)
    encoded = cwd.replace("/", "-")
    jsonl_dir = Path.home() / ".claude" / "projects" / encoded

    if not jsonl_dir.exists():
        typer.echo(f"No transcript directory found at {jsonl_dir}")
        raise typer.Exit(1)

    manifest = get_manifest(project)
    total = 0

    for jsonl_file in sorted(jsonl_dir.glob("*.jsonl")):
        typer.echo(f"Replaying {jsonl_file.name}...")
        with jsonl_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    drain._route(event)
                    total += 1
                except Exception:
                    pass
            offset = f.tell()

        write_manifest(
            project,
            {**manifest, "last_byte_offset": offset, "last_jsonl_file": jsonl_file.name,
             "bootstrap_complete": True},
        )
        manifest = get_manifest(project)

    typer.echo(f"Replay complete. Processed {total} events.")
