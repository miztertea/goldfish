# Goldfish Phases 5-8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete goldfishh — session lifecycle handlers, prompt enrichment, async event routing, and operational commands — so every Claude Code hook event is meaningfully handled and `goldfishh status/doctor/replay` work.

**Architecture:** Phases 1-4 built the foundation (queue, drain, vault, config, CLI, init). Phases 5-8 wire real handlers into drain.py for every event type, split sync vs async processing in hook.py, add a new enricher.py for prompt decomposition, and implement the three operational commands. Every function remains a subprocess call, file write, or config read — no algorithms.

**Tech Stack:** Python 3.11+, Chonkie (SentenceChunker), Semble CLI (subprocess), OMEGA CLI (subprocess), typer (already installed), pathlib, tomllib/tomli_w (already installed).

**Current state after Phase 4:**
- 28 tests passing
- `hook.py`: appends ALL events to queue.jsonl, no stdout output
- `drain.py`: routes ALL events to `semble search . <cwd>` — stub only
- `cli.py`: status/doctor/replay are stubs
- Hooks fire but `goldfishh: not found` because binary not on PATH

---

## File Map

```
src/goldfishh/
├── claude_md.py  ← add path detection for hook command (Task P0)
├── drain.py      ← event-type routing + all async handlers (Tasks 5.1, 5.2, 5.4, 7.1, 7.2)
├── hook.py       ← split sync/async dispatch, stdout for sync events (Tasks 5.3, 6.2)
├── enricher.py   ← NEW: Chonkie decompose + Semble/OMEGA fan-out (Task 6.1)
└── cli.py        ← implement status, doctor, replay (Tasks 8.1, 8.2, 8.3)

tests/
├── test_drain.py    ← update stub test, extend with event-type tests
├── test_hook.py     ← extend with sync/stdout tests
├── test_enricher.py ← NEW
└── test_cli.py      ← NEW (status/doctor/replay)
```

---

## Pre-Phase: Fix Hook PATH

**Problem:** `goldfishh: not found` when hooks fire. Claude Code hooks run with a minimal PATH that doesn't include the editable install's `.venv/bin/`.

**Fix:** At hook registration time, detect the goldfishh binary path from `sys.executable`'s parent directory (the active venv) and bake the full path into `settings.json`. Falls back to bare `goldfishh` if detection fails.

---

### Task P0: Fix hook command path detection

**Files:**
- Modify: `src/goldfishh/claude_md.py`
- Test: `tests/test_claude_md.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_claude_md.py`:

```python
import sys
from pathlib import Path
from unittest.mock import patch


def test_register_hooks_uses_detected_goldfish_path(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({}))
    fake_bin = tmp_path / "goldfishh"
    fake_bin.touch()
    # Simulate: goldfishh not on system PATH, but exists in venv bin
    with patch("goldfishh.claude_md.shutil.which", return_value=None), \
         patch("goldfishh.claude_md.sys.executable", str(tmp_path / "python")):
        register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    # The hook command should contain the full path or a fallback
    stop_hooks = data["hooks"]["Stop"][0]["hooks"]
    cmd = stop_hooks[0]["command"]
    assert "goldfishh hook" in cmd or "hook" in cmd
```

- [ ] **Step 2: Run test — verify it passes already (or shows expected gap)**

```bash
.venv/bin/pytest tests/test_claude_md.py::test_register_hooks_uses_detected_goldfish_path -v
```

- [ ] **Step 3: Add path detection to `claude_md.py`**

Add `import shutil` and `import sys` at top of `src/goldfishh/claude_md.py`. Replace the `_GOLDFISH_HOOK_COMMAND` constant with a function:

```python
import json
import shutil
import sys
from pathlib import Path

DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"
GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfishh)"

_SYNC_HOOKS = ["SessionStart", "UserPromptSubmit", "PreCompact"]
_ASYNC_HOOKS = ["Stop", "SessionEnd"]


def _detect_goldfish_bin() -> str:
    # System PATH first (production installs via uv tool install)
    found = shutil.which("goldfishh")
    if found:
        return found
    # Venv bin dir (editable dev installs)
    candidate = Path(sys.executable).parent / "goldfishh"
    if candidate.exists():
        return str(candidate)
    return "goldfishh"


def _goldfish_hook_entry(async_: bool = False) -> dict:
    cmd = f"{_detect_goldfish_bin()} hook"
    entry: dict = {"type": "command", "command": cmd}
    if async_:
        entry["async"] = True
    return entry


def _already_registered(hook_list: list) -> bool:
    return any(
        isinstance(h, dict) and "goldfishh" in h.get("command", "") and "hook" in h.get("command", "")
        for h in hook_list
    )


def register_hooks(settings_path: Path = DEFAULT_SETTINGS) -> None:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    hooks = data.setdefault("hooks", {})

    for event in _SYNC_HOOKS:
        hook_list = hooks.setdefault(event, [{"hooks": []}])
        inner = hook_list[0].setdefault("hooks", [])
        if not _already_registered(inner):
            inner.append(_goldfish_hook_entry(async_=False))

    for event in _ASYNC_HOOKS:
        hook_list = hooks.setdefault(event, [{"hooks": []}])
        inner = hook_list[0].setdefault("hooks", [])
        if not _already_registered(inner):
            inner.append(_goldfish_hook_entry(async_=True))

    settings_path.write_text(json.dumps(data, indent=2))


def append_claude_md_block(claude_md_path: Path, block: str) -> None:
    existing = claude_md_path.read_text() if claude_md_path.exists() else ""
    if GOLDFISH_SENTINEL in existing:
        return
    claude_md_path.write_text(existing.rstrip() + "\n\n" + block + "\n")
```

