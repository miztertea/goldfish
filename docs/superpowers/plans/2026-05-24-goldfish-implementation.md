# Goldfish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build goldfish, a thin Python orchestrator (~400–600 lines) that wires OMEGA + GitNexus + Semble + Chonkie into a coherent agent memory OS for Claude Code.

**Architecture:** Event-driven orchestration layer — Claude Code hook events write to a JSONL queue, a drain process routes events to subprocess tool calls and vault file writes. No custom search, embedding, or graph code: every function is a subprocess call, a file write, or a config read.

**Tech Stack:** Python 3.11+, hatchling (build), typer (CLI), tomli-w (config), PyYAML (frontmatter), pytest (testing). Runtime deps installed by init wizard: GitNexus (npm), OMEGA (pip), Semble (uv), Chonkie (pip).

---

## File Map

```
src/goldfish/
├── __init__.py
├── cli.py       ← typer app; thin dispatch layer only
├── config.py    ← reads/writes ~/.goldfish/config.toml + per-project .manifest.toml
├── hook.py      ← reads stdin JSON, appends to queue.jsonl, exits (<10ms)
├── drain.py     ← reads queue, routes events to subprocess/OMEGA/vault
├── vault.py     ← pathlib-only file writes; YAML frontmatter; no network
├── claude_md.py ← surgically appends to CLAUDE.md; updates settings.json hooks
└── init.py      ← wizard: detect, install, scaffold, register

tests/
├── conftest.py
├── test_hook.py
├── test_drain.py
├── test_vault.py
├── test_config.py
├── test_claude_md.py
└── test_init.py
```

---

## Phase 1 — Tracer Bullet

Proves the end-to-end call chain: `hook.py` writes one event to `queue.jsonl`, `drain.py` reads it and calls semble as a subprocess. **Nothing else.**

**Milestone:** `pytest` passes. `echo '{"type":"Stop","cwd":"."}' | python -m goldfish.hook` writes one line to `~/.goldfish/queue.jsonl`. `python -m goldfish.drain` clears the queue and calls semble.

---

### Task 1.1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/goldfish/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "goldfish"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["src/goldfish"]
```

- [ ] **Step 2: Create package and test directories**

```bash
mkdir -p src/goldfish tests
touch src/goldfish/__init__.py tests/__init__.py
```

- [ ] **Step 3: Install in editable dev mode**

```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 4: Verify pytest runs with zero tests**

```bash
pytest
```
Expected: `no tests ran` — exit 0

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: project scaffold with hatchling and pytest"
```

---

### Task 1.2: `hook.py` — write event to queue

**Files:**
- Create: `src/goldfish/hook.py`
- Create: `tests/test_hook.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_hook.py`:

```python
import json
from pathlib import Path

from goldfish.hook import handle


def test_hook_appends_event_to_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "session_id": "abc123"}
    handle(event, queue=queue)
    lines = queue.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == event


def test_hook_appends_multiple_events_in_order(tmp_path):
    queue = tmp_path / "queue.jsonl"
    handle({"type": "Stop", "n": 1}, queue=queue)
    handle({"type": "Stop", "n": 2}, queue=queue)
    lines = queue.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["n"] == 1
    assert json.loads(lines[1])["n"] == 2


def test_hook_creates_parent_dirs(tmp_path):
    queue = tmp_path / "nested" / "dir" / "queue.jsonl"
    handle({"type": "Stop"}, queue=queue)
    assert queue.exists()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_hook.py -v
```
Expected: `ImportError: cannot import name 'handle' from 'goldfish.hook'`

- [ ] **Step 3: Implement `hook.py`**

Create `src/goldfish/hook.py`:

```python
import json
import sys
from pathlib import Path

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def handle(event: dict, queue: Path = QUEUE_PATH) -> None:
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("a") as f:
        f.write(json.dumps(event) + "\n")


def main() -> None:
    event = json.loads(sys.stdin.read())
    handle(event)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_hook.py -v
```
Expected: 3 passed

- [ ] **Step 5: Smoke test manually**

```bash
echo '{"type":"Stop","cwd":".","session_id":"test-123"}' | python -m goldfish.hook
cat ~/.goldfish/queue.jsonl
```
Expected: one JSON line printed

- [ ] **Step 6: Commit**

```bash
git add src/goldfish/hook.py tests/test_hook.py
git commit -m "feat: hook.py appends events to queue.jsonl"
```

---

### Task 1.3: `drain.py` — read queue and call semble

**Files:**
- Create: `src/goldfish/drain.py`
- Create: `tests/test_drain.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_drain.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

