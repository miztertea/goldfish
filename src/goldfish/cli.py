import json
import os
import shutil
import subprocess as sp
import sys
from io import TextIOWrapper
from pathlib import Path

# Windows default encoding (cp1252) cannot represent ✓/✗ — reconfigure at startup
if sys.platform == "win32":
    if isinstance(sys.stdout, TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if isinstance(sys.stderr, TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer

from goldfish import drain, hook
from goldfish.claude_md import DEFAULT_SETTINGS, register_hooks
from goldfish.config import VAULTS_ROOT, get_manifest, project_name, write_manifest
from goldfish.drain import QUEUE_PATH
from goldfish.miner import mine_project

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
    try:
        result = sp.run(["omega", "status"], capture_output=True, check=False)
        if result.returncode == 0:
            typer.echo("✓ OMEGA responsive")
        else:
            typer.echo("✗ OMEGA not responding — run: omega setup")
            ok = False
    except FileNotFoundError:
        typer.echo("✗ OMEGA not found — run: uv tool install omega-memory")
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

    # Semble check
    if shutil.which("semble"):
        typer.echo("✓ Semble")
    else:
        typer.echo("✗ Semble not found — run: uv tool install semble")
        ok = False

    # MCP registration check
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        try:
            mcp_data = json.loads(claude_json.read_text())
            mcp = mcp_data.get("mcpServers", {})
            for name in ("omega-memory", "semble", "gitnexus"):
                status = "✓" if name in mcp else "✗"
                if status == "✗":
                    typer.echo(f"{status} {name} MCP  — run: goldfish init to register")
                    ok = False
                else:
                    typer.echo(f"{status} {name} MCP")
        except Exception:
            typer.echo("✗ ~/.claude.json malformed — run: goldfish init")
            ok = False
    else:
        typer.echo("  ~/.claude.json not found — run: goldfish init")

    # Vault health check
    project = project_name(cwd)
    vault = VAULTS_ROOT / project
    expected_dirs = ["Memory/Decisions", "Memory/Lessons", "Memory/Errors", "Tasks", "Specs", "_context"]
    for d in expected_dirs:
        exists = (vault / d).exists()
        if exists:
            typer.echo(f"✓ vault/{d}")
        else:
            typer.echo(f"✗ vault/{d}")
            ok = False

    if ok:
        typer.echo("\nAll checks passed.")
    else:
        typer.echo("\nSome checks failed. See above for fix instructions.")
        raise typer.Exit(1)


@app.command(name="register-hooks")
def register_hooks_cmd() -> None:
    """Update Claude Code hook registrations with the correct goldfish binary path."""
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

    manifest = get_manifest(project, vaults_root=VAULTS_ROOT)
    resume_file = manifest.get("last_jsonl_file", "")
    resume_offset = manifest.get("last_byte_offset", 0)

    # Sort by mtime so we process oldest transcripts first
    jsonl_files = sorted(
        jsonl_dir.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime,
    )

    resume_path = jsonl_dir / resume_file if resume_file else None
    # If resume file no longer exists (e.g., logs rotated), start from the beginning.
    if resume_path and not resume_path.exists():
        resume_path = None
    past_resume = resume_path is None

    total = 0

    for jsonl_file in jsonl_files:
        if not past_resume:
            if jsonl_file == resume_path:
                past_resume = True
            else:
                # File is older than the resume point — already fully processed
                continue

        start = 0
        if resume_path and jsonl_file == resume_path:
            start = resume_offset

        typer.echo(f"Replaying {jsonl_file.name} (offset {start})...")

        with open(jsonl_file, "rb") as f:
            f.seek(start)
            content = f.read().decode("utf-8", errors="replace")

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                drain._route(event)
                total += 1
            except Exception:
                pass

        new_offset = jsonl_file.stat().st_size
        manifest = get_manifest(project, vaults_root=VAULTS_ROOT)
        write_manifest(
            project,
            {
                **manifest,
                "last_byte_offset": new_offset,
                "last_jsonl_file": jsonl_file.name,
                "bootstrap_complete": True,
            },
            vaults_root=VAULTS_ROOT,
        )
        manifest = get_manifest(project, vaults_root=VAULTS_ROOT)

    typer.echo(f"Replay complete. Processed {total} events.")


@app.command()
def mine() -> None:
    """Seed OMEGA episodic memory from historical JSONL session logs."""
    import json as _json

    cwd = os.getcwd()
    settings = _json.loads(DEFAULT_SETTINGS.read_text()) if DEFAULT_SETTINGS.exists() else {}
    from goldfish.miner import _find_hook_cmd

    auto_cmd = _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture")
    asst_cmd = _find_hook_cmd(settings, "Stop", "assistant_capture")
    if not auto_cmd and not asst_cmd:
        typer.echo("OMEGA hooks not registered — run: goldfish init")
        raise typer.Exit(1)

    typer.echo("Mining sessions from ~/.claude/projects/...")
    n = mine_project(cwd, _settings=settings)
    if n == 0:
        typer.echo("No new sessions to mine.")
    else:
        typer.echo(f"Done. {n} session(s) mined into OMEGA memory.")
