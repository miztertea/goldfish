# goldfish mine — Design Spec

**Date:** 2026-05-24  
**Status:** Approved for implementation

---

## Problem

OMEGA episodic memory has been capturing decisions and lessons automatically via Claude Code hooks since goldfish init. But all JSONL session logs that predate init are dark — OMEGA has never seen them. For users onboarding an existing project, every prior decision and lesson is invisible until it surfaces again organically.

**The gap:** `goldfish init` sets up future capture but does nothing for the past.

---

## Goal

Add `goldfish mine` — a CLI command that replays historical Claude Code JSONL session logs through OMEGA's own hook scripts, seeding episodic memory with past decisions and lessons. It is also called automatically during `goldfish init` for existing projects.

---

## Design Principles

1. **Zero classification logic in goldfish.** OMEGA's hook scripts (`auto_capture.py`, `assistant_capture.py`) already detect decisions, lessons, and errors. Replay through them — don't reimplement their logic.
2. **No data inflation.** No files copied into the repo. JSONL logs stay in `~/.claude/projects/`.
3. **OMEGA provides all safety.** Flood protection: 20 captures max (user), 10 caps (assistant) per session ID. Conservative regex filters noise. Dedup is handled by OMEGA's bridge.
4. **Incremental.** Processed session IDs recorded in `.manifest.toml`. Re-running `goldfish mine` skips already-processed sessions.
5. **Hook path discovery.** OMEGA hook command strings are already in `~/.claude/settings.json` (written by `goldfish init`). Parse them at runtime — no hardcoded paths.

---

## Architecture

### New file: `src/goldfish/miner.py`

~45 lines. Single public function `mine_project(cwd, settings_path)`.

**Flow:**
1. Locate `~/.claude/projects/{encoded_cwd}/` — the session JSONL directory.
2. Parse `~/.claude/settings.json` to find the auto_capture command (from `UserPromptSubmit` hooks) and assistant_capture command (from `Stop` hooks).
3. Load `.manifest.toml` and read `mined_sessions` (list of already-processed session IDs).
4. For each unprocessed `.jsonl` file:
   - Read all lines, parse JSON, skip malformed.
   - For each `type == "user"` entry: extract text, pipe to auto_capture hook.
   - For each `type == "assistant"` entry: extract text, pipe to assistant_capture hook.
   - Record session ID in `mined_sessions`, write manifest.
5. Return count of sessions processed.

**Why no turn pairing?**  
Claude Code JSONL is a tree (uses `isSidechain`, `parentUuid`), not a flat user/assistant sequence. Turn pairing breaks on cancellations, queued messages, and sidechain chains. Flattening chronologically and treating each message independently is simpler and correct — OMEGA's hooks evaluate each message independently anyway.

**Why no Chonkie?**  
OMEGA's hook scripts have their own length gates (min 20 chars for user, min 200 chars for assistant) and max caps per session. They already handle splitting and noise filtering. Adding Chonkie would duplicate that logic.

### Hook input formats

**auto_capture.py** (user messages):
```json
{"prompt": "<text>", "session_id": "<stem>", "cwd": "<abs_path>"}
```

**assistant_capture.py** (assistant messages):
```json
{"last_assistant_message": "<text>", "session_id": "<stem>", "cwd": "<abs_path>"}
```

These are the exact formats OMEGA's hooks read from stdin. Goldfish pipes JSON to the command's stdin via `subprocess.run(cmd, input=json_bytes)`.

### Text extraction

- **User messages:** `obj["message"]["content"]` — always a string.
- **Assistant messages:** `obj["message"]["content"]` — list of `{type, text}` blocks. Join all `type == "text"` blocks.
- Skip `type == "attachment"`, `type == "ai-title"`, `type == "file-history-snapshot"`, `type == "permission-mode"`.

### Manifest changes

Add `mined_sessions: list[str]` field. Written after each session completes so a crash mid-run doesn't reprocess completed sessions.

```toml
[project]
mined_sessions = ["abc123", "def456"]
```

---

## CLI

### `goldfish mine`

```
goldfish mine              Replay historical JSONL logs into OMEGA memory
```

