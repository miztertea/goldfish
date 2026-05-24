# goldfish

**Persistent memory for Claude Code agents.** One command installs and wires together GitNexus, OMEGA, and Semble so your AI agent never starts a session from scratch again.

```bash
uvx goldfish init
```

---

## The problem

Claude Code agents are stateless. Every session starts from zero. You spend 10–30 minutes re-explaining context that was established yesterday. The agent repeats mistakes it already made, asks questions already answered, and changes a function without knowing 47 others depend on it.

The tools to fix this exist. No single tool covers everything, and nothing connects them. That's the gap goldfish fills.

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
| **OMEGA** | `pip install omega-memory` | Episodic memory, SQLite, offline |
| **Semble** | `uv tool install semble` | Semantic search over code and vault notes |
| **Chonkie** | transitive dep of Semble | Splits multi-topic prompts into search queries |

### The flow

```
Claude Code JSONL logs         ← source of truth
       ↓ mined by OMEGA
SQLite episodic store          ← past decisions, lessons, errors
       ↓ written by goldfish
~/.goldfish/vaults/{project}/  ← plain markdown vault (human-readable)
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

All knowledge is plain markdown — readable with `cat`, searchable with `grep`, versionable with `git`, and viewable as a graph in [Obsidian](https://obsidian.md) (no plugins required).

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

# Or install globally first
uv tool install goldfish
goldfish init
```

The wizard:
1. Checks for Node.js, installs GitNexus (`npm install -g gitnexus`) if needed
2. Installs OMEGA (`pip install omega-memory`) if needed
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

Tests stub all subprocess calls and run without live tool installations. 78 tests, ~0.3s.

```bash
uv run pytest -v          # run all tests
uv run goldfish --help    # run CLI from source
```

---

## License

MIT
