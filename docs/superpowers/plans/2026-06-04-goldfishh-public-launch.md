# goldfishh Public Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully rebrand the `goldfish` CLI/module to `goldfishh`, update all public-facing metadata and docs, and add a consumer-intent routing rule to the CLAUDE.md coordination block.

**Architecture:** Mechanical Python module rename (`src/goldfish/` → `src/goldfishh/`) plus constant/path updates throughout the source, test, and doc tree. One new behavior: `append_claude_md_block` must detect and remove the old `"managed by goldfish"` sentinel before inserting the new `"managed by goldfishh"` one. All other changes are string substitutions.

**Tech Stack:** Python 3.13, uv, pytest, Typer CLI, GitHub CLI (`gh`)

---

## File Map

| File | Change |
|------|--------|
| `src/goldfish/` → `src/goldfishh/` | Rename entire directory |
| `src/goldfishh/config.py` | `~/.goldfish/` → `~/.goldfishh/` in VAULTS_ROOT + CONFIG_PATH |
| `src/goldfishh/vault.py` | VAULTS_ROOT constant update |
| `src/goldfishh/claude_md.py` | Rename GOLDFISH_SENTINEL constant + value; binary detection `goldfishh`; old-sentinel migration in `append_claude_md_block`; hook detection matches both old and new |
| `src/goldfishh/init.py` | Binary path, vault path, `shutil.which`, print messages, `_PACKAGE_SOURCE`, routing rule + branding in `_CLAUDE_MD_BLOCK`, import of `GOLDFISHH_SENTINEL` |
| `src/goldfishh/cli.py` | Hook detection string, all error messages `run: goldfish` → `run: goldfishh` |
| `pyproject.toml` | packages, script entry, description, readme, keywords, classifiers |
| `tests/test_claude_md.py` | Imports, sentinel constant, binary name assertions, new migration test |
| `tests/test_init.py` | Imports, binary name assertions |
| `tests/test_*.py` (all others) | Import updates only (`goldfish.` → `goldfishh.`) |
| `CLAUDE.md` | CLI references, routing rule, branding |
| `README.md` | h1, quick start, platform badges/section, CLI reference, Python note |
| `AGENTS.md` | CLI references and branding |
| `CONTRIBUTING.md` | CLI references and branding |
| `docs/architecture.md` | `goldfish hook` → `goldfishh hook` |
| `docs/memory-diagnostic.md` | `goldfish doctor` → `goldfishh doctor` |
| `docs/five-failures.md` | Project name references |
| `docs/tool-selection.md` | Project name references |

---

### Task 1: Rename Python module directory

**Files:**
- Rename: `src/goldfish/` → `src/goldfishh/`
- Modify: `pyproject.toml`

- [ ] **Step 1: Rename the source directory**

```bash
git mv src/goldfish src/goldfishh
```

- [ ] **Step 2: Update pyproject.toml packages entry**

In `pyproject.toml`, change:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/goldfish"]
```
to:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/goldfishh"]
```

- [ ] **Step 3: Verify tests fail (imports broken)**

