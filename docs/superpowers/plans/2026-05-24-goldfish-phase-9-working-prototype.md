# Goldfish Phase 9 — Fully Working Prototype

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all gaps between the implemented codebase and the PRD so that every Claude Code hook fires correctly, every event gets processed, and the prompt enrichment draws from all three memory layers.

**Architecture:** Five targeted fixes: (1) hook registration uses upsert-not-skip so the full binary path always wins; (2) all nine hook events get registered including the four that are currently missing; (3) drain gets a time budget and auto-fires at SessionStart and PreCompact; (4) enricher fans out to OMEGA in addition to Semble; (5) init is idempotent and CLAUDE.md block updates in-place.

**Tech Stack:** Python 3.11+, typer, pathlib, subprocess, time (stdlib). No new dependencies.

**Current state after Phase 8:**
- 60 tests passing
- `settings.json` has bare `"goldfishh hook"` (no path), causing `goldfishh: not found` on every hook
- `_ASYNC_HOOKS` is missing PostToolUse, SubagentStop, TaskCreated, TaskCompleted
- Queue never drains automatically — async events accumulate forever
- Enricher calls Semble but not OMEGA memory layer
- `goldfishh init` reinstalls tools on every run
- `append_claude_md_block` silently skips when block already exists

---

## File Map

```
src/goldfishh/
├── claude_md.py  ← upsert hook entries, create parent dir, add missing events (Task 9.0, 9.4)
├── cli.py        ← add register-hooks command (Task 9.0)
├── drain.py      ← add budget_ms to drain(), auto-trigger in session handlers (Task 9.1)
├── enricher.py   ← add omega query per chunk (Task 9.2)
└── init.py       ← check if tools installed before running, better output (Task 9.3, 9.4)

tests/
├── test_claude_md.py  ← update path-update test, add missing-events test, add update-in-place test
├── test_cli.py        ← add register-hooks test
├── test_drain.py      ← add budget_ms test, add auto-trigger test
├── test_enricher.py   ← add omega query test
└── test_init.py       ← NEW: idempotency tests
```

---

### Task 9.0: Fix `register_hooks` — upsert path, add missing events, add CLI command

**Problem:** `settings.json` has `"goldfishh hook"` (bare command). The `_already_registered` check returns True for any existing goldfishh hook entry, so the full path from `_detect_goldfish_bin()` is never written. Additionally, PostToolUse, SubagentStop, TaskCreated, TaskCompleted are not in `_ASYNC_HOOKS` so they never get registered.

**Fix:** Replace skip-if-found with remove-and-add (`_upsert_hook`). Add all 6 async events. Ensure parent dir is created before writing settings.json. Add `goldfishh register-hooks` CLI command.

**Files:**
- Modify: `src/goldfishh/claude_md.py`
- Modify: `src/goldfishh/cli.py`
- Modify: `tests/test_claude_md.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_claude_md.py` (keep all 5 existing tests):

```python
def test_register_hooks_updates_bare_command_to_full_path(tmp_path):
    """Existing 'goldfishh hook' (bare) must be replaced with the full detected path."""
    settings = tmp_path / "settings.json"
    # Pre-populate with bare command (simulates old settings.json state)
    settings.write_text(json.dumps({
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "goldfishh hook", "async": True}]}]
        }
    }))

    fake_venv_bin = tmp_path / "bin"
    fake_venv_bin.mkdir()
    (fake_venv_bin / "goldfishh").touch()

    with patch("goldfishh.claude_md.shutil.which", return_value=None), \
         patch("goldfishh.claude_md.sys.executable", str(fake_venv_bin / "python")):
        register_hooks(settings_path=settings)

    data = json.loads(settings.read_text())
    stop_cmds = [h["command"] for h in data["hooks"]["Stop"][0]["hooks"]]
    assert len(stop_cmds) == 1
    assert stop_cmds[0] != "goldfishh hook"
    assert stop_cmds[0].endswith(" hook")
    assert "goldfishh" in stop_cmds[0]


def test_register_hooks_registers_all_nine_events(tmp_path):
    """All sync + async events must be present after register_hooks."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({}))
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    registered = set(data["hooks"].keys())
    required = {
        "SessionStart", "UserPromptSubmit", "PreCompact",
        "Stop", "SessionEnd", "PostToolUse", "SubagentStop",
        "TaskCreated", "TaskCompleted",
    }
    assert required == registered


def test_register_hooks_preserves_non_goldfish_hooks(tmp_path):
    """GitNexus or other tool hooks must not be removed."""
    settings = tmp_path / "settings.json"
    gitnexus_hook = {"type": "command", "command": "npx gitnexus hook"}
    settings.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{"hooks": [gitnexus_hook]}],
        }
    }))
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    pre_tool_hooks = data["hooks"]["PreToolUse"][0]["hooks"]
    assert gitnexus_hook in pre_tool_hooks
```

