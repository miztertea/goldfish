import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from goldfish.config import VAULTS_ROOT, get_manifest, project_name, write_manifest
from goldfish.vault import read_note, scaffold, write_note

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def _run(cmd: list, **kwargs) -> Optional[subprocess.CompletedProcess]:
    """Run subprocess, returning None if the binary is not found."""
    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        return None


def drain(queue: Path = QUEUE_PATH, budget_ms: float = 0) -> int:
    """Process queued events. budget_ms=0 means no time limit."""
    if not queue.exists():
        return 0
    lines = queue.read_text().splitlines()
    processed = 0
    failed: list[str] = []
    unprocessed: list[str] = []
    deadline = time.monotonic() + budget_ms / 1000 if budget_ms > 0 else None

    for i, raw_line in enumerate(lines):
        if deadline and time.monotonic() >= deadline:
            unprocessed = lines[i:]
            break
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            failed.append(raw_line)
            continue
        try:
            _route(event)
            processed += 1
        except Exception:
            failed.append(raw_line)

    leftover = failed + unprocessed
    queue.write_text("\n".join(leftover) + "\n" if leftover else "")
    return processed


def _route(event: dict) -> None:
    handler = _HANDLERS.get(event.get("type", ""))
    if handler:
        handler(event)


def _handle_stop(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    session_id = event.get("session_id", "unknown")
    _run(["omega", "flush", session_id], capture_output=True, check=False)

    jsonl_file_path = event.get("jsonl_file", "")
    if jsonl_file_path:
        try:
            cwd = event.get("cwd", ".")
            project = project_name(cwd)
            offset = Path(jsonl_file_path).stat().st_size
            manifest = get_manifest(project, vaults_root=vaults_root)
            write_manifest(
                project,
                {**manifest, "last_byte_offset": offset, "last_jsonl_file": Path(jsonl_file_path).name},
                vaults_root=vaults_root,
            )
        except OSError:
            pass


def _handle_stop_event(event: dict) -> None:
    _handle_stop(event)


def _handle_session_end(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    wake_up = vaults_root / project / "_context" / "wake-up.md"
    if wake_up.exists():
        wake_up.unlink()


def _handle_post_tool_use(event: dict) -> None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    if tool in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            _run(["semble", "reindex", file_path], capture_output=True, check=False)
    elif tool == "Bash":
        cmd = tool_input.get("command", "")
        if cmd.strip().startswith("git commit"):
            session_id = event.get("session_id", "unknown")
            _run(["omega", "note", "git_commit", session_id], capture_output=True, check=False)


def _handle_subagent_stop(event: dict) -> None:
    session_id = event.get("session_id", "unknown")
    _run(["omega", "flush", session_id], capture_output=True, check=False)


def _handle_task_created(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    task_id = event.get("task_id", "unknown")
    session_id = event.get("session_id", "unknown")
    write_note(
        project,
        f"Tasks/{task_id}.md",
        {
            "id": f"task-{task_id}",
            "type": "task",
            "valid_from": _today(),
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": session_id,
            "source_offset": get_manifest(project, vaults_root=vaults_root).get("last_byte_offset", 0),
            "related": [],
        },
        f"Task created: {event.get('task_description', task_id)}",
        vaults_root=vaults_root,
    )


def _handle_task_completed(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    task_id = event.get("task_id", "unknown")
    task_path = f"Tasks/{task_id}.md"
    note_file = vaults_root / project / task_path
    if note_file.exists():
        fm, body = read_note(project, task_path, vaults_root=vaults_root)
        write_note(project, task_path, fm, body.rstrip() + "\n\n**Completed.**", vaults_root=vaults_root)
    else:
        _handle_task_created(event, vaults_root=vaults_root)


def handle_session_start(event: dict, vaults_root: Path = VAULTS_ROOT) -> str:
    drain(budget_ms=200)
    cwd = event.get("cwd", ".")
    session_id = event.get("session_id", "unknown")
    project = project_name(cwd)
    manifest = get_manifest(project, vaults_root=vaults_root)

    jsonl_dir = Path.home() / ".claude" / "projects" / cwd.replace("/", "-")

    if not manifest.get("bootstrap_complete", False):
        # New project — scaffold vault, index code, mine history, write wake-up
        scaffold(project, vaults_root=vaults_root)

        src_dir = Path(cwd) / "src"
        index_dir = src_dir if src_dir.exists() else Path(cwd)
        result = _run(["semble", "index", str(index_dir)], capture_output=True, check=False)
        if result is not None and result.returncode == 0:
            manifest = get_manifest(project, vaults_root=vaults_root)
            write_manifest(
                project,
                {**manifest, "semble_indexed_at": datetime.utcnow().isoformat()},
                vaults_root=vaults_root,
            )

        if jsonl_dir.exists():
            _run(["omega", "mine", str(jsonl_dir)], capture_output=True, check=False)

        body = (
            "# Wake-up — First Session\n\n"
            "This is the first Goldfish session for this project. "
            "Vault scaffolded and initial index complete.\n"
        )
        frontmatter = {
            "id": f"wake-up-{session_id}",
            "type": "checkpoint",
            "valid_from": _today(),
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": session_id,
            "source_offset": manifest.get("last_byte_offset", 0),
            "related": [],
        }
        write_note(project, "_context/wake-up.md", frontmatter, body, vaults_root=vaults_root)
        write_manifest(project, {**manifest, "bootstrap_complete": True}, vaults_root=vaults_root)
        return body

    else:
        # Existing project — mine incremental history and query OMEGA for context
        if jsonl_dir.exists():
            _run(["omega", "mine", str(jsonl_dir)], capture_output=True, check=False)

        src_dir = Path(cwd) / "src"
        reindex_target = str(src_dir) if src_dir.exists() else cwd
        reindex_result = _run(["semble", "reindex", reindex_target], capture_output=True, check=False)
        if reindex_result is not None and reindex_result.returncode == 0:
            manifest = get_manifest(project, vaults_root=vaults_root)
            write_manifest(
                project,
                {**manifest, "semble_indexed_at": datetime.utcnow().isoformat()},
                vaults_root=vaults_root,
            )

        result = _run(
            ["omega", "query", "current project state tasks decisions"],
            capture_output=True,
            check=False,
            text=True,
        )
        memory_context = result.stdout.strip() if result and result.returncode == 0 else ""

        body = "# Wake-up\n\n"
        if memory_context:
            body += f"## Memory Context\n\n{memory_context}\n"
        else:
            body += "No prior memory context found.\n"

        tasks_dir = vaults_root / project / "Tasks"
        open_tasks = []
        if tasks_dir.exists():
            for note_file in sorted(f for f in tasks_dir.iterdir() if f.suffix == ".md")[-10:]:
                note_text = note_file.read_text(encoding="utf-8")
                if "**Completed.**" not in note_text:
                    open_tasks.append(note_file.stem)

        decisions_dir = vaults_root / project / "Memory" / "Decisions"
        recent_decisions = []
        if decisions_dir.exists():
            files = sorted(
                (f for f in decisions_dir.iterdir() if f.suffix == ".md"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for f in files[:3]:
                lines = f.read_text(encoding="utf-8").splitlines()
                heading = next((l for l in lines if l.startswith("# ")), f.stem)
                recent_decisions.append(heading.lstrip("# "))

        if open_tasks:
            body += "\n## Open Tasks\n\n" + "\n".join(f"- {t}" for t in open_tasks) + "\n"
        if recent_decisions:
            body += "\n## Recent Decisions\n\n" + "\n".join(f"- {d}" for d in recent_decisions) + "\n"

        frontmatter = {
            "id": f"wake-up-{session_id}",
            "type": "checkpoint",
            "valid_from": _today(),
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": session_id,
            "source_offset": manifest.get("last_byte_offset", 0),
            "related": [],
        }
        write_note(project, "_context/wake-up.md", frontmatter, body, vaults_root=vaults_root)
        return body


def handle_pre_compact(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    drain(budget_ms=200)
    cwd = event.get("cwd", ".")
    session_id = event.get("session_id", "unknown")
    project = project_name(cwd)

    _run(["omega", "flush", session_id], capture_output=True, check=False)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    frontmatter = {
        "id": f"checkpoint-{session_id}-{ts}",
        "type": "checkpoint",
        "valid_from": _today(),
        "superseded_by": None,
        "confidence": 1.0,
        "source_session": session_id,
        "source_offset": get_manifest(project, vaults_root=vaults_root).get("last_byte_offset", 0),
        "related": [],
    }
    body = f"# Checkpoint — {session_id}\n\nPre-compact snapshot at {ts}.\n"
    write_note(
        project,
        f"Memory/Checkpoints/{session_id}-{ts}.md",
        frontmatter,
        body,
        vaults_root=vaults_root,
    )


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


_HANDLERS: dict = {
    "Stop": _handle_stop_event,
    "SessionEnd": _handle_session_end,
    "PostToolUse": _handle_post_tool_use,
    "SubagentStop": _handle_subagent_stop,
    "TaskCreated": _handle_task_created,
    "TaskCompleted": _handle_task_completed,
}


def main() -> None:
    count = drain()
    print(f"Drained {count} events")


if __name__ == "__main__":
    main()