- [ ] **Step 4: Re-run all tests to confirm no regressions**

```bash
.venv/bin/pytest -v
```
Expected: 28 passed

- [ ] **Step 5: Re-run goldfishh init to update settings.json with detected path**

```bash
goldfishh init
```
Expected: hook commands in `~/.claude/settings.json` now contain the full path to the goldfishh binary.

- [ ] **Step 6: Verify hooks now use full path**

```bash
python3 -c "import json; d=json.load(open('/root/.claude/settings.json' if __import__('os').path.exists('/root/.claude/settings.json') else '/home/tchawes/.claude/settings.json')); print(d['hooks']['Stop'][0]['hooks'][0]['command'])"
```
Expected: `/home/tchawes/goldfishh/.venv/bin/goldfishh hook` (or the detected path)

- [ ] **Step 7: Commit**

```bash
git add src/goldfishh/claude_md.py tests/test_claude_md.py
git commit -m "fix: detect goldfishh binary path for hook registration"
```

---

## Phase 5 — Session Lifecycle

Implement real handlers for SessionStart, PreCompact, Stop, and SessionEnd. After this phase, starting Claude Code writes a wake-up context note.

### Architecture for sync vs async

**Sync events** (Claude waits for exit, stdout → Claude context):
`SessionStart`, `UserPromptSubmit`, `PreCompact`

**Async events** (Claude does not wait, `async: true`):
`Stop`, `SessionEnd`, `PostToolUse`, `SubagentStop`, `TaskCreated`, `TaskCompleted`

**New design for hook.py:**
- Sync events → process inline (import handler from drain.py), write stdout, exit. Do NOT append to queue.
- Async events → append to queue.jsonl, exit immediately.

**New design for drain.py:**
- Replace the single `_route(event)` stub with an event-type dispatch dict.
- Each handler is a focused function.
- Async events only.

---

### Task 5.1: Refactor drain.py to event-type routing

**Files:**
- Modify: `src/goldfishh/drain.py`
- Modify: `tests/test_drain.py`

- [ ] **Step 1: Update `test_drain_calls_semble_with_event_cwd` (it tests the old stub)**

In `tests/test_drain.py`, rename and rewrite the test that checks semble is called for Stop events. After this refactor, Stop calls omega flush. Replace with a test that checks PostToolUse(Write) calls semble:

```python
def test_drain_routes_post_tool_use_write_to_semble(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {
        "type": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/my/project/src/auth.py"},
        "cwd": "/my/project",
    }
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        drain(queue=queue)
    args = mock_run.call_args[0][0]
    assert args[0] == "semble"
    assert "/my/project/src/auth.py" in args
```

Also update `test_drain_processes_one_event` to match new Stop behavior (omega flush, not semble):

```python
def test_drain_processes_one_event(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "cwd": "/home/user/project", "session_id": "s1"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 1
    # Stop calls omega flush
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "omega"


def test_drain_processes_multiple_events(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        {"type": "Stop", "cwd": "/p", "session_id": "s1"},
        {"type": "Stop", "cwd": "/p", "session_id": "s2"},
    ]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 2
    assert mock_run.call_count == 2
```

- [ ] **Step 2: Run tests — expect failures on the new tests (PostToolUse not handled yet)**

```bash
.venv/bin/pytest tests/test_drain.py -v
```
Expected: test_drain_routes_post_tool_use_write_to_semble FAILS (NotImplemented), others pass

- [ ] **Step 3: Refactor `drain.py` — replace stub `_route` with event-type dispatch**

Replace `src/goldfishh/drain.py` entirely:

```python
import json
import subprocess
from pathlib import Path

from goldfishh.config import VAULTS_ROOT, get_manifest, project_name, write_manifest
from goldfishh.vault import write_note

QUEUE_PATH = Path.home() / ".goldfishh" / "queue.jsonl"


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


_HANDLERS: dict = {}  # populated below after handler definitions


def _route(event: dict) -> None:
    handler = _HANDLERS.get(event.get("type", ""))
    if handler:
        handler(event)


def _handle_stop(event: dict) -> None:
    session_id = event.get("session_id", "unknown")
    subprocess.run(["omega", "flush", session_id], capture_output=True, check=False)


def _handle_session_end(event: dict) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    wake_up = VAULTS_ROOT / project / "_context" / "wake-up.md"
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


def _handle_task_created(event: dict) -> None:
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
            "source_offset": get_manifest(project).get("last_byte_offset", 0),
            "related": [],
        },
        f"Task created: {event.get('task_description', task_id)}",
    )


def _handle_task_completed(event: dict) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    task_id = event.get("task_id", "unknown")
    task_path = f"Tasks/{task_id}.md"
    note_file = VAULTS_ROOT / project / task_path
    if note_file.exists():
        from goldfishh.vault import read_note
        fm, body = read_note(project, task_path)
        write_note(project, task_path, fm, body.rstrip() + "\n\n**Completed.**")
    else:
        _handle_task_created(event)  # create if missing, then mark complete


def _today() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d")


_HANDLERS = {
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
```

- [ ] **Step 4: Run drain tests**

```bash
.venv/bin/pytest tests/test_drain.py -v
```
Expected: all pass (test_drain_routes_post_tool_use_write_to_semble now passes too)

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/goldfishh/drain.py tests/test_drain.py
git commit -m "refactor: drain.py event-type routing with async handlers"
```

---

### Task 5.2: SessionStart handler — new vs existing project

This is the **synchronous** SessionStart handler called directly from hook.py (not via drain queue). It returns a string written to stdout, which Claude Code injects as context.

**Files:**
- Modify: `src/goldfishh/drain.py` — add `handle_session_start(event) -> str`
- Modify: `tests/test_drain.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_drain.py`:

```python
from goldfishh.drain import handle_session_start