from goldfish.drain import drain


def test_drain_returns_zero_for_missing_queue(tmp_path):
    queue = tmp_path / "nonexistent.jsonl"
    assert drain(queue=queue) == 0


def test_drain_returns_zero_for_empty_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text("")
    assert drain(queue=queue) == 0


def test_drain_processes_one_event(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "cwd": "/home/user/project"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 1
    mock_run.assert_called_once()


def test_drain_clears_queue_after_processing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps({"type": "Stop", "cwd": "."}) + "\n")
    with patch("goldfish.drain.subprocess.run"):
        drain(queue=queue)
    assert queue.read_text() == ""


def test_drain_processes_multiple_events(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [{"type": "Stop", "cwd": "/p"}, {"type": "Stop", "cwd": "/p"}]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 2
    assert mock_run.call_count == 2


def test_drain_calls_semble_with_event_cwd(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "cwd": "/my/project"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        drain(queue=queue)
    args = mock_run.call_args[0][0]
    assert args[0] == "semble"
    assert "/my/project" in args
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_drain.py -v
```
Expected: `ImportError: cannot import name 'drain'`

- [ ] **Step 3: Implement `drain.py`**

Create `src/goldfish/drain.py`:

```python
import json
import subprocess
from pathlib import Path

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def drain(queue: Path = QUEUE_PATH) -> int:
    if not queue.exists():
        return 0
    lines = queue.read_text().splitlines()
    queue.write_text("")
    processed = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        _route(event)
        processed += 1
    return processed


def _route(event: dict) -> None:
    cwd = event.get("cwd", ".")
    subprocess.run(
        ["semble", "search", ".", cwd],
        capture_output=True,
        check=False,
    )


def main() -> None:
    count = drain()
    print(f"Drained {count} events")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```
Expected: 9 passed

- [ ] **Step 5: End-to-end smoke test (requires semble installed: `uv tool install semble`)**

```bash
# Write an event
echo '{"type":"Stop","cwd":"."}' | python -m goldfish.hook

# Drain it
python -m goldfish.drain

# Queue should be empty
cat ~/.goldfish/queue.jsonl
```
Expected: drain prints `Drained 1 events`, queue.jsonl is empty

- [ ] **Step 6: Commit**

```bash
git add src/goldfish/drain.py tests/test_drain.py
git commit -m "feat: drain.py reads queue and dispatches to semble subprocess"
```

---

**Phase 1 complete.** Core architecture proven: Claude Code hook event → `queue.jsonl` → semble subprocess.

---

## Phase 2 — Config & Vault Foundation

Establish the per-project state store (manifest) and vault write layer. Everything in phases 3–8 depends on these.

---

### Task 2.1: `config.py` — goldfish config and project manifest

**Files:**
- Create: `src/goldfish/config.py`
- Create: `tests/test_config.py`
- Modify: `pyproject.toml` — add `"tomli-w"` to `dependencies`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
from pathlib import Path
import pytest
from goldfish.config import is_new_project, project_name, write_manifest, get_manifest


def test_is_new_project_returns_true_when_no_manifest(tmp_path):
    assert is_new_project("myproject", vaults_root=tmp_path) is True


def test_is_new_project_returns_false_when_manifest_exists(tmp_path):
    write_manifest("myproject", {"bootstrap_complete": True}, vaults_root=tmp_path)
    assert is_new_project("myproject", vaults_root=tmp_path) is False


def test_write_and_get_manifest_roundtrip(tmp_path):
    data = {"last_byte_offset": 48291, "bootstrap_complete": False, "semble_indexed_at": ""}
    write_manifest("myproject", data, vaults_root=tmp_path)
    result = get_manifest("myproject", vaults_root=tmp_path)
    assert result["last_byte_offset"] == 48291
    assert result["bootstrap_complete"] is False


def test_project_name_from_cwd():
    assert project_name("/home/user/goldfish") == "goldfish"
    assert project_name("/home/user/my-project") == "my-project"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_config.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Add `tomli-w` to pyproject.toml**

In `pyproject.toml`, change:
```toml
dependencies = []
```
to:
```toml
dependencies = ["tomli-w"]
```

Then:
```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 4: Implement `config.py`**

Create `src/goldfish/config.py`:

```python
from pathlib import Path
import tomllib
import tomli_w

VAULTS_ROOT = Path.home() / ".goldfish" / "vaults"
CONFIG_PATH = Path.home() / ".goldfish" / "config.toml"

_MANIFEST_DEFAULTS = {
    "last_byte_offset": 0,
    "last_jsonl_file": "",
    "bootstrap_complete": False,
    "semble_indexed_at": "",
}


def project_name(cwd: str) -> str:
    return Path(cwd).name


def _manifest_path(project: str, vaults_root: Path = VAULTS_ROOT) -> Path:
    return vaults_root / project / ".manifest.toml"


def is_new_project(project: str, vaults_root: Path = VAULTS_ROOT) -> bool:
    return not _manifest_path(project, vaults_root).exists()


def get_manifest(project: str, vaults_root: Path = VAULTS_ROOT) -> dict:
    path = _manifest_path(project, vaults_root)
    if not path.exists():
        return dict(_MANIFEST_DEFAULTS)
    with path.open("rb") as f:
        return {**_MANIFEST_DEFAULTS, **tomllib.load(f)}


def write_manifest(project: str, data: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    path = _manifest_path(project, vaults_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(data, f)
```

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```
Expected: 13 passed

- [ ] **Step 6: Commit**

```bash
git add src/goldfish/config.py tests/test_config.py pyproject.toml
git commit -m "feat: config.py with manifest read/write and project identity"
```

---

### Task 2.2: `vault.py` — markdown file operations

**Files:**
- Create: `src/goldfish/vault.py`
- Create: `tests/test_vault.py`
- Modify: `pyproject.toml` — add `"PyYAML"` to `dependencies`

- [ ] **Step 1: Write failing tests**

Create `tests/test_vault.py`:

```python
from pathlib import Path
import yaml
import pytest
from goldfish.vault import scaffold, write_note, read_note

FRONTMATTER = {
    "id": "decision-jwt-2026-05-24",
    "type": "decision",
    "valid_from": "2026-05-24",
    "superseded_by": None,
    "confidence": 0.95,
    "source_session": "abc123",
    "source_offset": 100,
    "related": [],
}


def test_scaffold_creates_required_dirs(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    for d in ["Memory/Decisions", "Memory/Lessons", "Memory/Errors",
              "Memory/Checkpoints", "Specs", "Tasks", "_context"]:
        assert (tmp_path / "myproject" / d).is_dir()


def test_scaffold_is_idempotent(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    scaffold("myproject", vaults_root=tmp_path)  # should not raise


def test_write_note_creates_file_at_correct_path(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    write_note("myproject", "Memory/Decisions/jwt.md", FRONTMATTER, "We chose JWT.", vaults_root=tmp_path)
    assert (tmp_path / "myproject" / "Memory" / "Decisions" / "jwt.md").exists()


def test_read_note_roundtrip(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    write_note("myproject", "Memory/Decisions/jwt.md", FRONTMATTER, "We chose JWT.", vaults_root=tmp_path)
    fm, body = read_note("myproject", "Memory/Decisions/jwt.md", vaults_root=tmp_path)
    assert fm["id"] == "decision-jwt-2026-05-24"
    assert fm["superseded_by"] is None
    assert body.strip() == "We chose JWT."


def test_write_note_produces_valid_yaml_frontmatter(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    write_note("myproject", "Memory/Decisions/jwt.md", FRONTMATTER, "body", vaults_root=tmp_path)
    content = (tmp_path / "myproject" / "Memory" / "Decisions" / "jwt.md").read_text()
    assert content.startswith("---\n")
    parts = content.split("---\n", 2)
    assert len(parts) == 3
    parsed = yaml.safe_load(parts[1])
    assert parsed["type"] == "decision"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_vault.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Add `PyYAML` to pyproject.toml dependencies, then reinstall**

```toml
dependencies = ["tomli-w", "PyYAML"]
```

```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 4: Implement `vault.py`**

Create `src/goldfish/vault.py`:

```python
from pathlib import Path
import yaml

VAULTS_ROOT = Path.home() / ".goldfish" / "vaults"

_VAULT_DIRS = [
    "Memory/Decisions",
    "Memory/Lessons",
    "Memory/Errors",
    "Memory/Checkpoints",
    "Specs",
    "Tasks",
    "_context",
]


def scaffold(project: str, vaults_root: Path = VAULTS_ROOT) -> None:
    for d in _VAULT_DIRS:
        (vaults_root / project / d).mkdir(parents=True, exist_ok=True)


def write_note(
    project: str,
    path: str,
    frontmatter: dict,
    body: str,
    vaults_root: Path = VAULTS_ROOT,
) -> None:
    note_path = vaults_root / project / path
    note_path.parent.mkdir(parents=True, exist_ok=True)
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    note_path.write_text(f"---\n{fm_str}---\n{body}\n", encoding="utf-8")


def read_note(
    project: str,
    path: str,
    vaults_root: Path = VAULTS_ROOT,
) -> tuple[dict, str]:
    content = (vaults_root / project / path).read_text(encoding="utf-8")
    _, fm_str, body = content.split("---\n", 2)
    return yaml.safe_load(fm_str), body
```

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```
Expected: 18 passed

- [ ] **Step 6: Commit**

```bash
git add src/goldfish/vault.py tests/test_vault.py pyproject.toml
git commit -m "feat: vault.py with scaffold, write_note, read_note"
```

---

## Phase 3 — CLI Entry Point + Hook Registration

Makes `goldfish hook` and `goldfish drain` runnable as Claude Code hook commands. After this phase, hooks can be manually wired into `~/.claude/settings.json` for testing.

---

### Task 3.1: `cli.py` — typer app with entry point

**Files:**
- Create: `src/goldfish/cli.py`
- Modify: `pyproject.toml` — add `typer` to dependencies and `[project.scripts]`

- [ ] **Step 1: Add typer and entry point to `pyproject.toml`**

```toml
dependencies = ["tomli-w", "PyYAML", "typer"]

[project.scripts]
goldfish = "goldfish.cli:app"
```

```bash
uv pip install -e ".[dev]"
```

- [ ] **Step 2: Create `src/goldfish/cli.py`**

```python
import sys
import typer
from goldfish import hook, drain

app = typer.Typer(no_args_is_help=True)


@app.command()
def hook_cmd(name: str = typer.Argument(None)) -> None:
    """Read a Claude Code hook event from stdin and enqueue it."""
    hook.main()


@app.command()
def drain_cmd() -> None:
    """Process queued events."""
    drain.main()


@app.command()
def init() -> None:
    """Install and configure all goldfish dependencies."""
    typer.echo("init: not yet implemented")


@app.command()
def status() -> None:
    """Show queue depth and tool health."""
    typer.echo("status: not yet implemented")


@app.command()
def doctor() -> None:
    """Check goldfish configuration and fix instructions."""
    typer.echo("doctor: not yet implemented")


@app.command()
def replay() -> None:
    """Rebuild vault from Claude Code JSONL transcripts."""
    typer.echo("replay: not yet implemented")


# Register subcommands under their hook-friendly names
app.registered_commands[0].name = "hook"
app.registered_commands[1].name = "drain"
```

- [ ] **Step 3: Verify CLI works**

```bash
goldfish --help
echo '{"type":"Stop","cwd":"."}' | goldfish hook
goldfish drain
```
Expected: help text shown; hook enqueues event; drain prints `Drained 1 events`

- [ ] **Step 4: Commit**

```bash
git add src/goldfish/cli.py pyproject.toml
git commit -m "feat: typer CLI with hook, drain, and stub commands"
```

---

### Task 3.2: `claude_md.py` — hook registration in `~/.claude/settings.json`

**Files:**
- Create: `src/goldfish/claude_md.py`
- Create: `tests/test_claude_md.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_claude_md.py`:

```python
import json
from pathlib import Path
from goldfish.claude_md import register_hooks, append_claude_md_block

GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"

_HOOKS_TO_REGISTER = [
    ("Stop", False),
    ("SessionStart", False),
    ("UserPromptSubmit", False),
    ("PreCompact", False),
]


def test_register_hooks_adds_entries(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    assert "hooks" in data
    assert "Stop" in data["hooks"]


def test_register_hooks_is_idempotent(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    register_hooks(settings_path=settings)
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"]
    goldfish_entries = [h for h in stop_hooks if "goldfish" in str(h)]
    assert len(goldfish_entries) == 1


def test_append_claude_md_block_adds_block(tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing content\n")
    append_claude_md_block(claude_md, GOLDFISH_SENTINEL + "\nsome content\n")
    assert GOLDFISH_SENTINEL in claude_md.read_text()


def test_append_claude_md_block_is_idempotent(tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing content\n")
    block = GOLDFISH_SENTINEL + "\nsome content\n"
    append_claude_md_block(claude_md, block)
    append_claude_md_block(claude_md, block)
    assert claude_md.read_text().count(GOLDFISH_SENTINEL) == 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_claude_md.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `claude_md.py`**

Create `src/goldfish/claude_md.py`:

```python
import json
from pathlib import Path

DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"
GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"

_SYNC_HOOKS = ["SessionStart", "UserPromptSubmit", "PreCompact"]
_ASYNC_HOOKS = ["Stop", "SessionEnd"]

_GOLDFISH_HOOK_COMMAND = "goldfish hook"


def _goldfish_hook_entry(async_: bool = False) -> dict:
    entry: dict = {"type": "command", "command": _GOLDFISH_HOOK_COMMAND}
    if async_:
        entry["async"] = True
    return entry


def _already_registered(hook_list: list) -> bool:
    return any(
        isinstance(h, dict) and _GOLDFISH_HOOK_COMMAND in h.get("command", "")
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

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```
Expected: 22 passed

- [ ] **Step 5: Commit**

```bash
git add src/goldfish/claude_md.py tests/test_claude_md.py
git commit -m "feat: claude_md.py registers hooks in settings.json idempotently"
```

---

## Phase 4 — Init Wizard

**Dogfood milestone at the end of this phase: `uvx goldfish init` runs on the goldfish repo itself.**

---

### Task 4.1: `init.py` — dependency detection and installation

**Files:**
- Create: `src/goldfish/init.py`
- Create: `tests/test_init.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_init.py`:

```python
from unittest.mock import patch, call
import pytest
from goldfish.init import check_dependency, run


def test_check_dependency_returns_true_when_found():
    with patch("goldfish.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert check_dependency("node") is True


def test_check_dependency_returns_false_when_not_found():
    with patch("goldfish.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        assert check_dependency("gitnexus-nonexistent") is False


def test_run_exits_early_if_node_missing(tmp_path):
    with patch("goldfish.init.check_dependency", return_value=False), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         pytest.raises(SystemExit):
        run(cwd=str(tmp_path))
    mock_run.assert_not_called()


def test_run_calls_install_steps_in_order(tmp_path):
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(cmd[0] if isinstance(cmd, list) else cmd)
        class R:
            returncode = 0
        return R()

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.subprocess.run", side_effect=fake_run), \
         patch("goldfish.init.register_hooks"), \
         patch("goldfish.init.scaffold"), \
         patch("goldfish.init.write_manifest"):
        run(cwd=str(tmp_path))

    assert "npm" in calls        # npm install -g gitnexus
    assert "npx" in calls        # npx gitnexus analyze
    assert "pip" in calls        # pip install omega-memory
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_init.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `init.py`**

Create `src/goldfish/init.py`:

```python
import subprocess
import sys
from pathlib import Path

from goldfish.claude_md import register_hooks, append_claude_md_block, GOLDFISH_SENTINEL
from goldfish.config import project_name, write_manifest, get_manifest, is_new_project, VAULTS_ROOT
from goldfish.vault import scaffold

_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

### Before any non-trivial task — query all three layers:

**GitNexus (MCP):** `query`, `context`, `impact`, `detect_changes`
**OMEGA (MCP):** `omega_query("why did we choose X")`
**Semble (MCP):** `semble_search(query, path=./src)`

### Mandatory workflow before refactoring:
1. `gitnexus context({{name}})` → understand the symbol
2. `gitnexus impact({{target}})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.
"""


def check_dependency(cmd: str) -> bool:
    result = subprocess.run([cmd, "--version"], capture_output=True)
    return result.returncode == 0


def run(cwd: str = ".") -> None:
    project = project_name(cwd)

    if not check_dependency("node"):
        print("ERROR: Node.js is required for GitNexus. Install from https://nodejs.org")
        sys.exit(1)

    print("Installing GitNexus...")
    subprocess.run(["npm", "install", "-g", "gitnexus"], check=True)
    subprocess.run(["npx", "gitnexus", "analyze"], cwd=cwd, check=True)

    print("Installing OMEGA...")
    subprocess.run(["pip", "install", "omega-memory"], check=True)
    subprocess.run(["omega", "setup"], check=True)

    print("Installing Semble...")
    subprocess.run(["uv", "tool", "install", "semble"], check=True)

    vault_root = VAULTS_ROOT / project
    if is_new_project(project):
        scaffold(project)
        write_manifest(project, get_manifest(project))
        print(f"Vault scaffolded at {vault_root}")
    else:
        print(f"Vault already exists at {vault_root} — skipping scaffold")

    register_hooks()

    claude_md = Path(cwd) / "CLAUDE.md"
    if claude_md.exists():
        append_claude_md_block(claude_md, _CLAUDE_MD_BLOCK)

    print(f"\ngoldfish is ready. Launch Claude Code to begin.")
    print(f"Vault: {vault_root}")
    print(f"Open {vault_root} in Obsidian for a visual knowledge graph (optional).")
```

- [ ] **Step 4: Wire `init` into `cli.py`**

Replace the stub `init` command in `src/goldfish/cli.py`:

```python
@app.command()
def init() -> None:
    """Install and configure all goldfish dependencies."""
    import os
    from goldfish.init import run as _init
    _init(cwd=os.getcwd())
```

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```
Expected: 26 passed

- [ ] **Step 6: Commit**

```bash
git add src/goldfish/init.py tests/test_init.py src/goldfish/cli.py
git commit -m "feat: init wizard installs GitNexus, OMEGA, Semble, scaffolds vault"
```

---

### Task 4.2: Dogfood Milestone — goldfish runs on goldfish

- [ ] **Step 1: Index goldfish's own code with GitNexus**

```bash
npx gitnexus analyze
```
Expected: `.gitnexus/` created in repo root; hooks installed; CLAUDE.md updated

- [ ] **Step 2: Run goldfish init on the goldfish repo**

```bash
uvx goldfish init
```
Expected: OMEGA installed, Semble installed, vault scaffolded at `~/.goldfish/vaults/goldfish/`, hooks registered in `~/.claude/settings.json`

- [ ] **Step 3: Verify hooks are registered**

```bash
cat ~/.claude/settings.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('hooks',{}), indent=2))"
```
Expected: `SessionStart`, `UserPromptSubmit`, `PreCompact`, `Stop`, `SessionEnd` all present with `goldfish hook` command

- [ ] **Step 4: Verify vault exists**

```bash
ls ~/.goldfish/vaults/goldfish/
```
Expected: `Memory/  Specs/  Tasks/  _context/  .manifest.toml`

- [ ] **Step 5: Commit**

```bash
git add .gitnexus/ CLAUDE.md
git commit -m "chore: dogfood — goldfish indexed and running on itself"
```

**From this point forward, every Claude Code session building Goldfish has OMEGA tracking sessions, GitNexus mapping the codebase, and Semble indexing goldfish's own src/.**

---

## Phase 5 — Session Lifecycle

Implement the `SessionStart`, `PreCompact`, and `Stop`/`SessionEnd` event handlers. After this phase, starting Claude Code in any project triggers a wake-up context note.

---

### Task 5.1: SessionStart routing (new vs. existing project)

**Files:**
- Modify: `src/goldfish/drain.py` — extend `_route` for `SessionStart`
- Modify: `src/goldfish/hook.py` — write stdout for synchronous events

**Key behaviors:**

- New project: run `semble index ./src` (if `src/` exists, else `.`), async omega mine, scaffold vault, write `_context/wake-up.md` with "First session — code search ready, memory building."
- Existing project: omega mine new bytes from `manifest.last_byte_offset`, semble reindex changed files, omega query for project state, write `_context/wake-up.md` with current tasks/decisions.
- `hook.py` must write the wake-up.md path to stdout for `SessionStart` (Claude Code injects this as context).

**Tests to write:**

```python
def test_session_start_new_project_scaffolds_vault(tmp_path, ...):
    # Given: no manifest
    # When: SessionStart event drained
    # Then: vault dirs created, wake-up.md exists

def test_session_start_writes_wake_up_path_to_stdout(...):
    # Given: SessionStart event
    # When: hook.main() called (subprocess mock)
    # Then: stdout contains path to wake-up.md

def test_session_start_existing_project_skips_scaffold(...):
    # Given: manifest exists
    # When: SessionStart event drained
    # Then: scaffold not called again
```

---

### Task 5.2: PreCompact snapshot

**Files:**
- Modify: `src/goldfish/drain.py` — add `_handle_pre_compact`

```python
def _handle_pre_compact(event: dict) -> None:
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
            "source_offset": get_manifest(project).get("last_byte_offset", 0),
            "related": [],
        },
        f"Session checkpoint before compaction.\nSession: {session_id}",
    )
```

---

### Task 5.3: Stop / SessionEnd cleanup

**Files:**
- Modify: `src/goldfish/drain.py`

```python
def _handle_stop(event: dict) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    subprocess.run(["omega", "flush", event.get("session_id", "")], capture_output=True, check=False)
    # update manifest last_byte_offset

def _handle_session_end(event: dict) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    wake_up = VAULTS_ROOT / project / "_context" / "wake-up.md"
    if wake_up.exists():
        wake_up.unlink()
```

---

## Phase 6 — Prompt Enrichment (UserPromptSubmit)

The only synchronous handler that injects context into Claude's prompt window.

---

### Task 6.1: `enricher.py` — Chonkie decomposition + fan-out search

**Files:**
- Create: `src/goldfish/enricher.py`
- Create: `tests/test_enricher.py`
- Modify: `pyproject.toml` — add `"chonkie"` to dependencies

**Interface:**

```python
MIN_PROMPT_WORDS = 4

def decompose(prompt: str) -> list[str]:
    """Split multi-topic prompt into discrete search queries via Chonkie SentenceChunker."""
    if len(prompt.split()) < MIN_PROMPT_WORDS:
        return []
    from chonkie import SentenceChunker
    chunker = SentenceChunker()
    return [chunk.text for chunk in chunker(prompt)]

def enrich(prompt: str, cwd: str, project: str) -> str:
    """Return context block for injection into Claude's prompt window."""
    chunks = decompose(prompt)
    if not chunks:
        return ""
    results = []
    for chunk in chunks:
        code = subprocess.run(
            ["semble", "search", chunk, cwd],
            capture_output=True, check=False,
        )
        vault_path = str(VAULTS_ROOT / project)
        docs = subprocess.run(
            ["semble", "search", chunk, vault_path, "--content", "docs"],
            capture_output=True, check=False,
        )
        results.append(_format_chunk(chunk, code.stdout.decode(), docs.stdout.decode()))
    return "\n\n".join(results)
```

**`hook.py` change:** For `UserPromptSubmit`, call `enrich()` synchronously and write result to stdout before exiting.

**Tests:**

```python
def test_decompose_returns_empty_for_short_prompt():
    assert decompose("yes") == []
    assert decompose("do that") == []

def test_decompose_splits_multi_topic_prompt():
    chunks = decompose("fix the auth middleware and also the CI tests are broken")
    assert len(chunks) >= 2

def test_enrich_returns_empty_for_short_prompt(tmp_path):
    assert enrich("yes", ".", "myproject") == ""

def test_enrich_calls_semble_per_chunk(tmp_path):
    with patch("goldfish.enricher.subprocess.run") as mock_run:
        mock_run.return_value.stdout = b""
        mock_run.return_value.returncode = 0
        enrich("fix auth middleware and CI tests are broken", "/project", "myproject")
    assert mock_run.call_count >= 2  # at least one per chunk
```

---

## Phase 7 — Async PostToolUse Events

---

### Task 7.1: File edit reindex + git commit checkpoint

**Modify:** `src/goldfish/drain.py` — extend `_route` for `PostToolUse`

```python
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
            cwd = event.get("cwd", ".")
            project = project_name(cwd)
            subprocess.run(["omega", "note", "git_commit", event.get("session_id", "")],
                           capture_output=True, check=False)
```

---

### Task 7.2: SubagentStop, TaskCreated, TaskCompleted

**Modify:** `src/goldfish/drain.py`

These three events write a note to `Tasks/` and flush OMEGA — same pattern as other handlers.

```python
def _handle_task_created(event: dict) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    task_id = event.get("task_id", "unknown")
    write_note(project, f"Tasks/{task_id}.md", _task_frontmatter(event, "created"), "")

def _handle_task_completed(event: dict) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    task_id = event.get("task_id", "unknown")
    fm, body = read_note(project, f"Tasks/{task_id}.md")
    fm["superseded_by"] = None  # stays active, mark completed in body
    write_note(project, f"Tasks/{task_id}.md", fm, body + "\n\n**Completed.**")
```

---

## Phase 8 — Operational Commands

---

### Task 8.1: `goldfish status`

**Modify:** `src/goldfish/cli.py` — implement status command

```python
@app.command()
def status() -> None:
    """Show queue depth and tool health."""
    from goldfish.config import get_manifest, project_name
    import os
    queue = QUEUE_PATH
    depth = len(queue.read_text().splitlines()) if queue.exists() else 0
    project = project_name(os.getcwd())
    manifest = get_manifest(project)
    typer.echo(f"Queue depth:      {depth} events")
    typer.echo(f"Bootstrap:        {'complete' if manifest.get('bootstrap_complete') else 'pending'}")
    typer.echo(f"Semble indexed:   {manifest.get('semble_indexed_at') or 'never'}")
    typer.echo(f"Last JSONL offset: {manifest.get('last_byte_offset', 0)}")
```

---

### Task 8.2: `goldfish doctor`

Checks and prints fix instructions for:
- Node.js present (required for GitNexus): `check_dependency("node")`
- `.gitnexus/` present in cwd
- OMEGA responsive: `subprocess.run(["omega", "status"])`
- Semble index fresh (<1h): compare `manifest.semble_indexed_at` to now
- Queue depth reasonable (<100 events)
- Hooks registered: parse `~/.claude/settings.json`, check for `goldfish hook` entries

---

### Task 8.3: `goldfish replay`

```python
def replay(cwd: str = ".") -> None:
    """Rebuild vault from JSONL transcripts. Resumable from last manifest offset."""
    import re
    encoded = cwd.replace("/", "-")
    jsonl_dir = Path.home() / ".claude" / "projects" / encoded
    project = project_name(cwd)
    manifest = get_manifest(project)
    offset = manifest.get("last_byte_offset", 0)

    for jsonl_file in sorted(jsonl_dir.glob("*.jsonl")):
        with jsonl_file.open() as f:
            f.seek(offset)
            for line in f:
                event = json.loads(line)
                _route(event)
            offset = f.tell()
        write_manifest(project, {**manifest, "last_byte_offset": offset, "last_jsonl_file": jsonl_file.name})
        offset = 0  # reset for next file
```

---

## Self-Review

### Spec Coverage

| PRD Requirement | Task |
|---|---|
| hook.py writes to queue | 1.2 |
| drain.py routes events | 1.3 |
| config.py / manifest | 2.1 |
| vault.py file operations | 2.2 |
| cli.py typer entry point | 3.1 |
| Hook registration in settings.json | 3.2 |
| Init wizard (detect, install, scaffold) | 4.1 |
| Dogfood milestone | 4.2 |
| SessionStart (new + existing) | 5.1 |
| PreCompact snapshot | 5.2 |
| Stop / SessionEnd | 5.3 |
| Chonkie prompt decomposition | 6.1 |
| Fan-out enrichment (Semble + OMEGA) | 6.1 |
| PostToolUse file reindex | 7.1 |
| PostToolUse git commit checkpoint | 7.1 |
| SubagentStop / TaskCreated / TaskCompleted | 7.2 |
| goldfish status | 8.1 |
| goldfish doctor | 8.2 |
| goldfish replay | 8.3 |
| GitNexus: install via npm only, never bundle | 4.1 |
| Hook handlers exit in <10ms | 1.2, 1.3 |
| Obsidian = pathlib.write_text() only | 2.2 |
| init idempotent | 4.1 |
| No search/embedding/graph code | All phases |

### Type Consistency

- `project_name(cwd: str) -> str` — defined in Task 2.1, used in Tasks 5.1, 5.2, 5.3, 6.1, 7.1, 7.2, 8.3
- `is_new_project(project: str, vaults_root: Path) -> bool` — defined in Task 2.1, used in Task 5.1
- `write_note(project, path, frontmatter, body, vaults_root)` — defined in Task 2.2, used in Tasks 5.1, 5.2, 7.2
- `read_note(project, path, vaults_root) -> (dict, str)` — defined in Task 2.2, used in Task 7.2
- `get_manifest / write_manifest` — defined in Task 2.1, used in Tasks 5.1, 5.2, 5.3, 8.3
- `VAULTS_ROOT` — defined in Task 2.1 (config.py), imported in Tasks 6.1, 8.1
- `QUEUE_PATH` — defined in Task 1.3 (drain.py), used in Task 8.1

No conflicts found.
