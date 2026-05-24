# Goldfish Polish & Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all remaining gaps in Goldfish: failing test, doctor MCP mismatch, omega model download, datetime deprecation, cosmetic cleanup, and a full README rewrite.

**Architecture:** Six small, independent patches across 5 files. No new modules. Every fix maps to a concrete observed failure.

**Tech Stack:** Python 3.11+, pytest, uv, omega-memory CLI

---

## Identified Gaps

| # | Gap | File | Impact |
|---|-----|------|--------|
| 1 | `test_register_hooks_uses_venv_bin_path` missing `Path.home` patch | `tests/test_claude_md.py` | Test suite fails |
| 2 | Doctor checks `"omega"` but MCP key is `"omega-memory"` | `src/goldfish/cli.py` | Doctor reports false failure |
| 3 | Init doesn't run `omega setup --download-model` before `--client` | `src/goldfish/init.py` | First-run breaks without model |
| 4 | `datetime.utcnow()` deprecated in drain.py | `src/goldfish/drain.py` | Runtime warnings |
| 5 | Obsidian reference in init success message | `src/goldfish/init.py` | Misleading UX |
| 6 | README: pip reference, outdated content, no alignment with spec | `README.md` | Wrong install instructions |

---

## File Map

- **Modify** `tests/test_claude_md.py:47-69` — add `Path.home` patch to one test
- **Modify** `src/goldfish/cli.py:137` — change MCP name check from `"omega"` to `"omega-memory"`
- **Modify** `src/goldfish/init.py:130-148` — add `omega setup --download-model` step; remove Obsidian line
- **Modify** `src/goldfish/drain.py:277,299` — replace `datetime.utcnow()` with `datetime.now(UTC)`
- **Rewrite** `README.md` — full rewrite against PRD/CLAUDE.md spec

---

## Task 1: Fix failing test — add Path.home patch

**Files:**
- Modify: `tests/test_claude_md.py:47-69`

**Context:** `_detect_goldfish_bin()` first checks `Path.home() / ".local" / "bin" / "goldfish"`. Since `~/.local/bin/goldfish` actually exists in the test environment, the stable path is found before reaching the venv sibling check. The test patches `shutil.which` and `sys.executable` but not `Path.home`, so the real home directory leaks in.

- [ ] **Step 1: Open tests/test_claude_md.py and find the failing test**

  `tests/test_claude_md.py:47-69` — `test_register_hooks_uses_venv_bin_path`

- [ ] **Step 2: Add `Path.home` patch**

  Replace the `with` block in `test_register_hooks_uses_venv_bin_path`:

  ```python
  def test_register_hooks_uses_venv_bin_path(tmp_path):
      """When goldfish binary is found next to sys.executable, that full path is used."""
      settings = tmp_path / "settings.json"
      settings.write_text(json.dumps({}))

      fake_venv_bin = tmp_path / "bin"
      fake_venv_bin.mkdir()
      fake_goldfish = fake_venv_bin / "goldfish"
      fake_goldfish.touch()

      fake_executable = str(fake_venv_bin / "python")

      # shutil.which returns None → fall back to venv sibling
      with patch("goldfish.claude_md.shutil.which", return_value=None), \
           patch("goldfish.claude_md.sys.executable", fake_executable), \
           patch("goldfish.claude_md.Path.home", return_value=tmp_path):
          register_hooks(settings_path=settings)

      data = json.loads(settings.read_text())
      stop_hooks = data["hooks"]["Stop"][0]["hooks"]
      assert len(stop_hooks) == 1
      command = stop_hooks[0]["command"]
      assert str(fake_goldfish) in command
      assert command.endswith(" hook")
  ```

- [ ] **Step 3: Run the specific test to verify it passes**

  ```bash
  cd /home/tchawes/goldfish && uv run pytest tests/test_claude_md.py::test_register_hooks_uses_venv_bin_path -v
  ```

  Expected: `PASSED`

- [ ] **Step 4: Run full test suite**

  ```bash
  cd /home/tchawes/goldfish && uv run pytest -q
  ```

  Expected: All tests pass, 0 failed.

