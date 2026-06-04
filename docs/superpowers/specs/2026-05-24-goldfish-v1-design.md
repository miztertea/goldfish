# Goldfish v1.0 Design Spec

**Date:** 2026-05-24  
**Status:** Approved  
**Author:** Thomas Hawes  

---

## Goal

Complete the goldfishh v1.0 stack by closing the gap between passive memory (hooks, drain, vault — working) and active memory (MCP servers the agent calls at will — not yet registered). Also stabilize the hook binary path, update the CLAUDE.md active layer block to reference MCP tool names, improve wake-up context quality, and complete the operational tooling (doctor, replay resumability, semble_indexed_at tracking).

---

## Architecture

goldfishh is an orchestration layer — an Ansible playbook, not an application. Every function is a subprocess call, a file write, or a config read. No search algorithms, no embeddings, no graph code. The five tools (GitNexus, OMEGA, Semble, Chonkie, vault) each solve one or two of the five context failures; goldfishh installs, wires, and routes events between them.

v1.0 = passive memory (fully working) + active memory (MCP registration) + stability + quality improvements.

---

## Tech Stack

- Python 3.11+, typer, pathlib, subprocess, PyYAML, tomli-w
- GitNexus (npm), OMEGA (uv tool install), Semble (uv tool install)
- uv (required runtime alongside Node.js)

---

## Section 1: Init Wizard — Complete Flow

`init.py` gains six changes to match the PRD wizard exactly.

### 1.1 Self-install for hook path stability

First step in `run()`, before any tool installation:

```python
PACKAGE_SOURCE = "git+https://github.com/miztertea/goldfishh"

if not shutil.which("goldfishh") or Path(_detect_goldfish_bin()) != Path.home() / ".local/bin/goldfishh":
    result = subprocess.run(["uv", "tool", "install", "--from", PACKAGE_SOURCE, "goldfishh"])
    if result.returncode != 0:
        print("  note: self-install failed; hooks will use current executable")
```

Idempotent: if `~/.local/bin/goldfishh` already exists, `uv tool install` is a fast no-op.

### 1.2 GitNexus MCP registration

After `npx gitnexus analyze`, add:

```python
subprocess.run(["npx", "gitnexus", "setup"], cwd=cwd)
print("✓ GitNexus MCP registered")
```

`gitnexus setup` is idempotent — re-running updates the MCP entry without creating duplicates.

### 1.3 OMEGA MCP registration

Replace `["omega", "setup"]` with `["omega", "setup", "--client", "claude-code"]`. This registers the OMEGA MCP server in `~/.claude.json` AND installs OMEGA's own hooks (PostToolUse surface_memories, UserPromptSubmit auto_capture). These complement goldfishh's hooks — OMEGA captures memory, goldfishh enriches prompts and writes vault notes.

```python
r2 = subprocess.run(["omega", "setup", "--client", "claude-code"])
```

### 1.4 Semble MCP registration

After `uv tool install semble`, add:

```python
subprocess.run([
    "claude", "mcp", "add", "semble", "-s", "user",
    "--", "uvx", "--from", "semble[mcp]", "semble"
])
print("✓ Semble MCP registered")
```

Idempotent: `claude mcp add` overwrites if the key exists.

### 1.5 MCP registration tracked in manifest

After all three MCP registrations succeed, write to manifest:

```python
manifest["mcp_registered"] = True
write_manifest(project, manifest, vaults_root=vaults_root)
```

On subsequent `goldfishh init` runs, if `manifest.get("mcp_registered")` is True, skip MCP registration steps with a `✓ MCPs already registered` status line.

### 1.6 CLAUDE.md block updated to MCP tool names

Replace the existing `_CLAUDE_MD_BLOCK` constant in `init.py` with the PRD's active layer format using MCP tool names (see Section 3 below). The existing `append_claude_md_block` update-in-place logic handles this without duplication.

---

## Section 2: Hook Path Stability

### 2.1 `_detect_goldfish_bin()` preference order

In `claude_md.py`, update `_detect_goldfish_bin()` to prefer the stable uv tool install path:

```python
def _detect_goldfish_bin() -> str:
    stable = Path.home() / ".local" / "bin" / "goldfishh"
    if stable.exists():
        return str(stable)
    which = shutil.which("goldfishh")
    if which:
        return which
    return str(Path(sys.executable).parent / "goldfishh")
```

After `goldfishh init` self-installs, all subsequent hook registrations resolve to `~/.local/bin/goldfishh`.

---

## Section 3: CLAUDE.md Active Layer Block

Replace the `_CLAUDE_MD_BLOCK` constant in `init.py`:

