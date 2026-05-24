# goldfish mine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `goldfish mine` — a CLI command that replays historical Claude Code JSONL session logs through OMEGA's own hook scripts to seed episodic memory, called automatically during `goldfish init` for existing projects.

**Architecture:** `miner.py` discovers OMEGA hook commands from `~/.claude/settings.json`, iterates unprocessed JSONL session files, and pipes each user and assistant message to `fast_hook.py auto_capture` / `fast_hook.py assistant_capture` respectively. Goldfish contributes zero classification logic — OMEGA's hooks handle storage, dedup, and flood protection. Processed session IDs are persisted in `.manifest.toml` under `mined_sessions`.

**Tech Stack:** Python stdlib (`json`, `shlex`, `subprocess`, `pathlib`), existing `goldfish.config` helpers, typer CLI.

---

## File Map

| File | Change |
|------|--------|
| `src/goldfish/config.py` | Add `mined_sessions: []` to `_MANIFEST_DEFAULTS` |
| `src/goldfish/miner.py` | New — five small functions + `mine_project()` |
| `src/goldfish/cli.py` | Add `goldfish mine` command (~20 lines) |
| `src/goldfish/init.py` | Call `mine_project(cwd)` for existing projects |
| `README.md` | Fix stale counts, add `goldfish mine`, add onboarding section |
| `tests/test_config.py` | Two new tests for `mined_sessions` manifest field |
| `tests/test_miner.py` | New — eight tests for `miner.py` |
| `tests/test_init.py` | One new test: mine_project called for existing project |

---

## Background: How OMEGA hooks work

OMEGA registers its own hooks in `~/.claude/settings.json` (separate from goldfish's hooks) via `omega setup --client claude-code`. These entries look like:

```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "/path/to/omega/.../fast_hook.py auto_capture"}]}],
    "Stop":             [{"hooks": [{"type": "command", "command": "/path/to/omega/.../fast_hook.py assistant_capture"}]}]
  }
}
```

`fast_hook.py` reads JSON from stdin and merges it with env vars into a payload, then connects to the OMEGA daemon (UDS socket `~/.omega/hook.sock`). If the daemon is up (as it is during a live Claude Code session), captures go via socket. `assistant_capture` also has a fallback path for when the daemon is not available.

**Correct stdin payload formats:**

- `auto_capture` (user messages): `{"prompt": "<text>", "session_id": "<id>", "cwd": "<path>"}`
- `assistant_capture` (assistant messages): `{"last_assistant_message": "<text>", "session_id": "<id>", "cwd": "<path>"}`

---

## Task 1: config.py — add mined_sessions to manifest defaults

**Files:**
- Modify: `src/goldfish/config.py:9-14`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_config.py`:

```python
def test_get_manifest_default_includes_mined_sessions(tmp_path):
    result = get_manifest("newproject", vaults_root=tmp_path)
    assert result["mined_sessions"] == []


def test_manifest_roundtrip_preserves_mined_sessions(tmp_path):
    data = {
        "mined_sessions": ["session-abc", "session-def"],
        "bootstrap_complete": True,
    }
    write_manifest("myproject", data, vaults_root=tmp_path)
    result = get_manifest("myproject", vaults_root=tmp_path)
    assert result["mined_sessions"] == ["session-abc", "session-def"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v -k "mined_sessions"
```

Expected: FAIL — `KeyError: 'mined_sessions'`

- [ ] **Step 3: Add mined_sessions to _MANIFEST_DEFAULTS**

In `src/goldfish/config.py`, change `_MANIFEST_DEFAULTS` from:

```python
_MANIFEST_DEFAULTS = {
    "last_byte_offset": 0,
    "last_jsonl_file": "",
    "bootstrap_complete": False,
    "semble_indexed_at": "",
}
```

to:

```python
_MANIFEST_DEFAULTS = {
    "last_byte_offset": 0,
    "last_jsonl_file": "",
    "bootstrap_complete": False,
    "semble_indexed_at": "",
    "mined_sessions": [],
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: all PASS (existing tests plus 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add src/goldfish/config.py tests/test_config.py
git commit -m "feat: add mined_sessions to manifest defaults"
```

---

## Task 2: miner.py — core mining logic

**Files:**
- Create: `src/goldfish/miner.py`
- Create: `tests/test_miner.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_miner.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# These imports will fail until miner.py exists — that's the point
from goldfish.miner import (
    _extract_assistant_text,
    _extract_user_text,
    _find_hook_cmd,
    mine_project,
)


def _make_settings(auto_cmd: str, asst_cmd: str) -> dict:
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": auto_cmd}]}],
            "Stop": [{"hooks": [{"type": "command", "command": asst_cmd}]}],
        }
    }


def test_find_hook_cmd_returns_matching_command():
    settings = _make_settings("/python/fast_hook.py auto_capture", "/python/fast_hook.py assistant_capture")
    result = _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture")
    assert result == "/python/fast_hook.py auto_capture"


def test_find_hook_cmd_returns_none_when_not_found():
    settings = {"hooks": {"UserPromptSubmit": [{"hooks": [{"command": "other_tool"}]}]}}
    assert _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture") is None


def test_extract_user_text_returns_string_content():
    obj = {"type": "user", "message": {"content": "hello world"}}
    assert _extract_user_text(obj) == "hello world"


def test_extract_user_text_returns_empty_for_list_content():
    obj = {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}}
    assert _extract_user_text(obj) == ""


def test_extract_assistant_text_joins_text_blocks():
    obj = {
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": "First part."},
            {"type": "tool_use", "name": "Read"},
            {"type": "text", "text": "Second part."},
        ]},
    }
    result = _extract_assistant_text(obj)
    assert "First part." in result
    assert "Second part." in result