```bash
uv run pytest -x 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'goldfish'`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "refactor: rename src/goldfish → src/goldfishh"
```

---

### Task 2: Fix all Python imports

**Files:**
- Modify: `src/goldfishh/*.py` — all internal imports
- Modify: `tests/*.py` — all test imports

- [ ] **Step 1: Update imports in all source files**

Run this to confirm what needs changing:
```bash
grep -rn "from goldfish\." src/goldfishh/ tests/
```

In every file listed, change `from goldfish.` to `from goldfishh.` and `import goldfish.` to `import goldfishh.`. Also change module-path strings used in `patch()` calls in tests: `"goldfish.xxx"` → `"goldfishh.xxx"`.

Files to update in `src/goldfishh/`:
- `cli.py`: `from goldfish import ...`, `from goldfish.xxx import ...`
- `drain.py`: `from goldfish.xxx import ...`
- `enricher.py`: `from goldfish.xxx import ...`
- `hook.py`: `from goldfish.xxx import ...`
- `init.py`: all `from goldfish.xxx import ...`
- `miner.py`: `from goldfish.xxx import ...`

Files to update in `tests/`:
- Every test file: `from goldfish.xxx import ...` → `from goldfishh.xxx import ...`
- Every `patch("goldfish.xxx.yyy")` → `patch("goldfishh.xxx.yyy")`

- [ ] **Step 2: Run tests to verify they pass**

```bash
uv run pytest -x
```
Expected: all tests pass (or fail only for reasons unrelated to imports)

- [ ] **Step 3: Commit**

```bash
git add src/goldfishh/ tests/
git commit -m "refactor: update all imports goldfish → goldfishh"
```

---

### Task 3: Update binary name, vault/config paths, CLI script entry

**Files:**
- Modify: `src/goldfishh/config.py`
- Modify: `src/goldfishh/vault.py`
- Modify: `src/goldfishh/claude_md.py`
- Modify: `src/goldfishh/init.py`
- Modify: `src/goldfishh/cli.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_claude_md.py`
- Modify: `tests/test_init.py`

- [ ] **Step 1: Update vault/config paths in config.py**

In `src/goldfishh/config.py`, change:
```python
VAULTS_ROOT = Path.home() / ".goldfish" / "vaults"
CONFIG_PATH = Path.home() / ".goldfish" / "config.toml"
```
to:
```python
VAULTS_ROOT = Path.home() / ".goldfishh" / "vaults"
CONFIG_PATH = Path.home() / ".goldfishh" / "config.toml"
```

- [ ] **Step 2: Update vault.py path constant**

In `src/goldfishh/vault.py`, change:
```python
VAULTS_ROOT = Path.home() / ".goldfish" / "vaults"
```
to:
```python
VAULTS_ROOT = Path.home() / ".goldfishh" / "vaults"
```

- [ ] **Step 3: Update binary detection in claude_md.py**

In `src/goldfishh/claude_md.py`, change `_detect_goldfish_bin()`:
```python
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
```

Also update `_is_goldfish_hook` to match the renamed binary (the old-sentinel migration that strips `"goldfish hook"` entries is handled in Task 4):
```python
def _is_goldfish_hook(h: object) -> bool:
    if not isinstance(h, dict):
        return False
    cmd = h.get("command", "")
    return isinstance(cmd, str) and ("goldfishh" in cmd or "goldfish" in cmd) and cmd.endswith(" hook")
```

(The `"goldfish" in cmd` clause ensures stale old-binary hook entries are also removed on re-registration.)

- [ ] **Step 4: Update init.py binary path + print messages**

In `src/goldfishh/init.py`, change:
```python
def _goldfish_stable_path() -> Path:
    return Path.home() / ".local" / "bin" / "goldfish"
```
to:
```python
def _goldfish_stable_path() -> Path:
    return Path.home() / ".local" / "bin" / "goldfishh"
```

Change `run()`:
```python
    if stable.exists():
        print("✓ goldfishh installed (stable path)")
    elif shutil.which("goldfishh"):
        print("✓ goldfishh installed (found on PATH)")
    else:
        r = subprocess.run(["uv", "tool", "install", "goldfishh"])
        if r.returncode != 0:
            print("  note: goldfishh self-install failed; hook path may be unstable")
        else:
            print("✓ goldfishh installed at ~/.local/bin/goldfishh")
```

Also change the `shutil.which` call in the `elif` branch from `"goldfish"` to `"goldfishh"`.

Change the final print:
```python
    print("\n✓ goldfishh is ready.")
```

Update `_PACKAGE_SOURCE` (no longer needs git URL since it's on PyPI):
```python
_PACKAGE_SOURCE = "goldfishh"
```

- [ ] **Step 5: Update cli.py hook detection and error messages**

In `src/goldfishh/cli.py`, change line ~104-119:
```python
            has_goldfish = any(
                "goldfishh" in str(h) and "hook" in str(h)
                for group in hooks.values()
                for block in group
                for h in block.get("hooks", [])
            )
            if has_goldfish:
                typer.echo("✓ Hooks registered")
            else:
                typer.echo("✗ Hooks not registered — run: goldfishh init")
```

Change all other `"run: goldfish ..."` messages in `cli.py` to `"run: goldfishh ..."`:
- `"run: goldfishh init"` (appears several times)
- `"run: goldfishh drain"`

- [ ] **Step 6: Update pyproject.toml script entry**

In `pyproject.toml`, change:
```toml
[project.scripts]
goldfish = "goldfish.cli:app"
```
to:
```toml
[project.scripts]
goldfishh = "goldfishh.cli:app"
```

- [ ] **Step 7: Update tests for binary name**

In `tests/test_claude_md.py`:
- Line 52: `fake_goldfish = fake_venv_bin / "goldfish"` → `fake_goldfishh = fake_venv_bin / "goldfishh"` (rename variable throughout that test)
- Line 53: `fake_goldfish.touch()` → `fake_goldfishh.touch()`
- Line 69: `assert str(fake_goldfish) in command` → `assert str(fake_goldfishh) in command`
- Line 74 docstring: `"goldfish hook"` → `"goldfishh hook"`
- Line 77: old `"goldfish hook"` entry is now the OLD-format case being migrated (keep as-is for the migration test in Task 4, but the idempotency test at line 25 needs `"goldfishh" in str(h)`)
- Line 25: `[h for h in stop_hooks[0]["hooks"] if "goldfish" in str(h)]` → `if "goldfishh" in str(h)`
- Line 81: `(fake_venv_bin / "goldfish").touch()` → `(fake_venv_bin / "goldfishh").touch()`
- Line 90-92: update assertions to check for `"goldfishh hook"` and `"goldfishh"` in the command
- Line 135: `assert any("goldfish" in h.get("command", "")` → `"goldfishh"`
- Line 190: `local_bin = tmp_path / ".local" / "bin" / "goldfish"` → `"goldfishh"`
- Line 194: update `_detect_goldfish_bin` import from `goldfishh.claude_md`

In `tests/test_init.py`: update any binary path references similarly.

- [ ] **Step 8: Run tests**

```bash
uv run pytest tests/test_claude_md.py tests/test_init.py -v
```
Expected: all pass

- [ ] **Step 9: Run full suite**

```bash
uv run pytest
```
Expected: all pass

- [ ] **Step 10: Commit**

```bash
git add src/goldfishh/ tests/ pyproject.toml
git commit -m "refactor: rename binary goldfishh, update vault path ~/.goldfishh"
```

---

### Task 4: GOLDFISHH_SENTINEL rename + old-sentinel migration

**Files:**
- Modify: `src/goldfishh/claude_md.py`
- Modify: `src/goldfishh/init.py`
- Modify: `tests/test_claude_md.py`

- [ ] **Step 1: Write the failing test for old-sentinel migration**

Add to `tests/test_claude_md.py`:
```python
def test_append_claude_md_block_migrates_old_sentinel(tmp_path):
    """Re-init on a project with old 'managed by goldfish' block must replace it."""
    claude_md = tmp_path / "CLAUDE.md"
    old_sentinel = "## Agent Knowledge Tools (managed by goldfish)"
    claude_md.write_text("# Project\n\n" + old_sentinel + "\n\nOLD CONTENT\n")

    from goldfishh.claude_md import GOLDFISHH_SENTINEL, append_claude_md_block
    new_block = GOLDFISHH_SENTINEL + "\n\nNEW CONTENT\n"
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert old_sentinel not in content
    assert GOLDFISHH_SENTINEL in content
    assert "NEW CONTENT" in content
    assert "OLD CONTENT" not in content
    assert content.count(GOLDFISHH_SENTINEL) == 1
```

- [ ] **Step 2: Run to confirm it fails**

```bash
uv run pytest tests/test_claude_md.py::test_append_claude_md_block_migrates_old_sentinel -v
```
Expected: FAIL — `ImportError` or `AssertionError`

- [ ] **Step 3: Rename sentinel constant and update append_claude_md_block**

In `src/goldfishh/claude_md.py`:

Change the sentinel constant:
```python
_OLD_GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"
GOLDFISHH_SENTINEL = "## Agent Knowledge Tools (managed by goldfishh)"
```

Update `append_claude_md_block` to handle migration:
```python
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
    # Update in-place
    start = existing.index(GOLDFISHH_SENTINEL)
    after = existing[start + len(GOLDFISHH_SENTINEL):]
    m = re.search(r"\n##\s", after)
    if m:
        end = start + len(GOLDFISHH_SENTINEL) + m.start()
        claude_md_path.write_text(existing[:start] + block + "\n" + existing[end:], encoding="utf-8")
    else:
        claude_md_path.write_text(existing[:start] + block + "\n", encoding="utf-8")
```

- [ ] **Step 4: Update all sentinel references in claude_md.py**

Replace remaining `GOLDFISH_SENTINEL` usages with `GOLDFISHH_SENTINEL`. The constant `GOLDFISH_SENTINEL` is removed; `GOLDFISHH_SENTINEL` is the public name.

- [ ] **Step 5: Update init.py sentinel import**

In `src/goldfishh/init.py`, change:
```python
from goldfishh.claude_md import GOLDFISH_SENTINEL, append_claude_md_block, register_hooks
```
to:
```python
from goldfishh.claude_md import GOLDFISHH_SENTINEL, append_claude_md_block, register_hooks
```

Update `_CLAUDE_MD_BLOCK` f-string:
```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISHH_SENTINEL}
...
```

- [ ] **Step 6: Update test_claude_md.py sentinel references**

In `tests/test_claude_md.py`:
- Line 6: `GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"` → `GOLDFISHH_SENTINEL = "## Agent Knowledge Tools (managed by goldfishh)"`
- All uses of `GOLDFISH_SENTINEL` in tests → `GOLDFISHH_SENTINEL`
- `test_register_hooks_updates_bare_command_to_full_path`: the initial settings still use `"goldfish hook"` (old format) — this now tests migration of stale hooks
- Line 135 assertion: `"goldfishh"` instead of `"goldfish"`

- [ ] **Step 7: Run the migration test**

```bash
uv run pytest tests/test_claude_md.py::test_append_claude_md_block_migrates_old_sentinel -v
```
Expected: PASS

- [ ] **Step 8: Run full test suite**

```bash
uv run pytest
```
Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add src/goldfishh/claude_md.py src/goldfishh/init.py tests/test_claude_md.py
git commit -m "feat: rename GOLDFISHH_SENTINEL, add old-sentinel migration in append_claude_md_block"
```

---

### Task 5: Update `_CLAUDE_MD_BLOCK` routing rule + branding, sync CLAUDE.md

**Files:**
- Modify: `src/goldfishh/init.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update _CLAUDE_MD_BLOCK in init.py**

In `src/goldfishh/init.py`, in the `_CLAUDE_MD_BLOCK` string:

Change the opening line:
```
goldfish coordinates four layers of agent intelligence. All four are available from session start.
```
to:
```
goldfishh coordinates four layers of agent intelligence. All four are available from session start.
```

Change Layer 2 row in the table:
```
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
```
to:
```
| Layer 2 — Goldfishh | This coordination block — session sequence, layer routing | Always present |
```

Change the routing rule text from:
```
Vault = consumer is human (Obsidian-readable narrative, long-form). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read this note. Architectural decisions may warrant both; session facts warrant OMEGA only. Goldfish hooks automatically write vault notes for task events and session checkpoints — architectural summaries require explicit agent writes.
```
to:
```
Vault = consumer is human (Obsidian-readable narrative, long-form). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read this later (narrative, rationale, context for future contributors); OMEGA only when the consumer is the agent (facts, decisions, lessons). Session facts: OMEGA only. Goldfishh hooks automatically write vault notes for task events and session checkpoints — architectural summaries require explicit agent writes.
```

- [ ] **Step 2: Sync the same changes to CLAUDE.md**

In `CLAUDE.md`, find the Layer 2 block. It starts with an HTML comment `<!-- layer 2: goldfish — do not edit, maintained by goldfish init -->` — update that comment to `goldfishh` too. Then apply the identical changes to the heading and body:
- `"managed by goldfish"` → `"managed by goldfishh"` in the sentinel line
- `goldfish coordinates` → `goldfishh coordinates`
- `Layer 2 — Goldfish` → `Layer 2 — Goldfishh`
- Replace the routing rule paragraph with the new consumer-intent text (same as Step 1)

- [ ] **Step 3: Run tests (no logic changed, verifying nothing broken)**

```bash
uv run pytest
```
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add src/goldfishh/init.py CLAUDE.md
git commit -m "feat: consumer-intent routing rule, goldfishh branding in CLAUDE.md block"
```

---

### Task 6: pyproject.toml metadata for PyPI

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add description, readme, keywords, and classifiers**

In `pyproject.toml`, update the `[project]` section to:
```toml
[project]
name = "goldfishh"
dynamic = ["version"]
description = "Persistent memory for Claude Code — installs and wires GitNexus, OMEGA, and Semble"
readme = "README.md"
requires-python = "==3.13.*"
keywords = ["claude-code", "ai-memory", "llm-agent", "gitnexus", "omega"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.13",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
    "Topic :: Software Development",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = ["tomli-w", "PyYAML", "typer", "chonkie"]
```

- [ ] **Step 2: Verify package builds**

```bash
uv build
```
Expected: creates `dist/goldfishh-*.whl` and `dist/goldfishh-*.tar.gz` without errors

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add PyPI metadata — description, readme, keywords, classifiers"
```

---

### Task 7: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace h1 and badge section**

Replace the top of `README.md` (lines 1–17) with:
```html
<p align="center">
  <img src="assets/goldfish-logo.png" alt="goldfishh — persistent memory for Claude Code" width="280">
</p>

<h1 align="center">goldfishh</h1>

<p align="center">
  <strong>Persistent memory for Claude Code agents.</strong><br>
  One command installs and wires together GitNexus, OMEGA, and Semble so your AI agent<br>
  never starts a session from scratch again.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.13-blue.svg" alt="Python 3.13">
  <img src="https://img.shields.io/badge/platform-linux%20%7C%20macos-lightgrey.svg" alt="Platform: Linux | macOS">
  <img src="https://img.shields.io/badge/windows-beta-orange.svg" alt="Windows: beta">
  <a href="https://pypi.org/project/goldfishh/"><img src="https://img.shields.io/pypi/v/goldfishh.svg" alt="PyPI"></a>
</p>
```

- [ ] **Step 2: Replace Quick start section**

Replace the Quick start section with:
```markdown
## Quick start

**Prerequisites:** Python 3.13 (pinned — see note below), Node.js 18+, [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

```bash
uvx goldfishh init
```

Or install as a persistent tool:

```bash
uv tool install goldfishh
goldfishh init
```

> **Python 3.13 required.** `goldfishh` pins to Python 3.13 because `chonkie` (a required dependency) is incompatible with Python 3.14. `uvx` and `uv tool install` both respect this constraint automatically.

The init wizard detects and installs all dependencies, indexes your codebase, scaffolds your memory vault, and registers Claude Code hooks. Re-running is safe — it reports health and skips what's already installed.

If you have prior Claude Code sessions in this project, seed OMEGA with their history:

```bash
goldfishh mine
```
```

- [ ] **Step 3: Replace Platform support section**

Replace:
```markdown
## Platform support

Tested on a clean install of **Ubuntu 26.04 LTS**. Expected to work on other Linux distributions and macOS — not yet verified. Windows is out of scope for v1.
```
with:
```markdown
## Platform support

**Linux + macOS** (primary): tested on Ubuntu 26.04 LTS; macOS expected to work.  
**Windows** (beta): CI passes on Windows; clean-install verification pending.
```

- [ ] **Step 4: Update CLI reference section**

Replace all `goldfish <cmd>` with `goldfishh <cmd>`:
```
goldfishh init              Run the setup wizard
goldfishh mine              Seed OMEGA from historical JSONL session logs (run once on onboarding)
goldfishh status            Show queue depth, manifest state, and sync timestamps
goldfishh doctor            Check all dependencies and report with fix instructions
goldfishh register-hooks    Re-register hooks with the correct binary path
goldfishh replay            Rebuild vault from JSONL transcripts (resumable)
goldfishh hook              Handle a hook event from stdin (called by Claude Code)
goldfishh drain             Process queued events from ~/.goldfishh/queue.jsonl
```

- [ ] **Step 5: Update Development section**

```markdown
## Development

```bash
git clone https://github.com/miztertea/goldfish
cd goldfish
uv sync
uv run pytest
```

Tests stub all subprocess calls and run without live tool installations. ~100 tests, ~0.3s.

```bash
uv run pytest -v          # verbose test output
uv run goldfishh --help   # run CLI from source
```
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: update README — goldfishh branding, uvx install, platform support"
```

---

### Task 8: Update remaining docs + AGENTS.md + CONTRIBUTING.md

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/memory-diagnostic.md`
- Modify: `docs/five-failures.md`
- Modify: `docs/tool-selection.md`
- Modify: `AGENTS.md`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Update docs/architecture.md**

Find all occurrences of `goldfish hook` (in the hook lifecycle diagrams) and replace with `goldfishh hook`. Also update any `goldfish ` (with trailing space, as a command) to `goldfishh `. The project name "goldfish" in prose descriptions becomes "goldfishh".

Confirm changes:
```bash
grep -n "goldfish" docs/architecture.md
```
Expected after update: no bare `goldfish` references (only `goldfishh`)

- [ ] **Step 2: Update docs/memory-diagnostic.md**

Replace `goldfish doctor` with `goldfishh doctor`. Replace any other `goldfish` CLI references.

- [ ] **Step 3: Update docs/five-failures.md and docs/tool-selection.md**

Replace project name references: `goldfish` → `goldfishh` where referring to the tool name.

- [ ] **Step 4: Update AGENTS.md and CONTRIBUTING.md**

Replace all `goldfish <cmd>` references with `goldfishh <cmd>`. Replace project name branding.

- [ ] **Step 5: Verify no stale goldfish CLI references remain**

```bash
grep -rn "\bgoldfish\b" docs/ AGENTS.md CONTRIBUTING.md | grep -v "goldfishh\|miztertea/goldfish\|goldfish-logo\|goldfish\.png"
```
Expected: no output (all replaced)

- [ ] **Step 6: Commit**

```bash
git add docs/ AGENTS.md CONTRIBUTING.md
git commit -m "docs: goldfishh branding in all docs, AGENTS.md, CONTRIBUTING.md"
```

---

### Task 9: GitHub repository description and topics

**Files:** GitHub repo metadata (no code files)

- [ ] **Step 1: Update repo description and topics**

```bash
gh repo edit miztertea/goldfish \
  --description "Persistent memory for Claude Code — one command installs GitNexus, OMEGA, and Semble" \
  --add-topic claude-code \
  --add-topic ai-memory \
  --add-topic llm-agent \
  --add-topic python \
  --add-topic developer-tools
```
Expected: no error output

- [ ] **Step 2: Verify**

```bash
gh repo view miztertea/goldfish --json description,repositoryTopics
```
Expected: description and topics updated

---

### Task 10: Final verification + PR

**Files:** none

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v
```
Expected: all ~100 tests pass, ~0.3s

- [ ] **Step 2: Verify CLI entry point**

```bash
uv run goldfishh --help
```
Expected: CLI help text shown with `goldfishh` as the command name

- [ ] **Step 3: Verify package build**

```bash
uv build && ls dist/
```
Expected: `goldfishh-*.whl` and `goldfishh-*.tar.gz` present

- [ ] **Step 4: Create PR**

Use the `superpowers:finishing-a-development-branch` skill or create PR directly:
```bash
gh pr create \
  --title "feat: full goldfishh rebrand — CLI rename, PyPI metadata, public docs" \
  --body "Full rebrand from goldfish → goldfishh CLI command, vault path ~/.goldfishh, Python module src/goldfishh. PyPI page now has description and README. Consumer-intent routing rule in CLAUDE.md block. Old-sentinel migration so re-init doesn't create duplicate CLAUDE.md blocks."
```