Add to `tests/test_cli.py`:

```python
def test_register_hooks_command(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({}))
    with patch("goldfishh.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfishh.claude_md.shutil.which", return_value="/usr/local/bin/goldfishh"):
        result = runner.invoke(app, ["register-hooks"])
    assert result.exit_code == 0
    assert "hooks" in result.output.lower() or "registered" in result.output.lower()
    data = json.loads(settings.read_text())
    assert "Stop" in data.get("hooks", {})
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest tests/test_claude_md.py::test_register_hooks_updates_bare_command_to_full_path tests/test_claude_md.py::test_register_hooks_registers_all_nine_events tests/test_claude_md.py::test_register_hooks_preserves_non_goldfish_hooks tests/test_cli.py::test_register_hooks_command -v
```

Expected: FAIL — bare command not updated, missing events, no register-hooks command

- [ ] **Step 3: Rewrite `src/goldfishh/claude_md.py`**

Replace the entire file:

```python
import json
import re
import shutil
import sys
from pathlib import Path

DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"
GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfishh)"

_SYNC_HOOKS = ["SessionStart", "UserPromptSubmit", "PreCompact"]
_ASYNC_HOOKS = [
    "Stop", "SessionEnd", "PostToolUse", "SubagentStop",
    "TaskCreated", "TaskCompleted",
]


def _detect_goldfish_bin() -> str:
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
    return "goldfishh" in cmd and "hook" in cmd


def _upsert_hook(hooks: dict, event: str, bin_path: str, async_: bool) -> None:
    """Remove all stale goldfishh hook entries for event and insert a fresh one."""
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
```

- [ ] **Step 4: Add `register-hooks` command to `src/goldfishh/cli.py`**

Add after the `doctor` command (before the `replay` stub at the bottom):

```python
@app.command(name="register-hooks")
def register_hooks_cmd() -> None:
    """Update Claude Code hook registrations with the correct goldfishh binary path."""
    from goldfishh.claude_md import register_hooks
    register_hooks(settings_path=DEFAULT_SETTINGS)
    typer.echo(f"Hooks registered in {DEFAULT_SETTINGS}")
```

- [ ] **Step 5: Run all tests — verify pass**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest -v 2>&1 | tail -15
```

Expected: all tests pass (63+)

- [ ] **Step 6: Apply the fix to the real settings.json immediately**

```bash
cd /home/tchawes/goldfishh && .venv/bin/goldfishh register-hooks
```

Expected output: `Hooks registered in /home/tchawes/.claude/settings.json`

Verify the fix:
```bash
python3 -c "import json; d=json.load(open('/home/tchawes/.claude/settings.json')); [print(k, d['hooks'][k][0]['hooks'][0]['command']) for k in sorted(d['hooks'])]"
```

Expected: all entries show the full path (`.venv/bin/goldfishh hook`), all 9 events registered

- [ ] **Step 7: Commit**

```bash
cd /home/tchawes/goldfishh && git add src/goldfishh/claude_md.py src/goldfishh/cli.py tests/test_claude_md.py tests/test_cli.py && git commit -m "fix: register_hooks upserts full path, registers all 9 hook events"
```

---

### Task 9.1: Add time-budgeted drain with auto-trigger in session handlers

**Problem:** Async events (Stop, PostToolUse, etc.) accumulate in `queue.jsonl` but `drain()` is never called automatically. There is also no time budget — drain currently processes ALL events with no time limit, blocking Claude if the queue is large.

**Fix:** Add `budget_ms` parameter to `drain()` (0 = no limit). Call `drain(budget_ms=200)` at the start of `handle_session_start()` and `handle_pre_compact()` so the queue drains at each synchronous hook.

**Files:**
- Modify: `src/goldfishh/drain.py`
- Modify: `tests/test_drain.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_drain.py`:

```python
import time