- [ ] **Step 5: Commit**

  ```bash
  git add tests/test_claude_md.py
  git commit -m "fix: add Path.home patch to venv bin path test"
  ```

---

## Task 2: Fix doctor MCP name mismatch

**Files:**
- Modify: `src/goldfish/cli.py:137`

**Context:** `omega setup --client claude-code` registers the MCP server as `"omega-memory"` in `~/.claude.json`. The doctor currently iterates `("omega", "semble", "gitnexus")` — so it always reports `omega` as unregistered even when it's working.

- [ ] **Step 1: Update the MCP names tuple in doctor**

  In `src/goldfish/cli.py`, find:
  ```python
  for name in ("omega", "semble", "gitnexus"):
  ```

  Replace with:
  ```python
  for name in ("omega-memory", "semble", "gitnexus"):
  ```

- [ ] **Step 2: Run doctor to verify it no longer reports false failure**

  ```bash
  cd /home/tchawes/goldfish && uv run goldfish doctor
  ```

  Expected: `✓ omega-memory MCP` (not a failure) when omega is registered.

- [ ] **Step 3: Run test suite to confirm no regressions**

  ```bash
  cd /home/tchawes/goldfish && uv run pytest -q
  ```

  Expected: All pass.

- [ ] **Step 4: Commit**

  ```bash
  git add src/goldfish/cli.py
  git commit -m "fix: correct omega MCP key name to omega-memory in doctor"
  ```

---

## Task 3: Add omega model download to init + remove Obsidian reference

**Files:**
- Modify: `src/goldfish/init.py:130-165`

**Context:** When omega-memory is first installed, the embedding model is not downloaded by default. `omega setup --client claude-code` registers the MCP but fails silently if the model isn't present. The user had to run `omega setup --download-model` manually. Fix: run both flags in the correct order — model first, then client registration. Also remove the Obsidian reference from the success message (Obsidian is optional, not integrated).

- [ ] **Step 1: Update the MCP registration block in init.py**

  Find the MCP registration block (approximately lines 129–148):

  ```python
  # MCP registration — each tool registers its own MCP via its own CLI
  manifest = get_manifest(project, vaults_root=vaults_root)
  if not manifest.get("mcp_registered"):
      print("  Registering MCP servers...")
      try:
          subprocess.run(["npx", "gitnexus", "setup"], cwd=cwd)
      except FileNotFoundError:
          print("  note: gitnexus setup not available; skipping")
      try:
          subprocess.run(["omega", "setup", "--client", "claude-code"])
      except FileNotFoundError:
          print("  note: omega setup not available; skipping")
      try:
          subprocess.run([
              "claude", "mcp", "add", "semble", "-s", "user",
              "--", "uvx", "--from", "semble[mcp]", "semble"
          ])
      except FileNotFoundError:
          print("  note: claude CLI not available; skipping semble MCP registration")
      manifest["mcp_registered"] = True
      write_manifest(project, manifest, vaults_root=vaults_root)
      print("✓ MCPs registered (GitNexus, OMEGA, Semble)")
  else:
      print("✓ MCPs already registered")
  ```

  Replace the omega setup call with the two-step version:

  ```python
  # MCP registration — each tool registers its own MCP via its own CLI
  manifest = get_manifest(project, vaults_root=vaults_root)
  if not manifest.get("mcp_registered"):
      print("  Registering MCP servers...")
      try:
          subprocess.run(["npx", "gitnexus", "setup"], cwd=cwd)
      except FileNotFoundError:
          print("  note: gitnexus setup not available; skipping")
      try:
          print("  Downloading OMEGA embedding model (~127 MB, one-time)...")
          subprocess.run(["omega", "setup", "--download-model"])
          subprocess.run(["omega", "setup", "--client", "claude-code"])
      except FileNotFoundError:
          print("  note: omega setup not available; skipping")
      try:
          subprocess.run([
              "claude", "mcp", "add", "semble", "-s", "user",
              "--", "uvx", "--from", "semble[mcp]", "semble"
          ])
      except FileNotFoundError:
          print("  note: claude CLI not available; skipping semble MCP registration")
      manifest["mcp_registered"] = True
      write_manifest(project, manifest, vaults_root=vaults_root)
      print("✓ MCPs registered (GitNexus, OMEGA, Semble)")
  else:
      print("✓ MCPs already registered")
  ```