```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

## Agent Knowledge Tools (managed by goldfishh)

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

#### Semantic Search — Semble (MCP)
- `semble_search(query, path="./src")` — code search by meaning
- `semble_search(query, path="~/.goldfishh/vaults/<project>", content="docs")` — vault notes

### Mandatory workflow before refactoring:
1. `gitnexus context({{name}})` → understand the symbol
2. `gitnexus impact({{target}})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.
"""
```

---

## Section 4: Wake-up Content Quality

In `drain.py` `handle_session_start`, after the OMEGA query, add two vault reads.

### 4.1 Open tasks

```python
tasks_dir = vaults_root / project / "Tasks"
open_tasks = []
if tasks_dir.exists():
    for note_file in sorted(tasks_dir.iterdir())[-10:]:  # last 10
        _, body = read_note(project, f"Tasks/{note_file.name}", vaults_root=vaults_root)
        if "**Completed.**" not in body:
            open_tasks.append(note_file.stem)
```

### 4.2 Recent decisions

```python
decisions_dir = vaults_root / project / "Memory" / "Decisions"
recent_decisions = []
if decisions_dir.exists():
    files = sorted(decisions_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[:3]:
        lines = f.read_text().splitlines()
        # first non-frontmatter heading line
        heading = next((l for l in lines if l.startswith("# ")), f.stem)
        recent_decisions.append(heading.lstrip("# "))
```

### 4.3 Wake-up body assembly

```python
if open_tasks:
    body += f"\n## Open Tasks\n\n" + "\n".join(f"- {t}" for t in open_tasks) + "\n"
if recent_decisions:
    body += f"\n## Recent Decisions\n\n" + "\n".join(f"- {d}" for d in recent_decisions) + "\n"
```

---

## Section 5: Supporting Changes

### 5.1 `semble_indexed_at` tracking

After every `_run(["semble", "index", ...])` or `_run(["semble", "reindex", ...])` call in `drain.py` and `handle_session_start`, write the timestamp:

```python
manifest = get_manifest(project, vaults_root=vaults_root)
write_manifest(project, {**manifest, "semble_indexed_at": datetime.utcnow().isoformat()}, vaults_root=vaults_root)
```

### 5.2 Doctor completeness

Add three checks to `cli.py` `doctor` command:

**Semble installed:**
```python
result = subprocess.run(["semble", "--version"], capture_output=True)
print("✓ Semble" if result.returncode == 0 else "✗ Semble not found — run: uv tool install semble")
```

**MCP registration:**
```python
claude_json = Path.home() / ".claude.json"
if claude_json.exists():
    data = json.loads(claude_json.read_text())
    mcp = data.get("mcpServers", {})
    for name in ("omega", "semble", "gitnexus"):
        status = "✓" if name in mcp else "✗"
        print(f"{status} {name} MCP{'  — run: goldfishh init to register' if status == '✗' else ''}")
```

**Vault health:**
```python
vault = vaults_root / project
expected = ["Memory/Decisions", "Memory/Lessons", "Memory/Errors", "Tasks", "Specs", "_context"]
for d in expected:
    exists = (vault / d).exists()
    print(f"{'✓' if exists else '✗'} vault/{d}")
```

### 5.3 Replay resumability

In `cli.py` `replay` command, read `last_byte_offset` and `last_jsonl_file` from manifest:

```python
manifest = get_manifest(project, vaults_root=vaults_root)
resume_file = manifest.get("last_jsonl_file", "")
resume_offset = manifest.get("last_byte_offset", 0)
```

Sort JSONL files by mtime (oldest first). Skip files with mtime older than `resume_file`'s mtime. For `resume_file` itself, open and seek to `resume_offset` before reading lines. For all newer files, read from byte 0. After each successful batch, write updated `last_byte_offset` and `last_jsonl_file` back to manifest.

---

## Error Handling

All three MCP registration commands use `subprocess.run()` without `check=True`. Non-zero exit codes print a warning but do not `sys.exit(1)` — a failed `claude mcp add` should not abort the entire init. The doctor command surfaces registration failures after the fact.

The `_run()` helper (already in `drain.py` and `enricher.py`) catches `FileNotFoundError` for optional binaries. The same pattern applies to `claude mcp add` if the `claude` CLI is not found.

---

## Testing

All tests mock subprocess calls and file I/O. No live tool installations required.

**init.py:**
- `test_init_registers_omega_mcp` — verify `omega setup --client claude-code` called (not bare `omega setup`)
- `test_init_registers_semble_mcp` — verify `claude mcp add semble ...` called when semble present
- `test_init_registers_gitnexus_mcp` — verify `npx gitnexus setup` called after analyze
- `test_init_skips_mcp_if_already_registered` — manifest `mcp_registered=True` → no MCP calls
- `test_init_self_installs_goldfish` — `uv tool install --from ... goldfishh` called as first step

**claude_md.py:**
- `test_detect_goldfish_bin_prefers_local_bin` — `~/.local/bin/goldfishh` returned when exists
- `test_detect_goldfish_bin_falls_back_to_which` — falls back when local bin absent

**drain.py:**
- `test_session_start_includes_open_tasks_in_wakeup` — Tasks/ with incomplete note → body contains task name
- `test_session_start_includes_recent_decisions` — Decisions/ with 3 files → body lists them
- `test_semble_indexed_at_written_after_index` — manifest updated after semble index call

**cli.py:**
- `test_doctor_checks_mcp_registration` — `~/.claude.json` missing omega → prints ✗ omega MCP
- `test_doctor_checks_vault_structure` — missing Tasks/ → prints ✗ vault/Tasks

---

## File Structure

| File | Changes |
|------|---------|
| `src/goldfishh/init.py` | Self-install step, MCP registration (3 tools), updated CLAUDE.md block, manifest `mcp_registered` flag |
| `src/goldfishh/claude_md.py` | `_detect_goldfish_bin()` preference order |
| `src/goldfishh/drain.py` | Wake-up open tasks + recent decisions reads, `semble_indexed_at` writes |
| `src/goldfishh/cli.py` | Doctor: Semble check, MCP registration check, vault health; Replay: resumability |
| `tests/test_init.py` | 5 new tests for MCP registration and self-install |
| `tests/test_claude_md.py` | 2 new tests for `_detect_goldfish_bin` |
| `tests/test_drain.py` | 3 new tests for wake-up quality and semble_indexed_at |
| `tests/test_cli.py` | 2 new tests for doctor |