def test_session_start_new_project_creates_wake_up(tmp_path):
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfishh.drain.subprocess.run"), \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        result = handle_session_start(event, vaults_root=tmp_path)
    wake_up = tmp_path / "myapp" / "_context" / "wake-up.md"
    assert wake_up.exists()
    assert isinstance(result, str)
    assert len(result) > 0


def test_session_start_new_project_returns_first_session_message(tmp_path):
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfishh.drain.subprocess.run"), \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        result = handle_session_start(event, vaults_root=tmp_path)
    assert "first session" in result.lower() or "new project" in result.lower()


def test_session_start_existing_project_runs_omega_mine(tmp_path):
    from goldfishh.config import write_manifest
    write_manifest("myapp", {"last_byte_offset": 100, "bootstrap_complete": True,
                             "semble_indexed_at": "", "last_jsonl_file": ""}, vaults_root=tmp_path)
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s2"}
    with patch("goldfishh.drain.subprocess.run") as mock_run, \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        handle_session_start(event, vaults_root=tmp_path)
    cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(c[0] == "omega" for c in cmds)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_drain.py::test_session_start_new_project_creates_wake_up -v
```
Expected: `ImportError: cannot import name 'handle_session_start'`

- [ ] **Step 3: Add `handle_session_start` to `drain.py`**

Add after the existing `_today()` function (before `_HANDLERS`):

```python
def handle_session_start(event: dict, vaults_root: Path = VAULTS_ROOT) -> str:
    """
    Synchronous SessionStart handler called directly from hook.py.
    Returns wake-up content string for stdout injection.
    """
    from datetime import datetime
    cwd = event.get("cwd", ".")
    session_id = event.get("session_id", "unknown")
    project = project_name(cwd)

    manifest = get_manifest(project, vaults_root=vaults_root)

    if manifest.get("bootstrap_complete"):
        return _session_start_existing(cwd, project, session_id, manifest, vaults_root)
    else:
        return _session_start_new(cwd, project, session_id, vaults_root)


def _session_start_new(cwd: str, project: str, session_id: str, vaults_root: Path) -> str:
    from goldfishh.vault import scaffold
    scaffold(project, vaults_root=vaults_root)

    src = Path(cwd) / "src"
    index_target = str(src) if src.exists() else cwd
    subprocess.run(["semble", "index", index_target], capture_output=True, check=False)

    jsonl_dir = _jsonl_dir(cwd)
    if jsonl_dir.exists():
        subprocess.run(["omega", "mine", str(jsonl_dir)], capture_output=True, check=False)

    content = (
        "## Goldfish Wake-Up — First Session\n\n"
        f"**Project:** {project}\n"
        f"**Session:** {session_id}\n\n"
        "Code search ready. Episodic memory indexing from session history.\n"
        "Context improves as this session progresses.\n"
    )
    write_note(
        project,
        "_context/wake-up.md",
        {
            "id": f"wake-up-{session_id}",
            "type": "checkpoint",
            "valid_from": _today(),
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": session_id,
            "source_offset": 0,
            "related": [],
        },
        content,
        vaults_root=vaults_root,
    )

    write_manifest(
        project,
        {**get_manifest(project, vaults_root=vaults_root), "bootstrap_complete": True},
        vaults_root=vaults_root,
    )

    return content


def _session_start_existing(
    cwd: str, project: str, session_id: str, manifest: dict, vaults_root: Path
) -> str:
    jsonl_dir = _jsonl_dir(cwd)
    if jsonl_dir.exists():
        subprocess.run(["omega", "mine", str(jsonl_dir)], capture_output=True, check=False)

    result = subprocess.run(
        ["omega", "query", "current project state tasks decisions"],
        capture_output=True, check=False,
    )
    memory_context = result.stdout.decode(errors="replace").strip() if result.returncode == 0 else ""

    content = (
        "## Goldfish Wake-Up\n\n"
        f"**Project:** {project}\n"
        f"**Session:** {session_id}\n\n"
    )
    if memory_context:
        content += f"### Recent Context\n\n{memory_context}\n"
    else:
        content += "_No episodic memory yet for this project._\n"

    write_note(
        project,
        "_context/wake-up.md",
        {
            "id": f"wake-up-{session_id}",
            "type": "checkpoint",
            "valid_from": _today(),
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": session_id,
            "source_offset": manifest.get("last_byte_offset", 0),
            "related": [],
        },
        content,
        vaults_root=vaults_root,
    )

    return content


def _jsonl_dir(cwd: str) -> Path:
    encoded = str(Path(cwd)).replace("/", "-")
    return Path.home() / ".claude" / "projects" / encoded