- [ ] **Step 2: Remove the Obsidian reference from the final print block**

  Find (approximately line 163–165):
  ```python
  print(f"\n✓ goldfish is ready.")
  print(f"  Vault:    {vaults_root / project}")
  print(f"  Obsidian: open {vaults_root / project} as a vault (optional, no plugins needed)")
  ```

  Replace with:
  ```python
  print(f"\n✓ goldfish is ready.")
  print(f"  Vault: {vaults_root / project}")
  ```

- [ ] **Step 3: Run test suite to confirm no regressions**

  ```bash
  cd /home/tchawes/goldfish && uv run pytest -q
  ```

  Expected: All pass.

- [ ] **Step 4: Commit**

  ```bash
  git add src/goldfish/init.py
  git commit -m "fix: run omega setup --download-model before client registration; remove Obsidian ref"
  ```

---

## Task 4: Fix datetime.utcnow() deprecation in drain.py

**Files:**
- Modify: `src/goldfish/drain.py:277,299`

**Context:** `datetime.utcnow()` is deprecated in Python 3.12+. The code already imports `UTC` from `datetime` but only uses it in one place. Fix the two remaining uses.

- [ ] **Step 1: Fix handle_pre_compact timestamp**

  In `src/goldfish/drain.py`, find line ~277:
  ```python
  ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
  ```

  Replace with:
  ```python
  ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
  ```

- [ ] **Step 2: Fix _today() helper**

  Find line ~299:
  ```python
  def _today() -> str:
      return datetime.utcnow().strftime("%Y-%m-%d")
  ```

  Replace with:
  ```python
  def _today() -> str:
      return datetime.now(UTC).strftime("%Y-%m-%d")
  ```

- [ ] **Step 3: Run test suite to confirm no regressions and no warnings**

  ```bash
  cd /home/tchawes/goldfish && uv run pytest -q -W error::DeprecationWarning 2>&1 | grep -E "(FAILED|WARNING|passed|error)" | head -20
  ```

  Expected: All pass, no DeprecationWarning from drain.py.

- [ ] **Step 4: Commit**

  ```bash
  git add src/goldfish/drain.py
  git commit -m "fix: replace deprecated datetime.utcnow() with datetime.now(UTC)"
  ```

---

## Task 5: Rewrite README.md

**Files:**
- Rewrite: `README.md`

**Context:** Current README mentions `pip install omega-memory` (should be `uv tool install omega-memory`), describes Obsidian as if integrated, and has minor architecture drift from the PRD. Needs a full rewrite aligned with actual behavior.

