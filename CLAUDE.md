# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read these first — every session, no exceptions

- **PRD.md** — specification and architecture
- **DESIGN-COMPANION.MD** — every decision and why it was made

## What This Is

Goldfish is a Python CLI tool (`uvx goldfish init`) that wires together existing open-source tools to give Claude Code agents persistent, structured memory across sessions. It is **not** a memory engine — it is an orchestration layer (think Ansible playbook) that installs and connects: GitNexus, OMEGA, Semble, and Chonkie. ~400–600 lines of Python total. No search algorithms, no embeddings, no graph code.

The codebase does not exist yet. The PRD.md and DESIGN-COMPANION.MD are the complete specification. Build from those.

## Module Structure

```
cli.py       — typer CLI: init, hook, process, status, doctor, replay
init.py      — wizard: detects/installs all deps, runs gitnexus analyze + omega setup, scaffolds vault
hook.py      — reads stdin JSON event, appends to queue.jsonl, exits (<10ms); synchronously enriches UserPromptSubmit only
drain.py     — reads queue with 200ms budget, routes by event type to subprocess/OMEGA API/file writes
vault.py     — pathlib-only file writes: write_note(), read_note(), scaffold(); YAML frontmatter; no network
claude_md.py — surgically appends/updates CLAUDE.md and ~/.claude/settings.json; never overwrites
config.py    — reads/writes ~/.goldfish/config.toml and per-project .manifest.toml
```

## The Five Failures (drives every decision)

Every feature must map to at least one:
1. **Session amnesia** → OMEGA (SQLite episodic memory)
2. **Codebase blindness** → GitNexus (code graph, `npx gitnexus analyze`)
3. **Decision blindness** → OMEGA + vault markdown notes
4. **Impact blindness** → GitNexus (`gitnexus impact()`)
5. **Prompt deafness** → Chonkie (decompose prompt) + Semble (search code + vault) + OMEGA

## Tool Stack

| Tool | Install | Purpose |
|------|---------|---------|
| GitNexus | `npm install -g gitnexus` → `npx gitnexus analyze` | Code graph, blast radius, hooks, skills — do not replicate |
| OMEGA | `pip install omega-memory` → `omega setup` | Episodic memory, MCP, SQLite+ONNX, no daemon |
| Semble | `uv tool install semble` | Semantic code search + vault search via `--content docs` |
| Chonkie | transitive dep of Semble | SentenceChunker decomposes multi-topic prompts before fan-out |

## Non-Negotiable Constraints

- **Never write search, embedding, or graph code.** If you're writing a search algorithm, stop and find the right tool.
- **No always-on processes.** Every tool opens, executes, and closes. No daemons, no Docker.
- **Hook handlers must return in <10ms.** Write to queue.jsonl and exit. Never block Claude.
- **GitNexus license:** PolyForm Noncommercial. Install via `npm install -g gitnexus` only. Never bundle or redistribute.
- **Obsidian is optional.** Write markdown files with pathlib. That's the entire Obsidian integration. No plugins, no API keys, no REST client.
- **init.py is idempotent.** Re-running reports health, does not overwrite working config.

## Hook Event Routing

Synchronous (Claude waits for stdout): `SessionStart`, `UserPromptSubmit`, `PreCompact`  
Async (`async: true`): `PostToolUse(Write|Edit)`, `PostToolUse(Bash(git commit*))`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `SessionEnd`

GitNexus registers its own `PreToolUse` and `PostToolUse` hooks during `gitnexus analyze` — these coexist, no conflict.

## Queue Design

`~/.goldfish/queue.jsonl` — atomic JSONL appends, no locking. Drain prioritizes: session-lifecycle > tool events > file-change events. Partial drains leave remaining lines for the next cycle.

## Vault Layout

```
~/.goldfish/vaults/{project-name}/
├── .manifest.toml       ← last_byte_offset, bootstrap_complete, semble_indexed_at
├── Memory/
│   ├── Decisions/
│   ├── Lessons/
│   ├── Errors/
│   └── Checkpoints/
├── Specs/
├── Tasks/
└── _context/            ← ephemeral wake-up.md, refreshed each session
```

Project identity = `cwd`. Vault name = `Path(cwd).name`. No Code/ directory — GitNexus owns code intelligence in `.gitnexus/`.

## Vault Note Frontmatter Schema

```yaml
---
id: decision-{slug}-{date}
type: decision | lesson | error | checkpoint
valid_from: 2026-03-01
superseded_by: null          # set this instead of deleting old notes
confidence: 0.94
source_session: abc123
source_offset: 48291
related:
  - "[[Specs/auth-spec]]"
---
```

Semble search excludes notes where `superseded_by` is non-null (by not indexing them).

## Testing Approach

Test at module boundaries via input/output assertions, not internal function calls. Stub subprocess calls and the OMEGA API — tests run without live tool installations.

- **hook.py:** Any event payload → exactly one line added to queue.jsonl
- **drain.py:** Five queued events, 200ms budget for three → two remain in priority order
- **vault.py:** Decision payload → correct file at correct path with all frontmatter fields
- **config.py:** No manifest → `is_new_project()` returns true; manifest with offset → correct sync state
- **init.py:** Node.js absent → reports gap before touching any files; existing config → health check only
- **claude_md.py:** Existing CLAUDE.md → block appended, existing content unchanged; second run → block updated in place, not duplicated

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **goldfish** (667 symbols, 854 relationships, 28 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/goldfish/context` | Codebase overview, check index freshness |
| `gitnexus://repo/goldfish/clusters` | All functional areas |
| `gitnexus://repo/goldfish/processes` | All execution flows |
| `gitnexus://repo/goldfish/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Agent Knowledge Tools (managed by goldfish)

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
- `semble_search(query, path="~/.goldfish/vaults/<project>", content="docs")` — vault notes

### Mandatory workflow before refactoring:
1. `gitnexus context({name})` → understand the symbol
2. `gitnexus impact({target})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.


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
- `semble_search(query, path="~/.goldfish/vaults/<project>", content="docs")` — vault notes

### Mandatory workflow before refactoring:
1. `gitnexus context({name})` → understand the symbol
2. `gitnexus impact({target})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.
