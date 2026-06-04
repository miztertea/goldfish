import json
import re
import shutil
import sys
from pathlib import Path

from goldfishh.config import DEFAULT_SETTINGS

_OLD_GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"
GOLDFISHH_SENTINEL = "## Agent Knowledge Tools (managed by goldfishh)"

_SYNC_HOOKS = ["SessionStart", "UserPromptSubmit", "PreCompact"]
_ASYNC_HOOKS = [
    "Stop",
    "SessionEnd",
    "PostToolUse",
    "SubagentStop",
    "TaskCreated",
    "TaskCompleted",
]


def _detect_goldfish_bin() -> str:
    stable = Path.home() / ".local" / "bin" / "goldfishh"
    if stable.exists():
        return str(stable)
    found = shutil.which("goldfishh")
    if found:
        return found
    venv_bin = Path(sys.executable).parent / "goldfishh"
    if venv_bin.exists():
        return str(venv_bin)
    return "goldfishh"


def _goldfish_hook_entry(bin_path: str, async_: bool = False) -> dict:
    entry: dict = {"type": "command", "command": f"{bin_path} hook"}
    if async_:
        entry["async"] = True
    return entry


def _is_goldfish_hook(h: object) -> bool:
    if not isinstance(h, dict):
        return False
    cmd = h.get("command", "")
    return isinstance(cmd, str) and ("goldfishh" in cmd or "goldfish" in cmd) and cmd.endswith(" hook")


def _upsert_hook(hooks: dict, event: str, bin_path: str, async_: bool) -> None:
    """Remove all stale goldfish hook entries for event and insert a fresh one."""
    hook_list = hooks.setdefault(event, [{"hooks": []}])
    inner = hook_list[0].setdefault("hooks", [])
    inner[:] = [h for h in inner if not _is_goldfish_hook(h)]
    inner.append(_goldfish_hook_entry(bin_path, async_=async_))


def register_hooks(settings_path: Path = DEFAULT_SETTINGS) -> None:
    data = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    hooks = data.setdefault("hooks", {})
    bin_path = _detect_goldfish_bin()
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    for event in _SYNC_HOOKS:
        _upsert_hook(hooks, event, bin_path, async_=False)
    for event in _ASYNC_HOOKS:
        _upsert_hook(hooks, event, bin_path, async_=True)

    settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_claude_md_block(claude_md_path: Path, block: str) -> None:
    existing = claude_md_path.read_text(encoding="utf-8") if claude_md_path.exists() else ""

    # Migrate: remove old-format block if present
    if _OLD_GOLDFISH_SENTINEL in existing and GOLDFISHH_SENTINEL not in existing:
        start = existing.index(_OLD_GOLDFISH_SENTINEL)
        after = existing[start + len(_OLD_GOLDFISH_SENTINEL):]
        m = re.search(r"\n##\s", after)
        if m:
            end = start + len(_OLD_GOLDFISH_SENTINEL) + m.start()
            existing = existing[:start] + existing[end:]
        else:
            existing = existing[:start]

    if GOLDFISHH_SENTINEL not in existing:
        claude_md_path.write_text(existing.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
        return
    # Update: replace existing block in-place, preserving content before and after
    start = existing.index(GOLDFISHH_SENTINEL)
    after = existing[start + len(GOLDFISHH_SENTINEL):]
    m = re.search(r"\n##\s", after)
    if m:
        end = start + len(GOLDFISHH_SENTINEL) + m.start()
        claude_md_path.write_text(existing[:start] + block + "\n" + existing[end:], encoding="utf-8")
    else:
        claude_md_path.write_text(existing[:start] + block + "\n", encoding="utf-8")