def test_extract_assistant_text_returns_empty_for_empty_content():
    obj = {"type": "assistant", "message": {"content": []}}
    assert _extract_assistant_text(obj) == ""


def test_mine_project_returns_zero_when_sessions_dir_missing(tmp_path):
    # tmp_path has no .claude/projects/... subdirectory
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({}))
    n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=tmp_path / "nonexistent")
    assert n == 0


def test_mine_project_processes_user_messages(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "abc123.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "fix the auth middleware"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings(
        "/python fast_hook.py auto_capture",
        "/python fast_hook.py assistant_capture",
    )))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                         _sessions_dir=sessions_dir)

    assert n == 1
    assert mock_pipe.call_count >= 1
    payload = mock_pipe.call_args_list[0][0][1]
    assert payload["prompt"] == "fix the auth middleware"
    assert payload["session_id"] == "abc123"
    assert payload["cwd"] == "/home/tchawes/goldfish"


def test_mine_project_processes_assistant_messages(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "abc123.jsonl").write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "I fixed the auth middleware by updating JWT rotation."}]},
        }) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings(
        "/python fast_hook.py auto_capture",
        "/python fast_hook.py assistant_capture",
    )))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=sessions_dir)

    assert mock_pipe.call_count >= 1
    payload = mock_pipe.call_args_list[0][0][1]
    assert "last_assistant_message" in payload
    assert "JWT rotation" in payload["last_assistant_message"]


def test_mine_project_skips_already_mined_sessions(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "already-done.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "some prompt"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": ["already-done"]}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                         _sessions_dir=sessions_dir)

    assert n == 0
    mock_pipe.assert_not_called()