def test_drain_budget_zero_processes_all(tmp_path):
    """budget_ms=0 (default) means no time limit — all events processed."""
    queue = tmp_path / "queue.jsonl"
    events = [{"type": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfishh.drain.subprocess.run"):
        count = drain(queue=queue, budget_ms=0)
    assert count == 3
    assert queue.read_text().strip() == ""


def test_drain_budget_ms_leaves_unprocessed_events(tmp_path):
    """When budget expires, remaining events stay in queue for next cycle."""
    queue = tmp_path / "queue.jsonl"
    events = [{"type": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    with patch("goldfishh.drain.subprocess.run"), \
         patch("goldfishh.drain.time.monotonic", side_effect=[0, 100]):
        # deadline=0+0.001=0.001, first loop check returns 100 → immediate expire
        count = drain(queue=queue, budget_ms=1)

    assert count == 0
    remaining = [l for l in queue.read_text().splitlines() if l.strip()]
    assert len(remaining) == 3


def test_session_start_auto_drains_queue(tmp_path):
    """handle_session_start must call drain(budget_ms=200) before processing."""
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfishh.drain.subprocess.run"), \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.drain.drain") as mock_drain:
        mock_drain.return_value = 0
        handle_session_start(event, vaults_root=tmp_path)
    mock_drain.assert_called_once_with(budget_ms=200)


def test_pre_compact_auto_drains_queue(tmp_path):
    """handle_pre_compact must call drain(budget_ms=200) before snapshotting."""
    from goldfishh.vault import scaffold
    scaffold("myapp", vaults_root=tmp_path)
    event = {"type": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfishh.drain.subprocess.run"), \
         patch("goldfishh.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path), \
         patch("goldfishh.drain.drain") as mock_drain:
        mock_drain.return_value = 0
        handle_pre_compact(event, vaults_root=tmp_path)
    mock_drain.assert_called_once_with(budget_ms=200)
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest tests/test_drain.py::test_drain_budget_zero_processes_all tests/test_drain.py::test_drain_budget_ms_leaves_unprocessed_events tests/test_drain.py::test_session_start_auto_drains_queue tests/test_drain.py::test_pre_compact_auto_drains_queue -v
```

Expected: FAIL — drain() has no budget_ms param, session handlers don't call drain

- [ ] **Step 3: Add `import time` and update `drain()` in `src/goldfishh/drain.py`**

At the top of `drain.py`, add `import time` after `import json`:

```python
import json
import subprocess
import time
from datetime import datetime
```

Replace the `drain()` function (currently lines 12-33):

```python
def drain(queue: Path = QUEUE_PATH, budget_ms: float = 0) -> int:
    """Process queued events. budget_ms=0 means no limit."""
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
```

- [ ] **Step 4: Add auto-drain calls to `handle_session_start` and `handle_pre_compact`**

In `handle_session_start` (currently line 129), add `drain(budget_ms=200)` as the FIRST line of the function body:

```python
def handle_session_start(event: dict, vaults_root: Path = VAULTS_ROOT) -> str:
    drain(budget_ms=200)  # process previous session's async events before this one
    cwd = event.get("cwd", ".")
    # ... rest of function unchanged
```

In `handle_pre_compact` (currently line 204), add the drain call as the FIRST line:

```python
def handle_pre_compact(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    drain(budget_ms=200)  # flush queue before taking a snapshot
    cwd = event.get("cwd", ".")
    # ... rest of function unchanged
```

- [ ] **Step 5: Run all tests — verify pass**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest -v 2>&1 | tail -15
```

Expected: all tests pass

Note: existing `test_session_start_*` and `test_pre_compact_*` tests still pass because: (a) `drain(budget_ms=200)` is called with the real `QUEUE_PATH` which is empty at `~/.goldfishh/queue.jsonl`, so it returns 0 immediately without calling subprocess; OR (b) if you want to be extra safe, you can add `patch("goldfishh.drain.drain", return_value=0)` to those tests — but it's not required.

- [ ] **Step 6: Commit**

```bash
cd /home/tchawes/goldfishh && git add src/goldfishh/drain.py tests/test_drain.py && git commit -m "feat: time-budgeted drain with auto-trigger in SessionStart and PreCompact"
```

---

### Task 9.2: Add OMEGA query to enricher.py

**Problem:** PRD Flow 3 specifies fan-out to three layers: `semble search` (code), `semble search --content docs` (vault), and `omega query` (memory). Current `enricher.py` only calls Semble — OMEGA memory is never queried during prompt enrichment.

**Fix:** Add `omega query <chunk>` subprocess call per chunk. Include memory results in the formatted context block under a `**Memory:**` header.

**Files:**
- Modify: `src/goldfishh/enricher.py`
- Modify: `tests/test_enricher.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_enricher.py`:

```python
def test_enrich_calls_omega_query_per_chunk():
    """enrich() must call omega query for memory hits alongside semble calls."""
    mock_result = MagicMock()
    mock_result.stdout = b"relevant result"
    mock_result.returncode = 0
    with patch("goldfishh.enricher.subprocess.run", return_value=mock_result) as mock_run:
        enrich("fix the authentication middleware in the API layer", "/project", "myapp")
    # Expect: semble code, semble docs, omega query — at least 3 calls per chunk
    assert mock_run.call_count >= 3
    all_cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(cmd[0] == "omega" for cmd in all_cmds)


def test_enrich_includes_memory_section_in_output():
    """When omega returns results, output must contain a Memory section."""
    def fake_run(cmd, *args, **kwargs):
        m = MagicMock()
        if cmd[0] == "omega":
            m.stdout = b"" if not isinstance(m.stdout, bytes) else m.stdout
            m.stdout = b"past decision: use JWT"
            m.returncode = 0
        else:
            m.stdout = b""
            m.returncode = 0
        return m

    with patch("goldfishh.enricher.subprocess.run", side_effect=fake_run):
        result = enrich("fix the authentication middleware in the API layer", "/project", "myapp")

    assert "Memory" in result
    assert "past decision" in result
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest tests/test_enricher.py::test_enrich_calls_omega_query_per_chunk tests/test_enricher.py::test_enrich_includes_memory_section_in_output -v
```

Expected: FAIL — omega not called, no Memory section

- [ ] **Step 3: Update `src/goldfishh/enricher.py`**

Replace the `enrich` function:

```python
def enrich(prompt: str, cwd: str, project: str) -> str:
    """Decompose prompt and fan out to Semble (code + vault) and OMEGA (memory) per chunk."""
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
        mem_result = subprocess.run(
            ["omega", "query", chunk],
            capture_output=True, check=False,
        )

        code_out = code_result.stdout.decode(errors="replace").strip()
        docs_out = docs_result.stdout.decode(errors="replace").strip()
        mem_out = mem_result.stdout.decode(errors="replace").strip() if mem_result.returncode == 0 else ""

        if code_out or docs_out or mem_out:
            section = f"### Query: {chunk}\n"
            if code_out:
                section += f"\n**Code:**\n{code_out}\n"
            if docs_out:
                section += f"\n**Vault:**\n{docs_out}\n"
            if mem_out:
                section += f"\n**Memory:**\n{mem_out}\n"
            sections.append(section)

    if not sections:
        return ""

    return "## Goldfish Context\n\n" + "\n\n".join(sections)
```

- [ ] **Step 4: Run all tests — verify pass**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest -v 2>&1 | tail -15
```

Expected: all tests pass. Note: `test_enrich_calls_semble_for_code_and_docs` now expects `call_count >= 2` — since we added omega, call_count is now 3. Verify the assertion is `>= 2` (not `== 2`) — it already is.

- [ ] **Step 5: Commit**

```bash
cd /home/tchawes/goldfishh && git add src/goldfishh/enricher.py tests/test_enricher.py && git commit -m "feat: enricher fans out to OMEGA memory layer alongside Semble"
```

---

### Task 9.3: Fix init.py idempotency

**Problem:** `goldfishh init` runs `npm install -g gitnexus`, `pip install omega-memory`, and `uv tool install semble` unconditionally. Re-running takes minutes and produces noisy output. PRD requires: "Given an existing configuration, re-running init reports health rather than overwriting."

**Fix:** Check if each tool is already installed/indexed before running the install command. Print ✓/✗ status per component. Use `shutil.which()` for CLI tools and directory existence for the GitNexus index.

**Files:**
- Modify: `src/goldfishh/init.py`
- Create: `tests/test_init.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_init.py`:

```python
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from goldfishh.init import run


def test_init_skips_gitnexus_if_already_indexed(tmp_path):
    """If .gitnexus/ exists, npx gitnexus analyze must NOT run."""
    (tmp_path / ".gitnexus").mkdir()
    settings = tmp_path / "settings.json"

    with patch("goldfishh.init.check_dependency", return_value=True), \
         patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"), \
         patch("goldfishh.init.subprocess.run") as mock_run, \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_analyze_ran = any(
        isinstance(c, list) and "gitnexus" in c and "analyze" in c
        for c in cmds
    )
    assert not gitnexus_analyze_ran, "gitnexus analyze must not run when .gitnexus/ already exists"


def test_init_skips_omega_if_already_installed(tmp_path):
    """If omega CLI is found on PATH, pip install omega-memory must NOT run."""
    settings = tmp_path / "settings.json"

    with patch("goldfishh.init.check_dependency", return_value=True), \
         patch("goldfishh.init.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd), \
         patch("goldfishh.init.subprocess.run") as mock_run, \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    pip_install_ran = any(
        isinstance(c, list) and "pip" in c and "omega-memory" in c
        for c in cmds
    )
    assert not pip_install_ran, "pip install omega-memory must not run when omega already on PATH"


def test_init_skips_semble_if_already_installed(tmp_path):
    """If semble CLI is found on PATH, uv tool install semble must NOT run."""
    settings = tmp_path / "settings.json"

    with patch("goldfishh.init.check_dependency", return_value=True), \
         patch("goldfishh.init.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd), \
         patch("goldfishh.init.subprocess.run") as mock_run, \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    semble_install_ran = any(
        isinstance(c, list) and "semble" in c and "install" in c
        for c in cmds
    )
    assert not semble_install_ran, "uv tool install semble must not run when semble already on PATH"


def test_init_runs_gitnexus_when_not_indexed(tmp_path):
    """If .gitnexus/ does not exist, npx gitnexus analyze must run."""
    settings = tmp_path / "settings.json"

    with patch("goldfishh.init.check_dependency", return_value=True), \
         patch("goldfishh.init.shutil.which", return_value=None), \
         patch("goldfishh.init.subprocess.run") as mock_run, \
         patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_analyze_ran = any(
        isinstance(c, list) and "gitnexus" in c and "analyze" in c
        for c in cmds
    )
    assert gitnexus_analyze_ran, "gitnexus analyze must run when .gitnexus/ does not exist"
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest tests/test_init.py -v
```

Expected: FAIL — init always runs all installs regardless of existing state

- [ ] **Step 3: Rewrite `src/goldfishh/init.py`**

Replace the entire file:

```python
import shutil
import subprocess
import sys
from pathlib import Path

from goldfishh.claude_md import GOLDFISH_SENTINEL, append_claude_md_block, register_hooks
from goldfishh.config import (
    DEFAULT_SETTINGS,
    VAULTS_ROOT,
    get_manifest,
    is_new_project,
    project_name,
    write_manifest,
)
from goldfishh.vault import scaffold

_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

### Before any non-trivial task — query all three layers:

#### Code + Impact Intelligence — GitNexus (MCP)
- `query({{query}})` — hybrid BM25+semantic search across code graph
- `context({{name}})` — 360° view of any symbol (callers, callees, processes)
- `impact({{target}}, direction="upstream")` — blast radius before ANY change
- `detect_changes()` — map staged changes to affected processes pre-commit

#### Episodic Memory — OMEGA (MCP)
- `omega_query("why did we choose JWT")` — past decisions
- `omega_query("rate limiter bug")` — known issues
- `omega_query("Sarah rate limiter")` — person + topic references

#### Semantic Search — Semble (MCP/CLI)
- `semble search <query> ./src` — code search by meaning
- `semble search <query> ~/.goldfishh/vaults/<project> --content docs` — vault notes

### Mandatory workflow before refactoring:
1. `gitnexus context({{name}})` → understand the symbol
2. `gitnexus impact({{target}})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.
"""


def check_dependency(cmd: str) -> bool:
    result = subprocess.run([cmd, "--version"], capture_output=True)
    return result.returncode == 0


def run(
    cwd: str = ".",
    settings_path: Path = DEFAULT_SETTINGS,
    vaults_root: Path = VAULTS_ROOT,
) -> None:
    project = project_name(cwd)

    if not check_dependency("node"):
        print("✗ Node.js missing — required for GitNexus. Install from https://nodejs.org")
        sys.exit(1)
    print("✓ Node.js found")

    # GitNexus — skip if already indexed
    gitnexus_index = Path(cwd) / ".gitnexus"
    if gitnexus_index.exists():
        print("✓ GitNexus already indexed")
    else:
        print("  Installing GitNexus...")
        result = subprocess.run(["npm", "install", "-g", "gitnexus"], capture_output=True)
        if result.returncode != 0:
            print("  note: global npm install failed; using npx")
        subprocess.run(["npx", "gitnexus", "analyze"], cwd=cwd, check=True)
        print("✓ GitNexus indexed")

    # OMEGA — skip if already installed
    if shutil.which("omega"):
        print("✓ OMEGA already installed")
    else:
        print("  Installing OMEGA...")
        subprocess.run(["pip", "install", "omega-memory"], check=True)
        subprocess.run(["omega", "setup"], check=True)
        print("✓ OMEGA installed")

    # Semble — skip if already installed
    if shutil.which("semble"):
        print("✓ Semble already installed")
    else:
        print("  Installing Semble...")
        subprocess.run(["uv", "tool", "install", "semble"], check=True)
        print("✓ Semble installed")

    # Vault
    if is_new_project(project, vaults_root=vaults_root):
        scaffold(project, vaults_root=vaults_root)
        write_manifest(project, get_manifest(project, vaults_root=vaults_root), vaults_root=vaults_root)
        print(f"✓ Vault scaffolded at {vaults_root / project}")
    else:
        print(f"✓ Vault exists at {vaults_root / project}")

    # Hooks — always upsert (ensures path and events are current)
    register_hooks(settings_path=settings_path)
    print("✓ Hooks registered")

    # CLAUDE.md
    claude_md = Path(cwd) / "CLAUDE.md"
    if claude_md.exists():
        append_claude_md_block(claude_md, _CLAUDE_MD_BLOCK)
        print("✓ CLAUDE.md updated")

    print(f"\n✓ goldfishh is ready.")
    print(f"  Vault:    {vaults_root / project}")
    print(f"  Obsidian: open {vaults_root / project} as a vault (optional, no plugins needed)")
```

- [ ] **Step 4: Run all tests — verify pass**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest -v 2>&1 | tail -15
```

Expected: all tests pass (67+)

- [ ] **Step 5: Commit**

```bash
cd /home/tchawes/goldfishh && git add src/goldfishh/init.py tests/test_init.py && git commit -m "feat: idempotent init — skips already-installed tools, better status output"
```

---

### Task 9.4: Fix `append_claude_md_block` to update in-place + update CLAUDE.md content

**Problem:** (1) `append_claude_md_block` already has the update-in-place regex logic added in Task 9.0 — this task tests it thoroughly. (2) The `_CLAUDE_MD_BLOCK` in `init.py` was updated in Task 9.3. (3) The existing `test_append_claude_md_block_is_idempotent` test only checks the sentinel isn't duplicated, but doesn't verify the content was actually updated.

**Fix:** Add tests that verify: second call updates content (not just deduplicates sentinel), block between two real sections is correctly bounded, EOF case works correctly.

**Files:**
- Modify: `tests/test_claude_md.py`

(Note: the implementation is already done in Task 9.0 — this task adds the verification tests.)

- [ ] **Step 1: Write tests**

Add to `tests/test_claude_md.py`:

```python
def test_append_claude_md_block_updates_content_in_place(tmp_path):
    """Second call with different content must update the block, not duplicate it."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Project\n\nSome existing content.\n")

    old_block = GOLDFISH_SENTINEL + "\n\nOLD CONTENT HERE\n"
    new_block = GOLDFISH_SENTINEL + "\n\nNEW CONTENT HERE\n"

    append_claude_md_block(claude_md, old_block)
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert content.count(GOLDFISH_SENTINEL) == 1
    assert "NEW CONTENT HERE" in content
    assert "OLD CONTENT HERE" not in content


def test_append_claude_md_block_preserves_content_after_block(tmp_path):
    """Content in sections after the goldfishh block must be preserved on update."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "# Project\n\n"
        + GOLDFISH_SENTINEL + "\n\nOLD CONTENT\n\n"
        + "## Other Section\n\nKeep this.\n"
    )

    new_block = GOLDFISH_SENTINEL + "\n\nNEW CONTENT\n"
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert "Keep this." in content
    assert "NEW CONTENT" in content
    assert "OLD CONTENT" not in content
    assert content.count(GOLDFISH_SENTINEL) == 1


def test_append_claude_md_block_eof_case(tmp_path):
    """Block at EOF (no following sections) must be replaced cleanly."""
    claude_md = tmp_path / "CLAUDE.md"
    old_block = GOLDFISH_SENTINEL + "\n\nOLD\n"
    claude_md.write_text("# Header\n\n" + old_block)

    new_block = GOLDFISH_SENTINEL + "\n\nNEW\n"
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert "NEW" in content
    assert "OLD" not in content
    assert content.count(GOLDFISH_SENTINEL) == 1
```

- [ ] **Step 2: Run new tests**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest tests/test_claude_md.py::test_append_claude_md_block_updates_content_in_place tests/test_claude_md.py::test_append_claude_md_block_preserves_content_after_block tests/test_claude_md.py::test_append_claude_md_block_eof_case -v
```

Expected: PASS (implementation was completed in Task 9.0)

If any fail, the `append_claude_md_block` update logic in Task 9.0 has a bug — fix it before committing.

- [ ] **Step 3: Run full test suite**

```bash
cd /home/tchawes/goldfishh && .venv/bin/pytest -v 2>&1 | tail -15
```

Expected: all tests pass (70+)

- [ ] **Step 4: Commit**

```bash
cd /home/tchawes/goldfishh && git add tests/test_claude_md.py && git commit -m "test: comprehensive append_claude_md_block update-in-place coverage"
```

---

## Self-Review

### Spec Coverage

| PRD Requirement | Task |
|---|---|
| Hooks use full binary path (no `goldfishh: not found`) | 9.0 |
| All 9 hook events registered: SessionStart, UserPromptSubmit, PreCompact, Stop, SessionEnd, PostToolUse, SubagentStop, TaskCreated, TaskCompleted | 9.0 |
| `goldfishh register-hooks` command for manual path fix | 9.0 |
| Queue drains automatically — no manual `goldfishh drain` required | 9.1 |
| Drain has 200ms budget, leaves remaining for next cycle | 9.1 |
| Prompt enrichment fans out to OMEGA memory in addition to Semble | 9.2 |
| `goldfishh init` is idempotent — re-run reports health, doesn't reinstall | 9.3 |
| `append_claude_md_block` updates in-place on second run, not duplicated | 9.0, 9.4 |
| CLAUDE.md block matches full PRD spec (all three layers, all tools) | 9.3 |
| All existing 60 tests continue to pass | All |

### Placeholder Scan

No TBDs, TODOs, or placeholders. Every code step shows the complete implementation.

### Type Consistency

- `drain(queue: Path = QUEUE_PATH, budget_ms: float = 0) -> int` — defined Task 9.1, called with `drain(budget_ms=200)` in same file
- `enrich(prompt: str, cwd: str, project: str) -> str` — signature unchanged, body extended
- `run(cwd: str, settings_path: Path, vaults_root: Path) -> None` — signature unchanged
- `append_claude_md_block(claude_md_path: Path, block: str) -> None` — signature unchanged
- `_upsert_hook(hooks: dict, event: str, bin_path: str, async_: bool) -> None` — new helper, used only in `register_hooks`