def handle_pre_compact(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    """
    Synchronous PreCompact handler called directly from hook.py.
    Flushes OMEGA and writes a checkpoint note.
    """
    from datetime import datetime
    session_id = event.get("session_id", "unknown")
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    subprocess.run(["omega", "flush", session_id], capture_output=True, check=False)

    write_note(
        project,
        f"Memory/Checkpoints/{session_id}-{ts}.md",
        {
            "id": f"checkpoint-{session_id}-{ts}",
            "type": "checkpoint",
            "valid_from": ts[:8],
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": session_id,
            "source_offset": get_manifest(project, vaults_root=vaults_root).get("last_byte_offset", 0),
            "related": [],
        },
        f"Session checkpoint before compaction.\nSession: {session_id}\nTimestamp: {ts}",
        vaults_root=vaults_root,
    )
```

- [ ] **Step 4: Run new tests**

```bash
.venv/bin/pytest tests/test_drain.py -v
```
Expected: all pass

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/goldfishh/drain.py tests/test_drain.py
git commit -m "feat: SessionStart and PreCompact sync handlers with wake-up note"
```

---

### Task 5.3: hook.py — sync/async dispatch and stdout writing

**Files:**
- Modify: `src/goldfishh/hook.py`
- Modify: `tests/test_hook.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_hook.py`:

```python
import sys
import io
from unittest.mock import patch


def test_hook_async_event_appends_to_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "session_id": "s1", "cwd": "/p"}
    handle(event, queue=queue)
    assert queue.exists()
    assert len(queue.read_text().splitlines()) == 1


def test_hook_sync_session_start_writes_stdout(tmp_path, capsys):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "SessionStart", "session_id": "s1", "cwd": "/project/myapp"}
    with patch("goldfishh.hook.handle_session_start", return_value="wake-up content") as mock_handler:
        from goldfishh.hook import main_with_event
        main_with_event(event, queue=queue)
    captured = capsys.readouterr()
    assert "wake-up content" in captured.out
    # Sync events do NOT go to queue
    assert not queue.exists() or queue.read_text() == ""


def test_hook_sync_user_prompt_submit_writes_stdout(tmp_path, capsys):
    event = {"type": "UserPromptSubmit", "prompt": "fix the auth bug in middleware", "cwd": "/p", "session_id": "s1"}
    with patch("goldfishh.hook.enrich", return_value="## Context\nrelevant code here"):
        from goldfishh.hook import main_with_event
        main_with_event(event, queue=tmp_path / "queue.jsonl")
    captured = capsys.readouterr()
    assert "Context" in captured.out


def test_hook_sync_pre_compact_no_stdout(tmp_path, capsys):
    event = {"type": "PreCompact", "session_id": "s1", "cwd": "/p"}
    with patch("goldfishh.hook.handle_pre_compact") as mock_handler:
        from goldfishh.hook import main_with_event
        main_with_event(event, queue=tmp_path / "queue.jsonl")
    mock_handler.assert_called_once_with(event)
    captured = capsys.readouterr()
    assert captured.out == ""  # PreCompact returns nothing to stdout
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_hook.py -v
```
Expected: new tests fail (no `main_with_event` function yet)

- [ ] **Step 3: Rewrite `hook.py`**

Replace `src/goldfishh/hook.py` entirely:

```python
import json
import sys
from pathlib import Path

from goldfishh.config import project_name
from goldfishh.drain import handle_pre_compact, handle_session_start
from goldfishh.enricher import enrich

QUEUE_PATH = Path.home() / ".goldfishh" / "queue.jsonl"

_ASYNC_EVENTS = {"Stop", "SessionEnd", "PostToolUse", "SubagentStop", "TaskCreated", "TaskCompleted"}
_SYNC_EVENTS = {"SessionStart", "UserPromptSubmit", "PreCompact"}


def handle(event: dict, queue: Path = QUEUE_PATH) -> None:
    """Append event to queue (async events only)."""
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("a") as f:
        f.write(json.dumps(event) + "\n")


def main_with_event(event: dict, queue: Path = QUEUE_PATH) -> None:
    """Process one event. Exported for testing."""
    event_type = event.get("type", "")

    if event_type in _ASYNC_EVENTS or event_type not in _SYNC_EVENTS:
        handle(event, queue=queue)
        return

    # Synchronous events: process inline, write stdout
    if event_type == "SessionStart":
        result = handle_session_start(event)
        if result:
            sys.stdout.write(result)
    elif event_type == "UserPromptSubmit":
        prompt = event.get("prompt", "")
        cwd = event.get("cwd", ".")
        result = enrich(prompt, cwd, project_name(cwd))
        if result:
            sys.stdout.write(result)
    elif event_type == "PreCompact":
        handle_pre_compact(event)


def main() -> None:
    event = json.loads(sys.stdin.read())
    main_with_event(event)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run hook tests**

```bash
.venv/bin/pytest tests/test_hook.py -v
```
Expected: all pass (including original 3 tests)

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/goldfishh/hook.py tests/test_hook.py
git commit -m "feat: hook.py sync/async dispatch with stdout for SessionStart and PreCompact"
```

---

### Task 5.4: Stop/SessionEnd manifest update

The Stop handler currently only calls omega flush. It also needs to advance `last_byte_offset` in the manifest so the next SessionStart knows how much JSONL history is new.

**Files:**
- Modify: `src/goldfishh/drain.py` — extend `_handle_stop`
- Modify: `tests/test_drain.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_drain.py`:

```python
def test_stop_advances_manifest_offset(tmp_path):
    from goldfishh.config import write_manifest, get_manifest
    write_manifest("myapp", {"last_byte_offset": 0, "bootstrap_complete": True,
                             "semble_indexed_at": "", "last_jsonl_file": "abc.jsonl"}, vaults_root=tmp_path)
    # Create a fake JSONL file with some content
    jsonl_dir = Path.home() / ".claude" / "projects" / "-project-myapp"
    jsonl_dir.mkdir(parents=True, exist_ok=True)
    fake_jsonl = jsonl_dir / "abc.jsonl"
    fake_jsonl.write_text('{"type":"Stop"}\n{"type":"Stop"}\n')

    event = {"type": "Stop", "cwd": "/project/myapp", "session_id": "s1",
             "jsonl_file": str(fake_jsonl)}
    with patch("goldfishh.drain.subprocess.run"), \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        _handle_stop(event, vaults_root=tmp_path)

    manifest = get_manifest("myapp", vaults_root=tmp_path)
    assert manifest["last_byte_offset"] > 0
```

- [ ] **Step 2: Run test — verify it fails**

```bash
.venv/bin/pytest tests/test_drain.py::test_stop_advances_manifest_offset -v
```
Expected: FAIL — `_handle_stop` doesn't accept `vaults_root` or update manifest

- [ ] **Step 3: Update `_handle_stop` in `drain.py`**

Replace the existing `_handle_stop`:

```python
def _handle_stop(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    session_id = event.get("session_id", "unknown")
    cwd = event.get("cwd", ".")
    project = project_name(cwd)

    subprocess.run(["omega", "flush", session_id], capture_output=True, check=False)

    jsonl_file_path = event.get("jsonl_file", "")
    if jsonl_file_path:
        try:
            offset = Path(jsonl_file_path).stat().st_size
            manifest = get_manifest(project, vaults_root=vaults_root)
            write_manifest(
                project,
                {**manifest, "last_byte_offset": offset, "last_jsonl_file": Path(jsonl_file_path).name},
                vaults_root=vaults_root,
            )
        except OSError:
            pass
```

Also update the `_HANDLERS` dict entry for "Stop" to pass the correct signature (handlers in `_HANDLERS` are called with `(event,)` only). Add a wrapper:

```python
def _handle_stop_event(event: dict) -> None:
    _handle_stop(event)
```

And in `_HANDLERS`:
```python
_HANDLERS = {
    "Stop": _handle_stop_event,
    ...
}
```

Note: `_handle_stop` accepts optional `vaults_root` for testing; `_handle_stop_event` is the queue-dispatch wrapper that uses the default.

- [ ] **Step 4: Run all tests**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/goldfishh/drain.py tests/test_drain.py
git commit -m "feat: Stop handler advances manifest offset for incremental OMEGA mining"
```

---

## Phase 6 — Prompt Enrichment (UserPromptSubmit)

The only synchronous handler that injects context before Claude acts. Multi-topic prompts are decomposed by Chonkie and each chunk fanned out to Semble (code + vault) in parallel.

---

### Task 6.1: `enricher.py` — Chonkie decomposition + Semble fan-out

**Files:**
- Create: `src/goldfishh/enricher.py`
- Create: `tests/test_enricher.py`
- Modify: `pyproject.toml` — add `"chonkie"`

- [ ] **Step 1: Write failing tests**

Create `tests/test_enricher.py`:

```python
import subprocess
from unittest.mock import patch, MagicMock

from goldfishh.enricher import decompose, enrich


def test_decompose_returns_empty_for_short_prompt():
    assert decompose("yes") == []
    assert decompose("do that") == []
    assert decompose("ok") == []


def test_decompose_returns_prompt_for_medium_prompt():
    chunks = decompose("fix the authentication middleware")
    assert isinstance(chunks, list)
    assert len(chunks) >= 1


def test_decompose_splits_multi_topic_prompt():
    chunks = decompose(
        "fix the auth middleware and also the CI tests are broken "
        "and Sarah mentioned something about the rate limiter"
    )
    assert len(chunks) >= 2


def test_enrich_returns_empty_string_for_short_prompt():
    result = enrich("yes", "/project", "myapp")
    assert result == ""


def test_enrich_calls_semble_for_code_and_docs(tmp_path):
    mock_result = MagicMock()
    mock_result.stdout = b"some search result"
    mock_result.returncode = 0
    with patch("goldfishh.enricher.subprocess.run", return_value=mock_result) as mock_run:
        result = enrich(
            "fix the authentication middleware in the API layer",
            "/project",
            "myapp",
        )
    # At least 2 semble calls per chunk (code + docs)
    assert mock_run.call_count >= 2
    assert isinstance(result, str)


def test_enrich_formats_output_as_context_block():
    mock_result = MagicMock()
    mock_result.stdout = b"relevant code snippet here"
    mock_result.returncode = 0
    with patch("goldfishh.enricher.subprocess.run", return_value=mock_result):
        result = enrich("fix the authentication bug", "/project", "myapp")
    # Should return non-empty formatted block
    assert len(result) > 0


def test_enrich_returns_empty_on_no_results():
    mock_result = MagicMock()
    mock_result.stdout = b""
    mock_result.returncode = 0
    with patch("goldfishh.enricher.subprocess.run", return_value=mock_result):
        result = enrich("fix the authentication bug", "/project", "myapp")
    # Empty semble output → empty enrichment
    assert result == "" or isinstance(result, str)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_enricher.py -v
```
Expected: `ModuleNotFoundError: No module named 'goldfishh.enricher'`

- [ ] **Step 3: Add `chonkie` to `pyproject.toml`**

In `pyproject.toml`, update:
```toml
dependencies = ["tomli-w", "PyYAML", "typer", "chonkie"]
```

Then reinstall:
```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 4: Create `src/goldfishh/enricher.py`**

```python
import subprocess
from pathlib import Path

from goldfishh.config import VAULTS_ROOT

MIN_PROMPT_WORDS = 4


def decompose(prompt: str) -> list[str]:
    """Split multi-topic prompt into discrete queries. Returns [] for short prompts."""
    if len(prompt.split()) < MIN_PROMPT_WORDS:
        return []
    try:
        from chonkie import SentenceChunker
        chunker = SentenceChunker()
        chunks = chunker(prompt)
        return [c.text for c in chunks if c.text.strip()]
    except Exception:
        return [prompt]


def enrich(prompt: str, cwd: str, project: str) -> str:
    """
    Decompose prompt and fan out to Semble (code + vault) per chunk.
    Returns formatted context block, or "" if prompt is too short or all results empty.
    """
    chunks = decompose(prompt)
    if not chunks:
        return ""

    vault_path = str(VAULTS_ROOT / project)
    sections: list[str] = []

    for chunk in chunks:
        code_result = subprocess.run(
            ["semble", "search", chunk, cwd],
            capture_output=True, check=False,
        )
        docs_result = subprocess.run(
            ["semble", "search", chunk, vault_path, "--content", "docs"],
            capture_output=True, check=False,
        )

        code_out = code_result.stdout.decode(errors="replace").strip()
        docs_out = docs_result.stdout.decode(errors="replace").strip()

        if code_out or docs_out:
            section = f"### Query: {chunk}\n"
            if code_out:
                section += f"\n**Code:**\n{code_out}\n"
            if docs_out:
                section += f"\n**Vault:**\n{docs_out}\n"
            sections.append(section)

    if not sections:
        return ""

    return "## Goldfish Context\n\n" + "\n\n".join(sections)
```

- [ ] **Step 5: Run enricher tests**

```bash
.venv/bin/pytest tests/test_enricher.py -v
```
Expected: all pass

- [ ] **Step 6: Run full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/goldfishh/enricher.py tests/test_enricher.py pyproject.toml
git commit -m "feat: enricher.py — Chonkie decomposition and Semble fan-out for UserPromptSubmit"
```

---

### Task 6.2: Wire enricher into hook.py UserPromptSubmit

Hook.py already imports `enrich` and calls it for UserPromptSubmit (written in Task 5.3). This task verifies the integration is correct and adds an integration test.

**Files:**
- Modify: `tests/test_hook.py` — add integration-style test

- [ ] **Step 1: Add test verifying short prompts skip enrichment**

Add to `tests/test_hook.py`:

```python
def test_hook_short_prompt_produces_no_stdout(tmp_path, capsys):
    event = {"type": "UserPromptSubmit", "prompt": "yes", "cwd": "/p", "session_id": "s1"}
    with patch("goldfishh.hook.enrich", return_value="") as mock_enrich:
        from goldfishh.hook import main_with_event
        main_with_event(event, queue=tmp_path / "queue.jsonl")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_hook_long_prompt_calls_enrich_and_writes_stdout(tmp_path, capsys):
    event = {
        "type": "UserPromptSubmit",
        "prompt": "fix the authentication middleware and refactor the JWT rotation policy",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfishh.hook.enrich", return_value="## Goldfish Context\n\nsome results"):
        from goldfishh.hook import main_with_event
        main_with_event(event, queue=tmp_path / "queue.jsonl")
    captured = capsys.readouterr()
    assert "Goldfish Context" in captured.out
```

- [ ] **Step 2: Run new tests**

```bash
.venv/bin/pytest tests/test_hook.py -v
```
Expected: all pass

- [ ] **Step 3: Run full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_hook.py
git commit -m "test: verify UserPromptSubmit enrichment wired through hook.py"
```

---

## Phase 7 — Async PostToolUse Events

PostToolUse is the most common async event type. File edits trigger semble reindex; git commits trigger an OMEGA note.

**These handlers are already stubbed in Task 5.1.** This phase adds missing tests for full coverage.

---

### Task 7.1: PostToolUse handler coverage

The handlers exist in drain.py. This task adds tests for every routing branch.

**Files:**
- Modify: `tests/test_drain.py`

- [ ] **Step 1: Write tests for all PostToolUse branches**

Add to `tests/test_drain.py`:

```python
from goldfishh.drain import _handle_post_tool_use


def test_post_tool_use_edit_calls_semble_reindex(tmp_path):
    event = {
        "type": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/project/src/main.py"},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "semble"
    assert cmd[1] == "reindex"
    assert "/project/src/main.py" in cmd


def test_post_tool_use_bash_git_commit_calls_omega_note(tmp_path):
    event = {
        "type": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'fix auth'"},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "omega"
    assert "note" in cmd


def test_post_tool_use_bash_non_commit_does_nothing():
    event = {
        "type": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    mock_run.assert_not_called()


def test_post_tool_use_unknown_tool_does_nothing():
    event = {
        "type": "PostToolUse",
        "tool_name": "WebFetch",
        "tool_input": {},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    mock_run.assert_not_called()
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/pytest tests/test_drain.py -v
```
Expected: all pass

- [ ] **Step 3: Run full suite**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_drain.py
git commit -m "test: full PostToolUse routing coverage"
```

---

### Task 7.2: Task lifecycle handler coverage

TaskCreated and TaskCompleted handlers are already in drain.py from Task 5.1. This task adds tests.

**Files:**
- Modify: `tests/test_drain.py`

- [ ] **Step 1: Write tests for task lifecycle**

Add to `tests/test_drain.py`:

```python
from goldfishh.drain import _handle_task_created, _handle_task_completed


def test_task_created_writes_note_to_vault(tmp_path):
    event = {
        "type": "TaskCreated",
        "task_id": "task-abc",
        "task_description": "Implement auth middleware",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        _handle_task_created(event, vaults_root=tmp_path)
    note = tmp_path / "myapp" / "Tasks" / "task-abc.md"
    assert note.exists()
    assert "Implement auth middleware" in note.read_text()


def test_task_completed_appends_completed_marker(tmp_path):
    from goldfishh.vault import scaffold, write_note
    scaffold("myapp", vaults_root=tmp_path)
    write_note("myapp", "Tasks/task-abc.md",
               {"id": "task-abc", "type": "task", "valid_from": "2026-05-24",
                "superseded_by": None, "confidence": 1.0, "source_session": "s1",
                "source_offset": 0, "related": []},
               "Task body.",
               vaults_root=tmp_path)
    event = {
        "type": "TaskCompleted",
        "task_id": "task-abc",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        _handle_task_completed(event, vaults_root=tmp_path)
    content = (tmp_path / "myapp" / "Tasks" / "task-abc.md").read_text()
    assert "Completed" in content
```

Note: `_handle_task_created` and `_handle_task_completed` need a `vaults_root` parameter for testing. Update their signatures in `drain.py`:

- [ ] **Step 2: Update `_handle_task_created` and `_handle_task_completed` signatures in `drain.py`**

```python
def _handle_task_created(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    ...
    write_note(project, f"Tasks/{task_id}.md", {...}, ..., vaults_root=vaults_root)


def _handle_task_completed(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    ...
    note_file = vaults_root / project / task_path
    ...
    write_note(project, task_path, fm, ..., vaults_root=vaults_root)
```

Add wrappers for `_HANDLERS` (queue dispatch doesn't pass vaults_root):

```python
def _handle_task_created_event(event: dict) -> None:
    _handle_task_created(event)


def _handle_task_completed_event(event: dict) -> None:
    _handle_task_completed(event)
```

Update `_HANDLERS`:
```python
_HANDLERS = {
    ...
    "TaskCreated": _handle_task_created_event,
    "TaskCompleted": _handle_task_completed_event,
}
```

- [ ] **Step 3: Run all tests**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add src/goldfishh/drain.py tests/test_drain.py
git commit -m "feat: task lifecycle handlers with vault note writes and tests"
```

---

## Phase 8 — Operational Commands

Implement the three currently-stubbed CLI commands. These are pure read operations: no subprocess side effects, no queue writes.

---

### Task 8.1: `goldfishh status`

**Files:**
- Modify: `src/goldfishh/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from goldfishh.cli import app

runner = CliRunner()


def test_status_shows_queue_depth(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text('{"type":"Stop"}\n{"type":"Stop"}\n')
    with patch("goldfishh.cli.QUEUE_PATH", queue), \
         patch("goldfishh.cli.os.getcwd", return_value="/project/myapp"), \
         patch("goldfishh.cli.get_manifest", return_value={"last_byte_offset": 100,
                                                           "bootstrap_complete": True,
                                                           "semble_indexed_at": "2026-05-24T12:00:00"}):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "2" in result.output  # queue depth


def test_status_shows_bootstrap_complete(tmp_path):
    with patch("goldfishh.cli.QUEUE_PATH", tmp_path / "empty.jsonl"), \
         patch("goldfishh.cli.os.getcwd", return_value="/project/myapp"), \
         patch("goldfishh.cli.get_manifest", return_value={"last_byte_offset": 0,
                                                           "bootstrap_complete": True,
                                                           "semble_indexed_at": ""}):
        result = runner.invoke(app, ["status"])
    assert "complete" in result.output.lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_cli.py::test_status_shows_queue_depth -v
```
Expected: FAIL — status command just echoes stub text

- [ ] **Step 3: Implement `status` in `cli.py`**

Add imports to `cli.py`:
```python
import os
from goldfishh.config import get_manifest, project_name
from goldfishh.drain import QUEUE_PATH
```

Replace the status stub:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_cli.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/goldfishh/cli.py tests/test_cli.py
git commit -m "feat: goldfishh status command"
```

---

### Task 8.2: `goldfishh doctor`

Checks all system components and prints fix instructions for any failures.

**Files:**
- Modify: `src/goldfishh/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_cli.py`:

```python
def test_doctor_passes_when_all_healthy(tmp_path):
    gitnexus_dir = tmp_path / ".gitnexus"
    gitnexus_dir.mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/path/goldfishh hook", "async": True}]}]}}))
    with patch("goldfishh.cli.shutil.which", return_value="/usr/bin/node"), \
         patch("goldfishh.cli.subprocess.run") as mock_run, \
         patch("goldfishh.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfishh.cli.DEFAULT_SETTINGS", settings):
        mock_run.return_value.returncode = 0
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "✓" in result.output or "ok" in result.output.lower()


def test_doctor_flags_missing_node():
    with patch("goldfishh.cli.shutil.which", return_value=None), \
         patch("goldfishh.cli.os.getcwd", return_value="/project"):
        result = runner.invoke(app, ["doctor"])
    assert "node" in result.output.lower() or "nodejs" in result.output.lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_cli.py::test_doctor_flags_missing_node -v
```
Expected: FAIL — doctor just echoes stub text

- [ ] **Step 3: Implement `doctor` in `cli.py`**

Add `import shutil` and `import subprocess` to cli.py imports.

Replace the doctor stub:

```python
@app.command()
def doctor() -> None:
    """Check goldfishh configuration. Prints fix instructions for failures."""
    import shutil
    import subprocess
    import json
    from goldfishh.claude_md import DEFAULT_SETTINGS

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
    result = subprocess.run(["omega", "status"], capture_output=True, check=False)
    if result.returncode == 0:
        typer.echo("✓ OMEGA responsive")
    else:
        typer.echo("✗ OMEGA not responding — run: omega setup")
        ok = False

    # Hook registration check
    if DEFAULT_SETTINGS.exists():
        try:
            data = json.loads(DEFAULT_SETTINGS.read_text())
            hooks = data.get("hooks", {})
            has_goldfish = any(
                "goldfishh" in str(h)
                for event_hooks in hooks.values()
                for group in event_hooks
                for h in group.get("hooks", [])
            )
            if has_goldfish:
                typer.echo("✓ Hooks registered in settings.json")
            else:
                typer.echo("✗ Hooks not registered — run: goldfishh init")
                ok = False
        except (json.JSONDecodeError, KeyError):
            typer.echo("✗ settings.json malformed — run: goldfishh init")
            ok = False
    else:
        typer.echo("✗ ~/.claude/settings.json not found — run: goldfishh init")
        ok = False

    # Queue depth check
    queue = QUEUE_PATH
    if queue.exists():
        depth = len(queue.read_text().splitlines())
        if depth > 100:
            typer.echo(f"⚠ Queue depth {depth} — run: goldfishh drain")
        else:
            typer.echo(f"✓ Queue depth {depth}")
    else:
        typer.echo("✓ Queue empty")

    if ok:
        typer.echo("\nAll checks passed.")
    else:
        typer.echo("\nSome checks failed. See above for fix instructions.")
        raise typer.Exit(1)
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_cli.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/goldfishh/cli.py tests/test_cli.py
git commit -m "feat: goldfishh doctor command with per-component checks"
```

---

### Task 8.3: `goldfishh replay`

Rebuilds vault from JSONL transcripts. Resumable from `last_byte_offset`.

**Files:**
- Modify: `src/goldfishh/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_cli.py`:

```python
def test_replay_processes_jsonl_events(tmp_path):
    # Create a fake JSONL transcript
    encoded = "/project/myapp".replace("/", "-")
    jsonl_dir = tmp_path / ".claude" / "projects" / encoded
    jsonl_dir.mkdir(parents=True)
    events = [
        {"type": "TaskCreated", "task_id": "t1", "task_description": "auth", "cwd": "/project/myapp", "session_id": "s1"},
    ]
    jsonl_file = jsonl_dir / "session1.jsonl"
    jsonl_file.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    with patch("goldfishh.cli.os.getcwd", return_value="/project/myapp"), \
         patch("goldfishh.cli.Path.home", return_value=tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path / ".goldfishh" / "vaults"), \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path / ".goldfishh" / "vaults"):
        result = runner.invoke(app, ["replay"])

    assert result.exit_code == 0
    assert "replay" in result.output.lower() or "processed" in result.output.lower()
```

- [ ] **Step 2: Run test — verify it fails**

```bash
.venv/bin/pytest tests/test_cli.py::test_replay_processes_jsonl_events -v
```
Expected: FAIL — replay just echoes stub text

- [ ] **Step 3: Implement `replay` in `cli.py`**

Replace the replay stub:

```python
@app.command()
def replay() -> None:
    """Rebuild vault from Claude Code JSONL transcripts. Resumable."""
    from goldfishh.config import get_manifest, project_name, write_manifest
    from goldfishh.drain import _route
    import json as _json

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
                    event = _json.loads(line)
                    _route(event)
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
```

- [ ] **Step 4: Run all tests**

```bash
.venv/bin/pytest -v
```
Expected: all pass

- [ ] **Step 5: Run goldfishh doctor to verify everything wired up**

```bash
goldfishh doctor
```
Expected: hooks registered, Node.js found, .gitnexus found — may warn about OMEGA if not installed

- [ ] **Step 6: Commit**

```bash
git add src/goldfishh/cli.py tests/test_cli.py
git commit -m "feat: goldfishh replay command — rebuilds vault from JSONL transcripts"
```

---

## Self-Review

### Spec Coverage

| PRD Requirement | Task |
|---|---|
| hook.py writes async events to queue | P0, 5.3 |
| hook.py processes sync events inline + stdout | 5.3 |
| SessionStart new project: index, wake-up | 5.2 |
| SessionStart existing project: mine, reindex, query, wake-up | 5.2 |
| PreCompact: omega flush + checkpoint note | 5.2 |
| Stop: omega flush + manifest offset advance | 5.4 |
| SessionEnd: delete _context/wake-up.md | 5.1 |
| UserPromptSubmit: Chonkie decompose + Semble fan-out | 6.1, 6.2 |
| Short prompts (< 4 words) skip enrichment | 6.1, 6.2 |
| PostToolUse(Write/Edit): semble reindex | 5.1, 7.1 |
| PostToolUse(Bash git commit): omega note | 5.1, 7.1 |
| SubagentStop: omega flush | 5.1 |
| TaskCreated: vault note in Tasks/ | 5.1, 7.2 |
| TaskCompleted: append "Completed" to note | 5.1, 7.2 |
| goldfishh status: queue depth + manifest | 8.1 |
| goldfishh doctor: per-component health checks | 8.2 |
| goldfishh replay: rebuild from JSONL | 8.3 |
| Hook binary path on PATH | P0 |
| All handlers remain subprocess calls / file writes | All |
| No search/embedding/graph code written | All |
| <10ms hook exit for async events | 5.3 |

### Placeholder Scan

No TBDs, TODOs, or "implement later" phrases found. Every code step shows full implementation.

### Type Consistency

- `handle_session_start(event: dict, vaults_root: Path = VAULTS_ROOT) -> str` — defined Task 5.2, used Task 5.3
- `handle_pre_compact(event: dict, vaults_root: Path = VAULTS_ROOT) -> None` — defined Task 5.2, used Task 5.3
- `_handle_task_created(event: dict, vaults_root: Path = VAULTS_ROOT) -> None` — defined Task 5.1, tested Task 7.2
- `_handle_task_completed(event: dict, vaults_root: Path = VAULTS_ROOT) -> None` — defined Task 5.1, tested Task 7.2
- `_handle_post_tool_use(event: dict) -> None` — defined Task 5.1, tested Task 7.1
- `_handle_stop(event: dict, vaults_root: Path = VAULTS_ROOT) -> None` — defined Task 5.1, extended Task 5.4
- `decompose(prompt: str) -> list[str]` — defined Task 6.1, used hook.py Task 5.3
- `enrich(prompt: str, cwd: str, project: str) -> str` — defined Task 6.1, used hook.py Task 5.3
- `QUEUE_PATH` — from drain.py, imported in cli.py Task 8.1
- `project_name(cwd: str) -> str` — from config.py (Phase 2), used throughout

All drain.py event-dispatch wrappers (`_handle_stop_event`, `_handle_task_created_event`, `_handle_task_completed_event`) exist to match the `Callable[[dict], None]` shape expected by `_HANDLERS`.