- [ ] **Step 1: Write the new README.md**

  ```markdown
  # goldfish

  **Persistent memory for Claude Code agents.** One command installs and wires together GitNexus, OMEGA, and Semble so your AI agent never starts a session from scratch again.

  ```bash
  uvx goldfish init
  ```

  ---

  ## The problem

  Claude Code agents are stateless. Every session starts from zero. You spend 10–30 minutes re-explaining context that was already established yesterday. The agent repeats mistakes it already made, asks questions already answered, and changes a function without knowing 47 others depend on it.

  The tools to fix this exist. Nothing connects them. That's the gap goldfish fills.

  ## What goldfish solves

  | Failure | Cause | Solution |
  |---------|-------|---------|
  | Session amnesia | Agent starts blank every session | OMEGA episodic memory mines JSONL logs |
  | Codebase blindness | Agent doesn't know the shape of the code | GitNexus code knowledge graph |
  | Decision blindness | Agent doesn't know why things are built this way | Vault markdown notes + OMEGA |
  | Impact blindness | Agent doesn't know what breaks when it changes something | GitNexus blast-radius analysis |
  | Prompt deafness | Agent gets generic context, not prompt-specific context | Chonkie + Semble + OMEGA fan-out |

  ## How it works

  goldfish is an orchestration layer (~500 lines of Python), not a memory engine. Every function is a subprocess call, a file write, or a config read. The heavy lifting is done by:

  | Tool | Install | Purpose |
  |------|---------|---------|
  | **GitNexus** | `npm install -g gitnexus` | Code graph, blast radius, execution flows |
  | **OMEGA** | `uv tool install omega-memory` | Episodic memory, SQLite, offline |
  | **Semble** | `uv tool install semble` | Semantic search over code and vault notes |
  | **Chonkie** | transitive dep of Semble | Splits multi-topic prompts into search queries |

  ### The flow

  ```
  Claude Code JSONL logs         ← source of truth
         ↓ mined by OMEGA
  SQLite episodic store          ← past decisions, lessons, errors
         ↓ written by goldfish
  ~/.goldfish/vaults/{project}/  ← plain markdown vault
         ↑ indexed by GitNexus
  Code knowledge graph           ← symbols, callers, execution flows
         ↑ searched by Semble
  Prompt enrichment              ← context injected before every task
         ↑ decomposed by Chonkie
  ```

  ### Hook lifecycle

  When you work in Claude Code, goldfish responds to lifecycle events:

  | Event | What happens |
  |-------|-------------|
  | `SessionStart` | Drains queue, generates wake-up context from vault |
  | `UserPromptSubmit` | Decomposes prompt → fans out to Semble (code + vault) + OMEGA (memory) → injects context |
  | `PreCompact` | Drains queue, writes checkpoint note to vault |
  | `PostToolUse(Write\|Edit)` | Re-indexes changed file with Semble |
  | `PostToolUse(Bash git commit*)` | Records commit note in OMEGA |
  | `TaskCreated` / `TaskCompleted` | Writes task notes to vault |
  | `Stop` / `SessionEnd` | Advances JSONL offset in manifest |

  All async events write to `~/.goldfish/queue.jsonl` first and return in <10ms so Claude never blocks.

  ### Vault layout

  All knowledge is plain markdown — readable with `cat`, searchable with `grep`, versionable with `git`.

  ```
  ~/.goldfish/vaults/{project}/
  ├── .manifest.toml           ← sync state (byte offset, timestamps)
  ├── Memory/
  │   ├── Decisions/           ← architectural choices and rationale
  │   ├── Lessons/             ← patterns learned across sessions
  │   ├── Errors/              ← bugs and fixes
  │   └── Checkpoints/        ← pre-compaction snapshots
  ├── Specs/                   ← feature specs referenced by tasks
  ├── Tasks/                   ← task notes (created/completed events)
  └── _context/
      └── wake-up.md           ← refreshed every session
  ```

  Each note uses temporal frontmatter:

  ```yaml
  ---
  id: decision-jwt-auth-2026-05-24
  type: decision
  valid_from: 2026-05-24
  superseded_by: null
  confidence: 0.94
  source_session: abc123
  source_offset: 48291
  related:
    - "[[Specs/auth-spec]]"
  ---
  ```

  To supersede a note, set `superseded_by` instead of deleting it. Semble excludes superseded notes from search results automatically.

  ---

  ## Installation

  ### Prerequisites

  - Python 3.11+
  - Node.js 18+
  - [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

  ### Quick start

  ```bash
  # Run the init wizard (detects and installs all dependencies)
  uvx goldfish init
  ```

  The wizard:
  1. Checks for Node.js, installs GitNexus (`npm install -g gitnexus`) if needed
  2. Installs OMEGA (`uv tool install omega-memory`) if needed, downloads embedding model (~127 MB, one-time)
  3. Installs Semble (`uv tool install semble`) if needed
  4. Runs `npx gitnexus analyze` to build the code graph (skipped if `.gitnexus/` exists)
  5. Scaffolds `~/.goldfish/vaults/{project}/`
  6. Registers all 9 Claude Code hook events in `~/.claude/settings.json`
  7. Appends the agent knowledge block to `CLAUDE.md`

  Re-running `goldfish init` is safe — it reports health and skips already-installed tools.

  ---

  ## CLI reference

  ```
  goldfish init              Run the setup wizard
  goldfish hook              Handle a hook event from stdin (called by Claude Code)
  goldfish drain             Process queued events from ~/.goldfish/queue.jsonl
  goldfish register-hooks    Re-register hooks with the correct binary path
  goldfish status            Show current configuration and sync state
  goldfish doctor            Check all dependencies are installed and reachable
  goldfish replay            Re-process JSONL events from a session file
  ```

  ---

  ## Architecture

  ```
  cli.py        Typer CLI: init, hook, drain, register-hooks, status, doctor, replay
  init.py       Wizard: checks/installs deps, scaffolds vault, registers hooks
  hook.py       Reads stdin JSON event → appends to queue.jsonl; enriches UserPromptSubmit synchronously
  drain.py      Time-budgeted queue processor; routes events to subprocess/file writes
  enricher.py   Chonkie decompose → Semble (code + vault) + OMEGA (memory) fan-out per chunk
  vault.py      pathlib-only file writes: write_note(), read_note(), scaffold()
  claude_md.py  Upserts goldfish hooks in settings.json; updates CLAUDE.md block in-place
  config.py     Reads/writes ~/.goldfish/config.toml and per-project .manifest.toml
  ```

  ### Non-negotiable constraints

  - No search, embedding, or graph code — use the right tool
  - No always-on processes — every tool opens, executes, closes
  - Hook handlers return in <10ms — write to queue and exit
  - GitNexus is PolyForm Noncommercial — install via `npm install -g gitnexus` only, never bundle

  ---

  ## Development

  ```bash
  git clone https://github.com/miztertea/goldfish
  cd goldfish
  uv sync
  uv run pytest
  ```

  Tests stub all subprocess calls and run without live tool installations.

  ```bash
  uv run pytest -v          # run all tests
  uv run goldfish --help    # run CLI from source
  ```

  ---

  ## License

  MIT
  ```

