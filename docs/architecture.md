# Architecture

goldfish is an orchestration layer (~500 lines of Python). Every function is a subprocess call, a file write, or a config read. It does not build search, embeddings, or graphs.

## Component map

```
┌──────────────────────────────────────────────────────────┐
│                     CLAUDE CODE                          │
│           27 hook events, global settings.json           │
└────────────────────────┬─────────────────────────────────┘
                         │ stdin JSON on every event
              ┌──────────▼──────────┐
              │   goldfish hook    │  fast: append to queue, exit
              └──────────┬──────────┘
                         │
              ~/.goldfish/queue.jsonl   append-only, atomic
                         │
              ┌──────────▼──────────┐
              │    queue drain      │  200ms budget, priority lanes
              └──┬────────┬────────┬┘
                 │        │        │
    ┌────────────▼──┐  ┌──▼──┐  ┌──▼──────────────────┐
    │ subprocess:   │  │OMEGA│  │ pathlib.write_text() │
    │ gitnexus      │  │ API │  │ vault markdown files │
    │ semble        │  └─────┘  └──────────────────────┘
    └───────────────┘
                         ↑
              ┌──────────┴──────────┐
              │  Chonkie            │  prompt decomposition
              │  (inside Semble)    │  on UserPromptSubmit
              └─────────────────────┘
```

## Modules

| File | Responsibility |
|------|---------------|
| `cli.py` | Typer CLI: init, hook, drain, register-hooks, status, doctor, replay, mine |
| `init.py` | Setup wizard: detects/installs deps, scaffolds vault, registers hooks |
| `hook.py` | Reads stdin event → appends to queue.jsonl; enriches UserPromptSubmit synchronously |
| `drain.py` | Time-budgeted queue processor: routes events to subprocess/OMEGA API/file writes |
| `enricher.py` | Chonkie decompose → Semble + OMEGA fan-out per prompt chunk |
| `vault.py` | pathlib-only file writes: write_note(), read_note(), scaffold() |
| `claude_md.py` | Upserts goldfish block in CLAUDE.md; registers hooks in settings.json |
| `config.py` | Reads/writes ~/.goldfish/config.toml and per-project .manifest.toml |
| `miner.py` | Replays historical JSONL sessions through OMEGA's own hooks |

## Four-layer agent instruction model

goldfish installs agent instructions at four layers. Understanding the layers prevents duplication and drift:

| Layer | Maintained by | Where | Content |
|-------|--------------|-------|---------|
| Layer 0 — File-based memory | Auto-memory system | `memory/*.md` loaded at session start | User preferences, behavioral feedback, reference pointers — zero latency |
| Layer 1 — Tool-native | GitNexus, OMEGA, Semble | `<!-- gitnexus:start/end -->` in project files; `~/.claude/CLAUDE.md` for OMEGA; `.claude/agents/semble-search.md` | Each tool's specific MCP tool signatures and usage examples |
| Layer 2 — Coordination | goldfish (`init.py` → `claude_md.py`) | `## Agent Knowledge Tools (managed by goldfish)` sentinel | Cross-tool orchestration: query all layers before acting |
| Layer 3 — Project-specific | Human or agent | Above maintained blocks in `CLAUDE.md` and `AGENTS.md` | Codebase-specific guardrails, module map, contributor workflow |

Rule: Layer 3 and 2 authored content says WHY and WHAT. Layer 1 blocks say HOW. Layer 0 loads automatically at zero latency.

## Project identity and vault location

Project identity = `cwd`. This mirrors how Claude Code organizes its own JSONL transcripts at `~/.claude/projects/{encoded-cwd}/`.

Vault location: `~/.goldfish/vaults/{Path(cwd).name}/`  
GitNexus index: `{cwd}/.gitnexus/`  
Queue: `~/.goldfish/queue.jsonl`

No scanning, no discovery — everything is deterministic from `cwd`.

## Vault structure

```
~/.goldfish/vaults/{project}/
├── .manifest.toml          ← sync state: JSONL offset, bootstrap status, semble_indexed_at
├── Memory/
│   ├── Decisions/          ← why choices were made
│   ├── Lessons/            ← what worked and what didn't
│   ├── Errors/             ← bugs found and fixed
│   └── Checkpoints/        ← session snapshots before compaction
├── Specs/                  ← human + agent authored specs
├── Tasks/                  ← one note per task, linked to sessions
└── _context/               ← ephemeral: wake-up.md written each session
```

Vault notes use temporal frontmatter:

```yaml
---
id: decision-jwt-auth-2026-05-24
type: decision | lesson | error | checkpoint
valid_from: 2026-05-24
superseded_by: null
confidence: 0.94
source_session: abc123
source_offset: 48291
related:
  - "[[Specs/auth-spec]]"
---
```

To supersede a note: set `superseded_by` and write a new note. Old notes are never deleted.

## Hook registration

Registered globally at `~/.claude/settings.json` — fires for every Claude Code session.

```
Synchronous (Claude waits for stdout):
  SessionStart       → goldfish hook  (bootstrap or catchup + wake-up)
  UserPromptSubmit   → goldfish hook  (enrichment → stdout)
  PreCompact         → goldfish hook  (session snapshot)

Async (Claude does not wait):
  PostToolUse        → goldfish hook  (registered so GitNexus hooks coexist)
  SubagentStop       → goldfish hook
  TaskCreated        → goldfish hook
  TaskCompleted      → goldfish hook
  Stop               → goldfish hook
  SessionEnd         → goldfish hook

GitNexus registers its own hooks during gitnexus analyze:
  PreToolUse         → gitnexus hook
  PostToolUse        → gitnexus hook
```

Both hook sets coexist in `settings.json` without conflict.

## Runtime flows

### SessionStart — new project

```
Claude Code launches
        ↓
goldfish hook: .manifest.toml absent → NEW PROJECT
        ↓
scaffold(vault)
write_note("_context/wake-up.md", "First session. Vault ready.")
write_manifest(bootstrap_complete=True)
        ↓
stdout: wake-up.md path → injected as Claude context
```

### SessionStart — existing project

```
.manifest.toml exists
        ↓
omega query("current project state tasks decisions") → context
write_note("_context/wake-up.md", context)
        ↓
stdout: full context, no warning
Total: ~50-200ms
```

### UserPromptSubmit — prompt enrichment

```
Developer types: "fix auth middleware and JWT rotation, also CI broken"
        ↓
Chonkie.SentenceChunker(prompt) →
  chunk_1: "fix auth middleware JWT rotation"
  chunk_2: "CI broken"
        ↓
Parallel per chunk:
  semble search chunk ./src              → code hits
  semble search chunk vault --include-text-files → vault hits
  omega query(chunk)                     → memory hits
        ↓
Collect, deduplicate, format
        ↓
stdout: enriched context → Claude sees it before acting
Total: ~25ms
```

### PreCompact — snapshot before context loss

```
Claude's context window approaches capacity
        ↓
PreCompact fires (Claude waits)
        ↓
omega flush(session_snapshot)
vault.write("Memory/Checkpoints/{session_id}.md", summary)
        ↓
PreCompact returns → compaction proceeds
```
