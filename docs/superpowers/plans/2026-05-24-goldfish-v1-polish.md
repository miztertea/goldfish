# Goldfish v0.9 → v1.0 Polish Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all dead CLI calls from drain.py, fix the semble vault search flag, add `semble init` sub-agent wiring, update tests to reflect real event field names, and clean up stale documentation so goldfish is fully functional and honest end-to-end.

**Architecture:** Goldfish is a thin orchestration layer (~400–600 line target). Every change here removes fiction: dead subprocess calls to CLIs that don't have those subcommands, tests that assert on those fictional calls, and docs that describe the old design. After this plan, every line of Python either does something real or is gone.

**Tech Stack:** Python 3.11+, uv, pytest, typer, PyYAML, tomli-w, chonkie (new), semble, omega-memory[server], gitnexus

**Key verified facts (from live CLI + fetched docs, 2026-05-24):**
- `semble search` flag for vault/markdown: `--include-text-files` ✓ (NOT `--content docs` — docs site is outdated, flag doesn't exist)
- `semble init` creates `.claude/agents/semble-search.md` sub-agent spec — add to `goldfish init`
- OMEGA dead commands (never existed): `omega flush`, `omega mine`, `omega note`
- OMEGA real CLI: `omega query <text>`, `omega store <content> -t <type>`, `omega setup --download-model`, `omega status`
- GitNexus: 16 MCP tools, hooks coexist with goldfish hooks (no conflict)
- Full tool reference docs: `docs/tools/semble.md`, `docs/tools/omega.md`, `docs/tools/gitnexus.md`

---

## File Map

| File | What changes |
|------|-------------|
| `src/goldfish/enricher.py` | Fix `--content docs` → `--include-text-files` |
| `src/goldfish/drain.py` | Remove 8 dead subprocess calls, 2 no-op handlers, type fallback |
| `src/goldfish/hook.py` | Remove `event.get("type", "")` fallback after tests updated |
| `src/goldfish/init.py` | Fix `_CLAUDE_MD_BLOCK` duplicate sentinel heading |
| `CLAUDE.md` | Fix tool table, remove "codebase doesn't exist", clean triple duplicate block |
| `docs/tools/semble.md` | New — Semble CLI reference (Task 0) |
| `docs/tools/omega.md` | New — OMEGA CLI + MCP reference (Task 0) |
| `docs/tools/gitnexus.md` | New — GitNexus CLI + MCP reference (Task 0) |
| `src/goldfish/init.py` | Add `semble init` sub-agent call; fix `_CLAUDE_MD_BLOCK` duplicate |
| `pyproject.toml` | Add `chonkie` to dependencies |
| `tests/test_hook.py` | Update 6 events from `type` to `hook_event_name` |
| `tests/test_drain.py` | Update event format, remove 7 dead-code tests, rewrite 3 assertions |

---

## Task 0: Write tool reference documentation

**Files:**
- Create: `docs/tools/semble.md` ✅ (already done)
- Create: `docs/tools/omega.md` ✅ (already done)
- Create: `docs/tools/gitnexus.md` ✅ (already done)

These docs were written from live CLI verification (`semble --help`, `semble search --help`, fetched official docs). They are the authoritative source for goldfish contributors — trust them over third-party websites which are outdated.

**Critical corrections discovered during doc research:**

| Assumption | Reality |
|------------|---------|
| `semble search ... --content docs` | Flag does NOT exist. Use `--include-text-files` |
| `omega flush`, `omega mine`, `omega note` | These CLIs do not exist — confirmed dead code |
| `semble` only searches code | `semble init` creates a Claude Code sub-agent config file |
| goldfish needs to trigger OMEGA memory capture | OMEGA's own 7 hooks handle all capture automatically |

- [ ] **Step 1: Verify docs exist**

```bash
ls docs/tools/
```

Expected: `gitnexus.md  omega.md  semble.md`

- [ ] **Step 2: Commit the tool docs**

```bash
cd /home/tchawes/goldfish && git add docs/tools/
git commit -m "$(cat <<'EOF'
docs: add verified tool reference docs for semble, omega, gitnexus

Written from live CLI help output and fetched official documentation.
Key findings: semble --content flag does not exist in installed CLI
(--include-text-files is correct); omega flush/mine/note confirmed absent;
semble init creates Claude Code sub-agent config in project cwd.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 1: Fix enricher.py semble vault search flag

**Files:**
- Modify: `src/goldfish/enricher.py:45`
- Test: `tests/test_enricher.py` (check if it exists, create if not)

The `semble search` CLI does not accept `--content docs`. The correct flag for searching text/markdown files is `--include-text-files`. Without this, vault note searches silently return nothing.

- [ ] **Step 1: Verify the correct semble flag**

```bash
semble search "test query" ~/.goldfish/vaults/goldfish --include-text-files 2>&1 | head -5
```

Expected: results or "no results found" (not an error about unknown flags)

- [ ] **Step 2: Fix the flag in enricher.py**

In `src/goldfish/enricher.py`, change line 45-47 from:
```python
        docs_result = _run(
            ["semble", "search", chunk, vault_path, "--content", "docs"],
            capture_output=True, check=False,
        )
```
to:
```python
        docs_result = _run(
            ["semble", "search", chunk, vault_path, "--include-text-files"],
            capture_output=True, check=False,
        )
```

- [ ] **Step 3: Add chonkie to pyproject.toml dependencies**

In `pyproject.toml`, change line 9 from:
```toml
dependencies = ["tomli-w", "PyYAML", "typer"]
```
to:
```toml
dependencies = ["tomli-w", "PyYAML", "typer", "chonkie"]
```

- [ ] **Step 4: Write a test for the enricher's semble call**

Check if `tests/test_enricher.py` exists:
```bash
ls tests/test_enricher.py 2>/dev/null || echo "does not exist"
```

If it does not exist, create `tests/test_enricher.py`:
```python
from unittest.mock import patch, MagicMock
from goldfish.enricher import enrich, decompose


def test_enrich_vault_search_uses_include_text_files(tmp_path):
    """semble vault search must use --include-text-files, not --content docs."""
    with patch("goldfish.enricher._run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"some result"
        )
        enrich("fix the authentication middleware and refactor JWT", "/project", "myapp")

    calls = [call[0][0] for call in mock_run.call_args_list]
    vault_calls = [c for c in calls if "--include-text-files" in c or "--content" in c]
    assert vault_calls, "semble vault search must be called"
    assert all("--content" not in c for c in vault_calls), "--content flag must not be used"
    assert any("--include-text-files" in c for c in vault_calls), "--include-text-files must be used"


def test_decompose_short_prompt_returns_empty():
    result = decompose("yes")
    assert result == []


def test_decompose_long_prompt_returns_chunks():
    result = decompose("fix the authentication middleware and refactor the JWT rotation policy")
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(c, str) and c.strip() for c in result)


