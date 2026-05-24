import json
import shutil
import sys
from pathlib import Path

DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"
GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"

_SYNC_HOOKS = ["SessionStart", "UserPromptSubmit", "PreCompact"]
_ASYNC_HOOKS = ["Stop", "SessionEnd"]


def _detect_goldfish_bin() -> str:
    """Return the full path to the goldfish binary, or bare 'goldfish' as fallback."""
    # Prefer system-level install (production: uv tool install goldfish)
    found = shutil.which("goldfish")
    if found:
        return found
    # Fall back to venv-sibling binary (dev: uv pip install -e .)
    venv_bin = Path(sys.executable).parent / "goldfish"
    if venv_bin.exists():
        return str(venv_bin)
    # Last resort: hope it's on PATH at runtime
    return "goldfish"


def _goldfish_hook_entry(bin_path: str, async_: bool = False) -> dict:
    entry: dict = {"type": "command", "command": f"{bin_path} hook"}
    if async_:
        entry["async"] = True
    return entry


def _already_registered(hook_list: list) -> bool:
    return any(
        isinstance(h, dict) and "goldfish hook" in h.get("command", "")
        for h in hook_list
    )


def register_hooks(settings_path: Path = DEFAULT_SETTINGS) -> None:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    hooks = data.setdefault("hooks", {})
    bin_path = _detect_goldfish_bin()  # detect once

    for event in _SYNC_HOOKS:
        hook_list = hooks.setdefault(event, [{"hooks": []}])
        inner = hook_list[0].setdefault("hooks", [])
        if not _already_registered(inner):
            inner.append(_goldfish_hook_entry(bin_path, async_=False))

    for event in _ASYNC_HOOKS:
        hook_list = hooks.setdefault(event, [{"hooks": []}])
        inner = hook_list[0].setdefault("hooks", [])
        if not _already_registered(inner):
            inner.append(_goldfish_hook_entry(bin_path, async_=True))

    settings_path.write_text(json.dumps(data, indent=2))


def append_claude_md_block(claude_md_path: Path, block: str) -> None:
    existing = claude_md_path.read_text() if claude_md_path.exists() else ""
    if GOLDFISH_SENTINEL in existing:
        return
    claude_md_path.write_text(existing.rstrip() + "\n\n" + block + "\n")
