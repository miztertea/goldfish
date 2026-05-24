import json
import re
import shutil
import sys
from pathlib import Path

DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"
GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"

_SYNC_HOOKS = ["SessionStart", "UserPromptSubmit", "PreCompact"]
_ASYNC_HOOKS = [
    "Stop", "SessionEnd", "PostToolUse", "SubagentStop",
    "TaskCreated", "TaskCompleted",
]


def _detect_goldfish_bin() -> str:
    found = shutil.which("goldfish")
    if found:
        return found
    venv_bin = Path(sys.executable).parent / "goldfish"
    if venv_bin.exists():
        return str(venv_bin)
    return "goldfish"


def _goldfish_hook_entry(bin_path: str, async_: bool = False) -> dict:
    entry: dict = {"type": "command", "command": f"{bin_path} hook"}
    if async_:
        entry["async"] = True
    return entry


def _is_goldfish_hook(h: object) -> bool:
    if not isinstance(h, dict):
        return False
    cmd = h.get("command", "")
    return "goldfish hook" in cmd


def _upsert_hook(hooks: dict, event: str, bin_path: str, async_: bool) -> None:
    """Remove all stale goldfish hook entries for event and insert a fresh one."""
    hook_list = hooks.setdefault(event, [{"hooks": []}])
    inner = hook_list[0].setdefault("hooks", [])
    inner[:] = [h for h in inner if not _is_goldfish_hook(h)]
    inner.append(_goldfish_hook_entry(bin_path, async_=async_))


def register_hooks(settings_path: Path = DEFAULT_SETTINGS) -> None:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    hooks = data.setdefault("hooks", {})
    bin_path = _detect_goldfish_bin()
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    for event in _SYNC_HOOKS:
        _upsert_hook(hooks, event, bin_path, async_=False)
    for event in _ASYNC_HOOKS:
        _upsert_hook(hooks, event, bin_path, async_=True)

    settings_path.write_text(json.dumps(data, indent=2))


def append_claude_md_block(claude_md_path: Path, block: str) -> None:
    existing = claude_md_path.read_text() if claude_md_path.exists() else ""
    if GOLDFISH_SENTINEL not in existing:
        claude_md_path.write_text(existing.rstrip() + "\n\n" + block + "\n")
        return
    # Update: replace existing block in-place, preserving content before and after
    start = existing.index(GOLDFISH_SENTINEL)
    after = existing[start + len(GOLDFISH_SENTINEL):]
    m = re.search(r'\n##\s', after)
    if m:
        end = start + len(GOLDFISH_SENTINEL) + m.start()
        claude_md_path.write_text(existing[:start] + block + "\n" + existing[end:])
    else:
        claude_md_path.write_text(existing[:start] + block + "\n")