def test_mine_project_skips_non_message_entries(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    entries = [
        {"type": "ai-title", "title": "Session Title"},
        {"type": "permission-mode", "mode": "default"},
        {"type": "file-history-snapshot", "files": []},
        {"type": "user", "message": {"content": "real prompt"}},
    ]
    (sessions_dir / "sess1.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=sessions_dir)

    assert mock_pipe.call_count == 1  # only the user message


def test_mine_project_updates_manifest_with_session_id(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "sess1.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "prompt"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))
    written = []

    with patch("goldfish.miner._pipe_to_hook"), \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest", side_effect=lambda proj, data, **kw: written.append(data)), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=sessions_dir)

    assert written
    assert "sess1" in written[-1]["mined_sessions"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_miner.py -v
```

Expected: `ModuleNotFoundError: No module named 'goldfish.miner'`

- [ ] **Step 3: Create src/goldfish/miner.py**

```python
import json
import shlex
import subprocess
from pathlib import Path

from goldfish.claude_md import DEFAULT_SETTINGS
from goldfish.config import get_manifest, project_name, write_manifest


def _find_hook_cmd(settings: dict, event: str, script_name: str) -> str | None:
    for group in settings.get("hooks", {}).get(event, []):
        for h in group.get("hooks", []):
            if script_name in h.get("command", ""):
                return h["command"]
    return None


def _extract_user_text(obj: dict) -> str:
    content = obj.get("message", {}).get("content", "")
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
    except Exception:
        pass


def mine_project(
    cwd: str,
    settings_path: Path = DEFAULT_SETTINGS,
    _sessions_dir: Path | None = None,
) -> int:
    """Replay historical JSONL sessions through OMEGA's own hook scripts.

    Returns the number of sessions processed.
    _sessions_dir is injectable for testing; production code computes it from cwd.
    """
    if _sessions_dir is None:
        encoded = Path(cwd).as_posix().replace("/", "-")
        _sessions_dir = Path.home() / ".claude" / "projects" / encoded

    if not _sessions_dir.exists():
        return 0

    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    auto_capture_cmd = _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture")
    assistant_capture_cmd = _find_hook_cmd(settings, "Stop", "assistant_capture")

    project = project_name(cwd)
    manifest = get_manifest(project)
    mined = set(manifest.get("mined_sessions", []))
    processed = 0

    for jsonl_file in sorted(_sessions_dir.glob("*.jsonl")):
        session_id = jsonl_file.stem
        if session_id in mined:
            continue

        for line in jsonl_file.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            if msg_type == "user" and auto_capture_cmd:
                text = _extract_user_text(obj)
                if text:
                    _pipe_to_hook(auto_capture_cmd, {
                        "prompt": text, "session_id": session_id, "cwd": cwd,
                    })
            elif msg_type == "assistant" and assistant_capture_cmd:
                text = _extract_assistant_text(obj)
                if text:
                    _pipe_to_hook(assistant_capture_cmd, {
                        "last_assistant_message": text, "session_id": session_id, "cwd": cwd,
                    })

        mined.add(session_id)
        processed += 1
        write_manifest(project, {**manifest, "mined_sessions": list(mined)})

    return processed
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
uv run pytest tests/test_miner.py tests/test_config.py -v
```

Expected: all PASS

- [ ] **Step 5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all pass (89 existing + new miner/config tests)

- [ ] **Step 6: Commit**

```bash
git add src/goldfish/miner.py tests/test_miner.py
git commit -m "feat: add miner.py — replay JSONL sessions through OMEGA hooks"
```

---

## Task 3: cli.py — goldfish mine command

**Files:**
- Modify: `src/goldfish/cli.py`
- Test: `tests/test_cli.py` (add one test)

- [ ] **Step 1: Write the failing test**

Read `tests/test_cli.py` first. It has `import json`, `from unittest.mock import MagicMock, patch`, and `runner = CliRunner()` at module level — use them. Add at the bottom:

```python
def test_mine_command_reports_no_new_sessions(tmp_path):
    """mine prints 'no new sessions' and exits 0 when mine_project returns 0."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"command": "/python fast_hook.py auto_capture"}]}],
            "Stop": [{"hooks": [{"command": "/python fast_hook.py assistant_capture"}]}],
        }
    }))
    with patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.mine_project", return_value=0) as mock_mine:
        result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "no new sessions" in result.output.lower()
    mock_mine.assert_called_once_with(str(tmp_path))
```

Run: `uv run pytest tests/test_cli.py::test_mine_command_reports_no_new_sessions -v`

Expected: FAIL — `No such command 'mine'`

- [ ] **Step 2: Add the mine command to cli.py**

In `src/goldfish/cli.py`, add the following import at the top (near the other goldfish imports):

```python
from goldfish.miner import mine_project
```

Then add the command (after the `replay` command):

```python
@app.command()
def mine() -> None:
    """Seed OMEGA episodic memory from historical JSONL session logs."""
    import json as _json
    cwd = os.getcwd()
    settings = _json.loads(DEFAULT_SETTINGS.read_text()) if DEFAULT_SETTINGS.exists() else {}
    from goldfish.miner import _find_hook_cmd
    auto_cmd = _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture")
    asst_cmd = _find_hook_cmd(settings, "Stop", "assistant_capture")
    if not auto_cmd and not asst_cmd:
        typer.echo("OMEGA hooks not registered — run: goldfish init")
        raise typer.Exit(1)

    typer.echo(f"Mining sessions from ~/.claude/projects/...")
    n = mine_project(cwd)
    if n == 0:
        typer.echo("No new sessions to mine.")
    else:
        typer.echo(f"Done. {n} session(s) mined into OMEGA memory.")
```

Note: `DEFAULT_SETTINGS` is already imported from `goldfish.config` at the top of cli.py.

- [ ] **Step 3: Run the test to verify it passes**

```bash
uv run pytest tests/test_cli.py::test_mine_command_reports_no_new_sessions -v
```

Expected: PASS

- [ ] **Step 4: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/goldfish/cli.py tests/test_cli.py
git commit -m "feat: add goldfish mine CLI command"
```

---

## Task 4: init.py — call mine_project for existing projects

**Files:**
- Modify: `src/goldfish/init.py`
- Test: `tests/test_init.py` (add one test)

- [ ] **Step 1: Write the failing test**

Add at the bottom of `tests/test_init.py`:

```python
def test_init_calls_mine_project_for_existing_project(tmp_path):
    """On re-run for an existing project, mine_project must be called."""
    from goldfish.config import write_manifest
    project_dir = tmp_path / "goldfish"
    project_dir.mkdir()
    vaults_root = tmp_path / "vaults"
    # Existing project: manifest already written with bootstrap_complete=True
    write_manifest("goldfish", {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": "", "mined_sessions": [],
    }, vaults_root=vaults_root)
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    (project_dir / ".gitnexus").mkdir()

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value="/usr/bin/omega"), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"), \
         patch("goldfish.config.VAULTS_ROOT", vaults_root), \
         patch("goldfish.init.VAULTS_ROOT", vaults_root), \
         patch("goldfish.init.mine_project") as mock_mine:
        mock_run.return_value = MagicMock(returncode=0)
        mock_mine.return_value = 3
        run(cwd=str(project_dir), settings_path=settings, vaults_root=vaults_root)

    mock_mine.assert_called_once_with(str(project_dir))
```

Run: `uv run pytest tests/test_init.py::test_init_calls_mine_project_for_existing_project -v`

Expected: FAIL — `AssertionError: Expected call`

- [ ] **Step 2: Add the mine_project call to init.py**

At the top of `src/goldfish/init.py`, add the import:

```python
from goldfish.miner import mine_project
```

In the `run()` function, find the vault block:

```python
    if is_new_project(project, vaults_root=vaults_root):
        scaffold(project, vaults_root=vaults_root)
        manifest = get_manifest(project, vaults_root=vaults_root)
        manifest["bootstrap_complete"] = True
        write_manifest(project, manifest, vaults_root=vaults_root)
        print(f"✓ Vault scaffolded at {vaults_root / project}")
    else:
        print(f"✓ Vault exists at {vaults_root / project}")
```

Change the `else` branch to:

```python
    else:
        print(f"✓ Vault exists at {vaults_root / project}")
        n = mine_project(cwd)
        if n:
            print(f"✓ Mined {n} historical session(s) into OMEGA memory.")
```

- [ ] **Step 3: Run the test to verify it passes**

```bash
uv run pytest tests/test_init.py::test_init_calls_mine_project_for_existing_project -v
```

Expected: PASS

- [ ] **Step 4: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/goldfish/init.py tests/test_init.py
git commit -m "feat: call mine_project on init for existing projects"
```

---

## Task 5: README.md — update stale info and document goldfish mine

**Files:**
- Modify: `README.md`

No tests for README.

- [ ] **Step 1: Apply all README corrections**

The README currently has several stale entries. Make the following changes (edit each in place):

**a. Fix test count and line count (near bottom of Development section):**

Change:
```
Tests stub all subprocess calls and run without live tool installations. 78 tests, ~0.3s.
```
to:
```
Tests stub all subprocess calls and run without live tool installations. ~100 tests, ~0.3s.
```

**b. Fix Python version prerequisite (in Prerequisites section):**

Change:
```
- Python 3.11+
```
to:
```
- Python 3.13+ (required by chonkie's native dependencies; `uvx` downloads it automatically)
```

**c. Fix Chonkie description (in "How it works" tool table):**

Change:
```
| **Chonkie** | transitive dep of Semble | Splits multi-topic prompts into search queries |
```
to:
```
| **Chonkie** | goldfish dependency | Splits multi-topic prompts into search queries |
```

**d. Remove stale hook table entries (in "Hook lifecycle" section):**

Remove these two rows from the hook table:
```
| `PostToolUse(Write\|Edit)` | Re-indexes changed file with Semble |
| `PostToolUse(Bash git commit*)` | Records commit note in OMEGA |
```

**e. Add `goldfish mine` to Hook lifecycle table:**

The table header/rows cover session events. Add `goldfish mine` usage note after the hook table:

```markdown
Run `goldfish mine` once after setup to seed OMEGA with history from past sessions.
```

**f. Add `goldfish mine` to CLI reference section:**

After `goldfish replay`, add:
```
goldfish mine              Seed OMEGA from historical JSONL session logs (run once on onboarding)
```

**g. Add Onboarding an existing project section:**

After the "Quick start" section and before the horizontal rule, add:

```markdown
### Onboarding an existing project

If you have prior Claude Code sessions in this project, seed OMEGA from them:

```bash
goldfish init          # sets up hooks for future sessions
goldfish mine          # seeds OMEGA from all past sessions (run once, inside a Claude session)
```

`goldfish mine` is also called automatically on subsequent `goldfish init` runs.
```

**h. Add `miner.py` to the Architecture module table:**

After the `enricher.py` row, add:
```
miner.py      replay historical JSONL → pipes user/assistant text to OMEGA's own hooks (auto_capture, assistant_capture)
```

- [ ] **Step 2: Verify README renders correctly**

```bash
# Quick sanity check — make sure no obvious formatting issues
grep -n "goldfish mine" README.md
grep -n "3.13" README.md
grep -n "miner.py" README.md
```

Expected: each grep returns at least one line.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README — goldfish mine, fix stale counts and hook table"
```

---

## Final verification

- [ ] **Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS

- [ ] **Run goldfish doctor**

```bash
uv run goldfish doctor
```

Expected: all checks pass (or same result as before — doctor doesn't check miner)

- [ ] **Smoke test the mine command**

```bash
uv run goldfish mine
```

Expected: reports N sessions mined (or "No new sessions to mine" if already mined).
