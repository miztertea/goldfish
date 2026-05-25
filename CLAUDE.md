# CLAUDE.md

## What this is

goldfish is an orchestration layer (~500 lines of Python) that installs and wires together GitNexus, OMEGA, and Semble. It does not build search, embeddings, or graphs — those problems are solved by dedicated tools. Every function is a subprocess call, a file write, or a config read.

## Module map

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

## Non-negotiable constraints

- **Never write search, embedding, or graph code.** Find the right tool and call it.
- **No always-on processes.** Every tool opens, executes, and closes. No daemons.
- **Hook handlers return in <10ms.** Write to queue.jsonl and exit. Never block Claude.
- **GitNexus is PolyForm Noncommercial.** Install via `npm install -g gitnexus` only. Never bundle.

## Hook event routing

Synchronous (Claude waits for stdout): `SessionStart`, `UserPromptSubmit`, `PreCompact`
Async (`async: true`): `PostToolUse`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `SessionEnd`

goldfish registers `PostToolUse` so GitNexus hooks coexist cleanly. GitNexus registers its own `PreToolUse` and `PostToolUse` during `gitnexus analyze` — both sets coexist without conflict.

## Testing approach

- Test at module boundaries: input/output assertions, not internal calls
- Stub subprocess calls and the OMEGA API — tests run without live tool installations
- ~100 tests, ~0.3s
- See `tests/` for patterns per module

## Docs

| Topic | File |
|-------|------|
| System architecture + runtime flows | [docs/architecture.md](docs/architecture.md) |
| Five failures framework | [docs/five-failures.md](docs/five-failures.md) |
| Tool selection rationale | [docs/tool-selection.md](docs/tool-selection.md) |
| Design decisions log | [docs/design-decisions.md](docs/design-decisions.md) |
| Obsidian optional viewer | [docs/obsidian.md](docs/obsidian.md) |

## Agent Knowledge Tools (managed by goldfish)

goldfish wires together three intelligence layers. Query all three before any non-trivial task.

| Layer | Tool | What it knows |
|-------|------|---------------|
| Code + impact | GitNexus (MCP) | Call graph, execution flows, blast radius, pre-commit diff |
| Episodic memory | OMEGA (MCP) | Past decisions, session history, known issues |
| Semantic search | Semble (MCP) | Code by meaning, vault notes and decisions |

### Before any refactor or architecture change:
1. GitNexus context — understand the symbol and its callers
2. GitNexus impact — know the blast radius before touching anything
3. OMEGA query — check prior decisions and known issues on this topic
4. Then act.

Each tool's full usage instructions are in its own maintained section in this file.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **goldfish** (1017 symbols, 1247 relationships, 30 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
