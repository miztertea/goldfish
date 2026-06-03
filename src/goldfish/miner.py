import json
import shlex
import subprocess
from pathlib import Path

from goldfish.config import DEFAULT_SETTINGS, get_manifest, project_name, write_manifest


def _find_hook_cmd(settings: dict, event: str, script_name: str) -> str | None:
    for group in settings.get("hooks", {}).get(event, []):
        for h in group.get("hooks", []):
            if script_name in h.get("command", ""):
                return h["command"]
    return None


def _extract_user_text(obj: dict) -> str:
    content = obj.get("message", {}).get("content", "")
    # content is a list when the user turn contains tool_result blocks; skip to avoid piping raw tool JSON to OMEGA
    return content if isinstance(content, str) else ""


def _extract_assistant_text(obj: dict) -> str:
    content = obj.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return ""
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text")


def _pipe_to_hook(cmd: str, payload: dict) -> None:
    try:
        subprocess.run(
            shlex.split(cmd),
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise  # caller skips marking session as mined so it can be retried
    except Exception:
        pass


def mine_project(
    cwd: str,
    settings_path: Path = DEFAULT_SETTINGS,
    _sessions_dir: Path | None = None,
    _settings: dict | None = None,
) -> int:
    """Replay historical JSONL sessions through OMEGA's own hook scripts.

    Returns the number of sessions processed.
    _sessions_dir and _settings are injectable for testing and to avoid double
    file reads when the caller already has parsed settings.
    """
    if _sessions_dir is None:
        encoded = Path(cwd).as_posix().replace("/", "-")
        _sessions_dir = Path.home() / ".claude" / "projects" / encoded

    if not _sessions_dir.exists():
        return 0

    if _settings is None:
        _settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    auto_capture_cmd = _find_hook_cmd(_settings, "UserPromptSubmit", "auto_capture")
    assistant_capture_cmd = _find_hook_cmd(_settings, "Stop", "assistant_capture")

    project = project_name(cwd)
    manifest = get_manifest(project)
    mined = set(manifest.get("mined_sessions", []))
    processed = 0

    for jsonl_file in sorted(_sessions_dir.glob("*.jsonl")):
        session_id = jsonl_file.stem
        if session_id in mined:
            continue

        session_ok = True
        for line in jsonl_file.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            try:
                if msg_type == "user" and auto_capture_cmd:
                    text = _extract_user_text(obj)
                    if text:
                        _pipe_to_hook(
                            auto_capture_cmd,
                            {
                                "prompt": text,
                                "session_id": session_id,
                                "cwd": cwd,
                            },
                        )
                elif msg_type == "assistant" and assistant_capture_cmd:
                    text = _extract_assistant_text(obj)
                    if text:
                        _pipe_to_hook(
                            assistant_capture_cmd,
                            {
                                "last_assistant_message": text,
                                "session_id": session_id,
                                "cwd": cwd,
                            },
                        )
            except subprocess.TimeoutExpired:
                session_ok = False
                break

        if session_ok:
            mined.add(session_id)
            processed += 1
            fresh = get_manifest(project)
            write_manifest(project, {**fresh, "mined_sessions": list(mined)})

    return processed