def test_enrich_short_prompt_returns_empty():
    result = enrich("yes", "/project", "myapp")
    assert result == ""


def test_enrich_returns_empty_when_no_results(tmp_path):
    with patch("goldfish.enricher._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"")
        result = enrich("fix auth middleware for JWT rotation", "/project", "myapp")
    assert result == ""
```

- [ ] **Step 5: Run the new tests**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/test_enricher.py -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
cd /home/tchawes/goldfish && git add src/goldfish/enricher.py pyproject.toml tests/test_enricher.py
git commit -m "$(cat <<'EOF'
fix: semble vault search flag and add chonkie dependency

--content docs does not exist; --include-text-files is the correct flag
for searching markdown files. Add chonkie to pyproject.toml so it is
available in goldfish's own tool environment.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Fix CLAUDE.md — tool table, stale text, and duplicate blocks

**Files:**
- Modify: `CLAUDE.md`
- Modify: `src/goldfish/init.py`

CLAUDE.md has three problems:
1. Tool table shows `pip install omega-memory` and `--content docs` (both wrong)
2. Line 14 says "The codebase does not exist yet." (it exists)
3. Lines 156–208: triple-duplicate `## Agent Knowledge Tools` block from a bug in `_CLAUDE_MD_BLOCK`

The root cause of the duplicate block: `_CLAUDE_MD_BLOCK` in `init.py` starts with `{GOLDFISH_SENTINEL}` and then immediately repeats `## Agent Knowledge Tools (managed by goldfish)` as a second heading, causing every `append_claude_md_block` call to double the heading. Two successive `goldfish init` runs created three copies.

- [ ] **Step 1: Fix `_CLAUDE_MD_BLOCK` in init.py**

In `src/goldfish/init.py`, the `_CLAUDE_MD_BLOCK` variable starts at line 24. Change it from:
```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

## Agent Knowledge Tools (managed by goldfish)

### Before any non-trivial task — query all three layers:
```
to (remove the duplicate heading line):
```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

### Before any non-trivial task — query all three layers:
```

- [ ] **Step 2: Fix the tool table in CLAUDE.md**

In `CLAUDE.md` lines 39–44, update the Tool Stack table:
```markdown
## Tool Stack

| Tool | Install | Purpose |
|------|---------|---------|
| GitNexus | `npm install -g gitnexus` → `npx gitnexus analyze` | Code graph, blast radius, hooks, skills — do not replicate |
| OMEGA | `uv tool install "omega-memory[server]"` → `omega setup --download-model && omega setup --client claude-code` | Episodic memory, MCP, SQLite+ONNX, no daemon |
| Semble | `uv tool install semble` | Semantic code search + vault search via `--include-text-files` |
| Chonkie | goldfish dependency | SentenceChunker decomposes multi-topic prompts before fan-out |
```

- [ ] **Step 3: Remove "The codebase does not exist yet." from CLAUDE.md**

In `CLAUDE.md` line 14, change:
```markdown
The codebase does not exist yet. The PRD.md and DESIGN-COMPANION.MD are the complete specification. Build from those.
```
to (remove the line entirely):
```markdown
```
(Just delete that line — the paragraph above still makes sense without it.)

- [ ] **Step 4: Fix the triple-duplicate block in CLAUDE.md**

Lines 156–208 of `CLAUDE.md` contain three copies of `## Agent Knowledge Tools (managed by goldfish)`. Replace everything from line 156 to end-of-file with a single clean copy:
```markdown
## Agent Knowledge Tools (managed by goldfish)

### Before any non-trivial task — query all three layers:

#### Code + Impact Intelligence — GitNexus (MCP)
- `query({query})` — hybrid BM25+semantic search across code graph
- `context({name})` — 360° view of any symbol (callers, callees, processes)
- `impact({target}, direction="upstream")` — blast radius before ANY change
- `detect_changes()` — map staged changes to affected processes pre-commit

#### Episodic Memory — OMEGA (MCP)
- `omega_query("why did we choose JWT")` — past decisions
- `omega_query("rate limiter bug")` — known issues
- `omega_query("Sarah rate limiter")` — person + topic references

#### Semantic Search — Semble (MCP)
- `semble_search(query, path="./src")` — code search by meaning
- `semble_search(query, path="~/.goldfish/vaults/<project>")` — vault notes (markdown indexed automatically)

### Mandatory workflow before refactoring:
1. `gitnexus context({name})` → understand the symbol
2. `gitnexus impact({target})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.
```

- [ ] **Step 5: Verify CLAUDE.md has exactly one goldfish block**

```bash
grep -c "## Agent Knowledge Tools (managed by goldfish)" /home/tchawes/goldfish/CLAUDE.md
```

Expected: `1`

- [ ] **Step 6: Run the claude_md tests**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/test_claude_md.py -v
```

Expected: all pass

- [ ] **Step 6b: Add `semble init` to goldfish init**

`semble init` writes `.claude/agents/semble-search.md` in the project cwd, creating a Claude Code sub-agent for Semble search. Add this call to `init.py`'s `run()` function, after the semble install check:

In `src/goldfish/init.py`, find the Semble install block and add `semble init` after it:
```python
    # Semble — skip if already installed
    if shutil.which("semble"):
        print("✓ Semble already installed")
    else:
        print("  Installing Semble...")
        r = subprocess.run(["uv", "tool", "install", "semble"])
        if r.returncode != 0:
            print("✗ Semble install failed.")
            sys.exit(1)
        print("✓ Semble installed")

    # Semble sub-agent — idempotent (skips if already exists)
    subprocess.run(["semble", "init"], cwd=cwd, capture_output=True)
    print("✓ Semble sub-agent configured")
```

Add a test to `tests/test_init.py`:
```python
def test_init_calls_semble_init(tmp_path):
    """semble init must be called to set up the Claude Code sub-agent."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value="/usr/bin/semble"), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    semble_init_ran = any(
        isinstance(c, list) and "semble" in c and "init" in c
        for c in cmds
    )
    assert semble_init_ran, "semble init must be called to set up Claude Code sub-agent"
```

- [ ] **Step 7: Commit**

```bash
cd /home/tchawes/goldfish && git add CLAUDE.md src/goldfish/init.py tests/test_init.py
git commit -m "$(cat <<'EOF'
fix: remove duplicate CLAUDE.md goldfish block, add semble init

_CLAUDE_MD_BLOCK started with GOLDFISH_SENTINEL then immediately repeated
the heading, causing each goldfish init run to add another copy. Fix the
block, clean up the three existing copies, update the tool table to
reflect uv installs, and add semble init call to wire up the Claude Code
search sub-agent in each project.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Update tests to use hook_event_name field

**Files:**
- Modify: `tests/test_hook.py`
- Modify: `tests/test_drain.py`

Claude Code hook events set `hook_event_name`, not `type`. The tests currently use `{"type": "Stop"}` etc., which only pass because of a fallback. Task 5 removes that fallback; tests must use the real field name first.

**Note:** Tests that call `handle()` directly (which just appends JSON to the queue) do not need updating — `handle()` is format-agnostic. Only tests that call `main_with_event()` or `drain()` need updating, because those functions do routing on `hook_event_name`.

- [ ] **Step 1: Update test_hook.py events**

In `tests/test_hook.py`, update all events that go through `main_with_event()`. Change every `"type"` key to `"hook_event_name"` in these tests:

`test_async_event_appends_to_queue` (line 36):
```python
    event = {"hook_event_name": "Stop", "session_id": "s1", "cwd": "/p"}
```

`test_sync_session_start_writes_stdout_not_queue` (line 45):
```python
    event = {"hook_event_name": "SessionStart", "session_id": "s1", "cwd": "/project/myapp"}
```

`test_sync_pre_compact_calls_handler` (line 57):
```python
    event = {"hook_event_name": "PreCompact", "session_id": "s1", "cwd": "/p"}
```

`test_unknown_event_type_goes_to_queue` (line 68):
```python
    event = {"hook_event_name": "SomeNewEvent", "cwd": "/p"}
```

`test_hook_short_prompt_produces_no_stdout` (line 76):
```python
    event = {"hook_event_name": "UserPromptSubmit", "prompt": "yes", "cwd": "/p", "session_id": "s1"}
```

`test_hook_long_prompt_calls_enrich_and_writes_stdout` (line 85–93):
```python
    event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "fix the authentication middleware and refactor the JWT rotation policy",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
```

Leave `test_hook_appends_event_to_queue`, `test_hook_appends_multiple_events_in_order`, `test_hook_creates_parent_dirs` unchanged — they call `handle()` directly.

- [ ] **Step 2: Update test_drain.py event format — routing tests**

In `tests/test_drain.py`, change every event used in routing/drain tests to use `hook_event_name`:

`test_drain_processes_one_event` (line 21):
```python
    event = {"hook_event_name": "Stop", "cwd": "/home/user/project", "session_id": "s1"}
```

`test_drain_clears_queue_after_processing` (line 33):
```python
    queue.write_text(json.dumps({"hook_event_name": "Stop", "cwd": "."}) + "\n")
```

`test_drain_processes_multiple_events` (lines 42–45):
```python
    events = [
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s1"},
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s2"},
    ]
```

`test_drain_routes_post_tool_use_write_to_semble` (line 54–58):
```python
    event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/my/project/src/auth.py"},
        "cwd": "/my/project",
    }