- Prints progress: `Mining {n} sessions from {path}...`
- Prints per-session: `  Session {stem}: {user_count} user, {asst_count} assistant messages fed`
- Prints summary: `Done. {n} sessions mined.`
- If sessions dir doesn't exist: `No session logs found for this project.` (exit 0)
- If OMEGA hooks not found in settings.json: `OMEGA hooks not registered — run: goldfish init` (exit 1)

### init.py integration

After vault scaffold succeeds (any run where `bootstrap_complete` was already true, i.e. existing project):

```python
from goldfish.miner import mine_project
n = mine_project(cwd)
if n:
    typer.echo(f"Mined {n} historical sessions into OMEGA memory.")
```

For brand-new projects (`bootstrap_complete` was false before this run), skip mining — there are no prior logs relevant to OMEGA yet and the vault is being created fresh.

---

## Files Changed

| File | Change |
|------|--------|
| `src/goldfish/miner.py` | New — `mine_project()`, `_find_hook_cmd()`, `_extract_user_text()`, `_extract_assistant_text()`, `_pipe_to_hook()` |
| `src/goldfish/cli.py` | Add `goldfish mine` command (~15 lines) |
| `src/goldfish/init.py` | Call `mine_project(cwd)` for existing projects after scaffold |
| `src/goldfish/config.py` | Handle `mined_sessions` field in manifest read/write |
| `README.md` | Add `goldfish mine`; fix stale info (see below) |

---

## README Updates

The current README has several stale references that should be corrected as part of this feature:

| Item | Current | Correct |
|------|---------|---------|
| Test count | "78 tests" | "89 tests" |
| Line count | "~500 lines" | "~1000 lines" (946 pre-mine, ~990 after) |
| Python version | "Python 3.11+" | "Python 3.13+" |
| Chonkie | "transitive dep of Semble" | direct goldfish dependency |
| Hook table | Lists PostToolUse(Write\|Edit), PostToolUse(Bash git commit*) | Remove — these handlers were removed in v1.0 |
| CLI reference | Missing `goldfish mine` | Add |
| Architecture table | Missing `miner.py` | Add |

Also add a new **"Onboarding an existing project"** section showing:

```bash
goldfish init          # sets up hooks for future sessions
goldfish mine          # seeds OMEGA from all past sessions (run once)
```

---

## Testing

Test at module boundary — no live OMEGA installation required.

### `tests/test_miner.py`

**`test_mine_project_processes_user_messages`**  
Given a fake JSONL file with one `type=user` entry, and a mock `_pipe_to_hook`, verify the mock is called with `{"prompt": text, "session_id": stem, "cwd": cwd}` and the correct command.

**`test_mine_project_processes_assistant_messages`**  
Same structure, `type=assistant`, verify `{"last_assistant_message": text, ...}`.

**`test_mine_project_skips_already_mined_sessions`**  
Given manifest with `mined_sessions = ["already-done"]`, verify the corresponding JSONL file is never opened.

**`test_mine_project_skips_non_message_entries`**  
JSONL entries with `type=ai-title`, `type=permission-mode`, etc. produce no pipe calls.

**`test_mine_project_returns_session_count`**  
Three JSONL files, two already mined → returns 1.

**`test_mine_project_no_sessions_dir`**  
Non-existent sessions dir → returns 0, no error.

**`test_mine_project_updates_manifest`**  
After processing, `mined_sessions` includes the new session ID.

**`test_find_hook_cmd_parses_settings`**  
Given a real-shaped settings.json structure, verify `_find_hook_cmd` returns the correct command string for `UserPromptSubmit` + `auto_capture`.

---

## Non-Goals

- No re-mining: once a session ID is in `mined_sessions`, it is never reprocessed. If OMEGA is wiped and re-initialized, the user can delete `mined_sessions` from `.manifest.toml` to re-mine.
- No `omega consolidate` or `omega compact` calls — those are post-processing commands OMEGA exposes directly; not goldfish's responsibility.
- No streaming progress bar — simple line-per-session output is sufficient.
- No parallel processing — sessions are processed serially. The bottleneck is OMEGA's bridge, not file I/O.
