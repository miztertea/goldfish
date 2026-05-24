import json
import subprocess
from datetime import datetime
from pathlib import Path

from goldfish.config import VAULTS_ROOT, get_manifest, project_name, write_manifest
from goldfish.vault import read_note, scaffold, write_note

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def drain(queue: Path = QUEUE_PATH) -> int:
    if not queue.exists():
        return 0
    lines = queue.read_text().splitlines()
    processed = 0
    failed: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            failed.append(line)
            continue
        try:
            _route(event)
            processed += 1
        except Exception:
            failed.append(line)
    queue.write_text("\n".join(failed) + "\n" if failed else "")
    return processed


def _route(event: dict) -> None:
    handler = _HANDLERS.get(event.get("type", ""))
    if handler:
        handler(event)


def _handle_stop(event: dict) -> None:
    session_id = event.get("session_id", "unknown")
    subprocess.run(["omega", "flush", session_id], capture_output=True, check=False)


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
            subprocess.run(["semble", "reindex", file_path], capture_output=True, check=False)
    elif tool == "Bash":
        cmd = tool_input.get("command", "")
        if cmd.strip().startswith("git commit"):
            session_id = event.get("session_id", "unknown")
            subprocess.run(["omega", "note", "git_commit", session_id], capture_output=True, check=False)


def _handle_subagent_stop(event: dict) -> None:
    session_id = event.get("session_id", "unknown")
    subprocess.run(["omega", "flush", session_id], capture_output=True, check=False)


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
        subprocess.run(["semble", "index", str(index_dir)], capture_output=True, check=False)

        if jsonl_dir.exists():
            subprocess.run(["omega", "mine", str(jsonl_dir)], capture_output=True, check=False)

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
        subprocess.run(["omega", "mine", str(jsonl_dir)], capture_output=True, check=False)

        result = subprocess.run(
            ["omega", "query", "current project state tasks decisions"],
            capture_output=True,
            check=False,
            text=True,
        )
        memory_context = result.stdout.strip() if result.returncode == 0 else ""

        body = "# Wake-up\n\n"
        if memory_context:
            body += f"## Memory Context\n\n{memory_context}\n"
        else:
            body += "No prior memory context found.\n"

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
    cwd = event.get("cwd", ".")
    session_id = event.get("session_id", "unknown")
    project = project_name(cwd)

    subprocess.run(["omega", "flush", session_id], capture_output=True, check=False)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    frontmatter = {
        "id": f"checkpoint-{session_id}-{ts}",
        "type": "checkpoint",
        "valid_from": ts[:8],
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
    "Stop": _handle_stop,
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