```

`test_drain_unknown_event_type_does_nothing` (line 71):
```python
    event = {"hook_event_name": "UnknownEvent", "cwd": "/p"}
```

`test_drain_skips_bad_json_and_continues` (line 82):
```python
        json.dumps({"hook_event_name": "Stop", "cwd": "/p"}),
```

`test_session_start_new_project_creates_wake_up` (line 99):
```python
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
```

`test_session_start_new_project_returns_first_session_message` (line 110):
```python
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
```

`test_session_start_existing_project_calls_omega_mine` (line 124):
```python
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s2"}
```

`test_pre_compact_writes_checkpoint_note` (line 136):
```python
    event = {"hook_event_name": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
```

The `_handle_post_tool_use` tests use `{"type": "PostToolUse"}` but call the handler directly (not through drain). Update anyway for consistency:

`test_post_tool_use_edit_calls_semble_reindex` (line 152):
```python
    event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/project/src/main.py"},
        "cwd": "/project",
        "session_id": "s1",
    }
```

`test_post_tool_use_bash_git_commit_calls_omega_note` (line 165):
```python
    event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'fix auth'"},
        "cwd": "/project",
        "session_id": "s1",
    }
```

`test_post_tool_use_bash_non_commit_does_nothing` (line 180):
```python
    event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "cwd": "/project",
        "session_id": "s1",
    }
