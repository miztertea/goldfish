import json
import subprocess
from pathlib import Path

from goldfish.config import VAULTS_ROOT, get_manifest, project_name, write_manifest
from goldfish.vault import write_note

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


def _handle_stop(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
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
        from goldfish.vault import read_note
        fm, body = read_note(project, task_path, vaults_root=vaults_root)
        write_note(project, task_path, fm, body.rstrip() + "\n\n**Completed.**", vaults_root=vaults_root)
    else:
        _handle_task_created(event, vaults_root=vaults_root)


def _today() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d")


# Wrappers for _HANDLERS (queue dispatch uses default vaults_root)
def _handle_stop_event(event: dict) -> None:
    _handle_stop(event)


def _handle_session_end_event(event: dict) -> None:
    _handle_session_end(event)


def _handle_task_created_event(event: dict) -> None:
    _handle_task_created(event)


def _handle_task_completed_event(event: dict) -> None:
    _handle_task_completed(event)


_HANDLERS: dict = {
    "Stop": _handle_stop_event,
    "SessionEnd": _handle_session_end_event,
    "PostToolUse": _handle_post_tool_use,
    "SubagentStop": _handle_subagent_stop,
    "TaskCreated": _handle_task_created_event,
    "TaskCompleted": _handle_task_completed_event,
}


def main() -> None:
    count = drain()
    print(f"Drained {count} events")


if __name__ == "__main__":
    main()