- [ ] **Step 2: Verify the README renders correctly (spot-check key sections)**

  ```bash
  grep -n "pip install" /home/tchawes/goldfish/README.md
  ```

  Expected: No output (no pip install references remaining).

  ```bash
  grep -n "Obsidian" /home/tchawes/goldfish/README.md
  ```

  Expected: Only the `superseded_by` doc note and vault layout — no "install Obsidian" or "Obsidian plugin" references.

- [ ] **Step 3: Commit**

  ```bash
  git add README.md
  git commit -m "docs: rewrite README against current architecture and spec"
  ```

---

## Task 6: Verify complete test suite and doctor output

- [ ] **Step 1: Run full test suite**

  ```bash
  cd /home/tchawes/goldfish && uv run pytest -v
  ```

  Expected: All tests pass, 0 failed, 0 warnings from drain.py.

- [ ] **Step 2: Run doctor**

  ```bash
  cd /home/tchawes/goldfish && uv run goldfish doctor
  ```

  Expected: `✓ omega-memory MCP`, `✓ semble`, `✓ gitnexus` — no false failures.

- [ ] **Step 3: Run goldfish status**

  ```bash
  cd /home/tchawes/goldfish && uv run goldfish status
  ```

  Expected: Shows project, queue depth, manifest state cleanly.

---

## Self-Review

**Spec coverage:**
- Session amnesia / OMEGA: no changes (working)
- Codebase blindness / GitNexus: no changes (working)
- Decision blindness / vault: no changes (working)
- Impact blindness: no changes (working)
- Prompt deafness / Chonkie+Semble: no changes (working)
- First-run UX (omega model): Task 3 covers this
- Doctor accuracy: Task 2 covers this
- Test correctness: Task 1 covers this
- Documentation: Task 5 covers this
- Deprecation warnings: Task 4 covers this

**Placeholder scan:** No TBDs, TODOs, or vague instructions. All code blocks are complete.

**Type consistency:** No new types or method signatures introduced. All changes are minimal patches to existing code.