```

`test_post_tool_use_unknown_tool_does_nothing` (line 193):
```python
    event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "WebFetch",
        "tool_input": {},
        "cwd": "/project",
        "session_id": "s1",
    }
```

`test_task_created_writes_note_to_vault` (line 210):
```python
    event = {
        "hook_event_name": "TaskCreated",
        "task_id": "task-abc",
        "task_description": "Implement auth middleware",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
```

`test_task_completed_appends_completed_marker` (line 239):
```python
    event = {
        "hook_event_name": "TaskCompleted",
        "task_id": "task-abc",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
```

`test_stop_advances_manifest_offset` (line 264–271): update `type` → `hook_event_name` AND `jsonl_file` → `transcript_path`:
```python
    event = {
        "hook_event_name": "Stop",
        "cwd": "/project/myapp",
        "session_id": "s1",
        "transcript_path": str(jsonl_file),
    }
```

`test_drain_budget_zero_processes_all` (line 282):
```python
    events = [{"hook_event_name": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
```

`test_drain_budget_ms_leaves_unprocessed_events` (line 294):
```python
    events = [{"hook_event_name": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
```

`test_session_start_auto_drains_queue` (line 308):
```python
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
```

`test_pre_compact_auto_drains_queue` (line 320):
```python
    event = {"hook_event_name": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
```

`test_semble_indexed_at_written_after_index` (line 387):
```python
    event = {"hook_event_name": "SessionStart", "session_id": "s1", "cwd": str(tmp_path / "myapp")}
```

`test_session_start_excludes_completed_tasks` (line 412):
```python
    event = {"hook_event_name": "SessionStart", "session_id": "s1", "cwd": str(tmp_path / "myapp")}
```

- [ ] **Step 3: Run the full test suite — expect all passing (fallback still present)**

```bash
cd /home/tchawes/goldfish && python -m pytest -x -q
```

Expected: all tests pass (the type fallback in hook.py and drain.py still catches both formats)

- [ ] **Step 4: Commit**

```bash
cd /home/tchawes/goldfish && git add tests/test_hook.py tests/test_drain.py
git commit -m "$(cat <<'EOF'
test: update events to use hook_event_name field

Claude Code hook payloads use hook_event_name, not type. Update all
routing-path tests to use the correct field so they test real behaviour.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Remove dead code from drain.py

**Files:**
- Modify: `src/goldfish/drain.py`

The following subprocess calls reference CLIs that do not have these subcommands:
- `omega flush` (×3) — does not exist
- `omega mine` (×2) — does not exist
- `omega note` (×1) — does not exist
- `semble index` (×1) — does not exist
- `semble reindex` (×2) — does not exist

OMEGA manages its own transcript mining via its own registered hooks (`fast_hook.py`). Goldfish's job is only to call `omega query` at session start for context retrieval. Semble auto-indexes on first search; no explicit indexing call is needed.

After removing all dead calls:
- `_handle_stop_event` → just called `_handle_stop`; inline it
- `_handle_subagent_stop` → only called `omega flush`; becomes empty; remove it
- `_handle_post_tool_use` → both branches (`semble reindex` and `omega note`) are dead; remove it
- `semble_indexed_at` manifest tracking → never meaningfully set; remove it

**The complete replacement for drain.py** (rewrite the whole file cleanly):

- [ ] **Step 1: Replace drain.py with the cleaned version**

Replace the entire content of `src/goldfish/drain.py` with:

```python
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from goldfish.config import VAULTS_ROOT, get_manifest, project_name, write_manifest
from goldfish.vault import read_note, scaffold, write_note

QUEUE_PATH = Path.home() / ".goldfish" / "queue.jsonl"


def _run(cmd: list, **kwargs) -> Optional[subprocess.CompletedProcess]:
    """Run subprocess, returning None if the binary is not found."""
    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        return None


def drain(queue: Path = QUEUE_PATH, budget_ms: float = 0) -> int:
    """Process queued events. budget_ms=0 means no time limit."""
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


def _route(event: dict) -> None:
    handler = _HANDLERS.get(event.get("hook_event_name", ""))
    if handler:
        handler(event)


def _handle_stop(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    jsonl_file_path = event.get("transcript_path", event.get("jsonl_file", ""))
    if jsonl_file_path:
        try:
            cwd = event.get("cwd", ".")
            project = project_name(cwd)
            offset = Path(jsonl_file_path).stat().st_size
            manifest = get_manifest(project, vaults_root=vaults_root)
            write_manifest(
                project,
                {**manifest, "last_byte_offset": offset, "last_jsonl_file": Path(jsonl_file_path).name},
                vaults_root=vaults_root,
            )
        except OSError:
            pass


def _handle_session_end(event: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    cwd = event.get("cwd", ".")
    project = project_name(cwd)
    wake_up = vaults_root / project / "_context" / "wake-up.md"
    if wake_up.exists():
        wake_up.unlink()


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
    drain(budget_ms=200)
    cwd = event.get("cwd", ".")
    session_id = event.get("session_id", "unknown")
    project = project_name(cwd)
    manifest = get_manifest(project, vaults_root=vaults_root)

    if not manifest.get("bootstrap_complete", False):
        scaffold(project, vaults_root=vaults_root)
        body = (
            "# Wake-up — First Session\n\n"
            "This is the first Goldfish session for this project. "
            "Vault scaffolded and ready.\n"
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

    # Existing project — query OMEGA for prior context
    result = _run(
        ["omega", "query", "current project state tasks decisions"],
        capture_output=True,
        check=False,
        text=True,
    )
    memory_context = result.stdout.strip() if result and result.returncode == 0 else ""

    body = "# Wake-up\n\n"
    if memory_context:
        body += f"## Memory Context\n\n{memory_context}\n"
    else:
        body += "No prior memory context found.\n"

    tasks_dir = vaults_root / project / "Tasks"
    open_tasks = []
    if tasks_dir.exists():
        for note_file in sorted(f for f in tasks_dir.iterdir() if f.suffix == ".md")[-10:]:
            note_text = note_file.read_text(encoding="utf-8")
            if "**Completed.**" not in note_text:
                open_tasks.append(note_file.stem)

    decisions_dir = vaults_root / project / "Memory" / "Decisions"
    recent_decisions = []
    if decisions_dir.exists():
        files = sorted(
            (f for f in decisions_dir.iterdir() if f.suffix == ".md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for f in files[:3]:
            lines = f.read_text(encoding="utf-8").splitlines()
            heading = next((l for l in lines if l.startswith("# ")), f.stem)
            recent_decisions.append(heading.lstrip("# "))

    if open_tasks:
        body += "\n## Open Tasks\n\n" + "\n".join(f"- {t}" for t in open_tasks) + "\n"
    if recent_decisions:
        body += "\n## Recent Decisions\n\n" + "\n".join(f"- {d}" for d in recent_decisions) + "\n"

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
    drain(budget_ms=200)
    cwd = event.get("cwd", ".")
    session_id = event.get("session_id", "unknown")
    project = project_name(cwd)

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    frontmatter = {
        "id": f"checkpoint-{session_id}-{ts}",
        "type": "checkpoint",
        "valid_from": _today(),
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
    return datetime.now(UTC).strftime("%Y-%m-%d")


_HANDLERS: dict = {
    "Stop": _handle_stop,
    "SessionEnd": _handle_session_end,
    "TaskCreated": _handle_task_created,
    "TaskCompleted": _handle_task_completed,
}


def main() -> None:
    count = drain()
    print(f"Drained {count} events")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the test suite — expect failures on dead-code tests**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/test_drain.py -v 2>&1 | tail -30
```

Expected: failures on `test_drain_processes_one_event`, `test_drain_processes_multiple_events`, `test_drain_routes_post_tool_use_write_to_semble`, `test_session_start_existing_project_calls_omega_mine`, `test_post_tool_use_*`, `test_semble_indexed_at_written_after_index`. These are all testing removed behaviour. All other tests should pass.

---

## Task 5: Remove dead-code tests and fix assertions for real behaviour

**Files:**
- Modify: `tests/test_drain.py`

After Task 4, several tests assert on behaviour that was deliberately removed. This task deletes those tests and rewrites the ones that asserted on implementation details (subprocess mock counts) rather than observable outputs.

- [ ] **Step 1: Delete the seven tests for removed code**

Remove these complete test functions from `tests/test_drain.py`:
1. `test_drain_routes_post_tool_use_write_to_semble` — `semble reindex` removed
2. `test_session_start_existing_project_calls_omega_mine` — `omega mine` removed
3. `test_post_tool_use_edit_calls_semble_reindex` — handler removed
4. `test_post_tool_use_bash_git_commit_calls_omega_note` — handler removed
5. `test_post_tool_use_bash_non_commit_does_nothing` — handler removed
6. `test_post_tool_use_unknown_tool_does_nothing` — handler removed
7. `test_semble_indexed_at_written_after_index` — semble_indexed_at tracking removed

Also remove these import lines if they become unused:
```python
from goldfish.drain import _handle_post_tool_use
```
(check: `_handle_task_created` and `_handle_task_completed` imports still needed)

- [ ] **Step 2: Rewrite test_drain_processes_one_event**

The old test asserted `cmd[0] == "omega"` which was the (now-removed) `omega flush` call. Replace with:

```python
def test_drain_processes_one_event(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"hook_event_name": "Stop", "cwd": "/home/user/project", "session_id": "s1"}
    queue.write_text(json.dumps(event) + "\n")
    count = drain(queue=queue)
    assert count == 1
    assert queue.read_text().strip() == ""
```

- [ ] **Step 3: Rewrite test_drain_processes_multiple_events**

Remove the `mock_run.call_count` assertion — Stop events make no subprocess calls:

```python
def test_drain_processes_multiple_events(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s1"},
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s2"},
    ]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    count = drain(queue=queue)
    assert count == 2
    assert queue.read_text().strip() == ""
```

- [ ] **Step 4: Fix test_drain_clears_queue_after_processing**

Remove the `patch("goldfish.drain.subprocess.run")` context — Stop makes no subprocess calls:

```python
def test_drain_clears_queue_after_processing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps({"hook_event_name": "Stop", "cwd": "."}) + "\n")
    drain(queue=queue)
    assert queue.read_text() == ""
```

- [ ] **Step 5: Add test_session_start_existing_project_calls_omega_query**

Replace the deleted `omega mine` test with the real behaviour — `omega query` is called:

```python
def test_session_start_existing_project_calls_omega_query(tmp_path):
    from unittest.mock import MagicMock
    from goldfish.config import write_manifest
    write_manifest("myapp", {
        "last_byte_offset": 100, "bootstrap_complete": True,
        "last_jsonl_file": ""
    }, vaults_root=tmp_path)
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s2"}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path), \
         patch("goldfish.drain.drain"):
        mock_run.return_value = MagicMock(returncode=0, stdout="some context")
        handle_session_start(event, vaults_root=tmp_path)
    cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(c[0] == "omega" and "query" in c for c in cmds), "omega query must be called for existing project"
```

- [ ] **Step 6: Run the full test suite — all must pass**

```bash
cd /home/tchawes/goldfish && python -m pytest -x -q
```

Expected: all tests pass, no failures

- [ ] **Step 7: Commit**

```bash
cd /home/tchawes/goldfish && git add src/goldfish/drain.py tests/test_drain.py
git commit -m "$(cat <<'EOF'
refactor: remove dead CLI calls from drain.py and update tests

omega mine, omega flush, omega note, semble index, semble reindex do not
exist as CLI subcommands. OMEGA manages its own transcript mining via its
own registered hooks. Remove all nine dead calls, three no-op handlers,
and the tests that asserted on them. Replace with a test verifying that
omega query is called for existing-project session start.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Remove the type field fallback from routing

**Files:**
- Modify: `src/goldfish/hook.py:29`
- Modify: `src/goldfish/drain.py:50` (in `_route`)

Now that all tests use `hook_event_name`, the `event.get("type", "")` fallback in both routing functions is dead code. Remove it so the code is unambiguous.

- [ ] **Step 1: Remove fallback from hook.py**

In `src/goldfish/hook.py` line 29, change:
```python
    event_type = event.get("hook_event_name", event.get("type", ""))
```
to:
```python
    event_type = event.get("hook_event_name", "")
```

- [ ] **Step 2: Verify drain.py already has clean routing after Task 4**

The new drain.py written in Task 4 already uses:
```python
def _route(event: dict) -> None:
    handler = _HANDLERS.get(event.get("hook_event_name", ""))
```

If the old fallback is still there, change it to `event.get("hook_event_name", "")`.

- [ ] **Step 3: Run the full test suite**

```bash
cd /home/tchawes/goldfish && python -m pytest -x -q
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
cd /home/tchawes/goldfish && git add src/goldfish/hook.py src/goldfish/drain.py
git commit -m "$(cat <<'EOF'
fix: remove type field fallback from event routing

All tests now use hook_event_name. The type fallback was a crutch for
tests written before the correct field name was known. Remove it so
routing is unambiguous and future contributors aren't confused.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Final verification and line count assessment

**Files:** none modified — verification only

- [ ] **Step 1: Run the complete test suite**

```bash
cd /home/tchawes/goldfish && python -m pytest -v 2>&1 | tail -20
```

Expected: all tests pass, zero failures

- [ ] **Step 2: Run goldfish doctor**

```bash
goldfish doctor
```

Expected: `All checks passed.` (or only expected gaps like gitnexus index)

- [ ] **Step 3: Count lines per module**

```bash
wc -l src/goldfish/*.py | sort -n
```

Expected approximate results:
| File | Target | After cleanup |
|------|--------|---------------|
| `__init__.py` | — | 0 |
| `config.py` | — | ~41 |
| `vault.py` | — | ~42 |
| `hook.py` | — | ~55 |
| `enricher.py` | — | ~70 |
| `claude_md.py` | — | ~79 |
| `init.py` | — | ~165 |
| `drain.py` | ~200 after cleanup | ~200 |
| `cli.py` | — | ~240 |
| **Total** | **400–600** | **~890** |

The 400–600 line target from the PRD was aspirational and written before `cli.py` and `enricher.py` were added to the spec. The honest assessment: ~890 lines for a tool that installs four dependencies, manages hooks, enriches prompts, drains an event queue, and maintains a vault is reasonable. No code is superfluous after this cleanup.

- [ ] **Step 4: Verify semble vault search works end-to-end**

```bash
semble search "session start" ~/.goldfish/vaults/goldfish --include-text-files 2>&1 | head -10
```

Expected: results from wake-up.md or checkpoint notes (not an error)

- [ ] **Step 5: Verify omega query works**

```bash
omega query "goldfish session start" 2>&1 | head -5
```

Expected: results or "no results" (not a command-not-found error)

- [ ] **Step 6: Commit summary note to vault**

```bash
omega store "Completed v1.0 polish: removed 9 dead CLI calls from drain.py (omega flush x3, omega mine x2, omega note, semble index, semble reindex x2), fixed semble --include-text-files flag in enricher.py, fixed duplicate CLAUDE.md block, updated all tests to use hook_event_name field. Total lines ~890 (PRD target was 400-600, aspirational)." decision
```

---

## Self-Review

**Spec coverage check:**

| PRD requirement | Covered? |
|-----------------|----------|
| `semble search <query> <path>` is correct CLI form | ✓ Task 1 |
| OMEGA manages its own mining via its own hooks | ✓ Task 4 (removed goldfish's dead omega mine calls) |
| Hook handlers return in <10ms | ✓ unchanged (hook.py untouched except fallback removal) |
| init.py is idempotent | ✓ Task 2 (duplicate block fix prevents CLAUDE.md from growing on re-runs) |
| `hook_event_name` is the correct field name | ✓ Tasks 3, 5, 6 |
| `transcript_path` is the correct Stop event field | ✓ Task 3 (test updated) |
| Vault notes in correct format | ✓ unchanged |
| `omega query` for session context | ✓ Task 4 (preserved, tested in Task 5) |
| chonkie for prompt decomposition | ✓ Task 1 (added to deps) |

**Gaps found:** None beyond the line count aspirational target (documented in Task 7).

**Placeholder scan:** No TBDs, no "implement later", no steps without code. ✓

**Type consistency:** All functions and field names are consistent with existing codebase. ✓
