<!-- layer 3: project — maintained by project team -->
# AGENTS.md

This is the agent constitution for goldfish development. Read this before touching any code.

## What you're working in

goldfish is an orchestration layer (~500 lines of Python, 9 modules). Every function is a subprocess call, a file write, or a config read. There is no search code, no embedding code, no graph code — those problems are solved by GitNexus, OMEGA, and Semble. goldfish wires them together.

## The five failures (your contribution guardrail)

Every change must map to at least one of these failures. If your change doesn't address any of them, don't build it.

| Context Failure | Symptom | Tool |
|----------------|---------|------|
| 1. Session amnesia | "We discussed this last week" / "You already fixed that" | OMEGA |
| 2. Codebase blindness | 15 tool calls to find one function; missing a module entirely | GitNexus |
| 3. Decision blindness | "I'll use Redis for sessions" (we decided against that) | OMEGA + vault |
| 4. Impact blindness | Changes verify_jwt(), breaks 4 callers silently | GitNexus |
| 5. Prompt deafness | "Fix the auth bug" → agent searches from zero | Chonkie + Semble + OMEGA |

## Non-negotiable constraints

- **Never write search, embedding, or graph code.** Find the right tool and call it as a subprocess.
- **No always-on processes.** Every tool opens, executes, and closes. No daemons, no Docker.
- **Hook handlers return in <10ms.** Write to queue.jsonl and exit. Never block Claude.
- **GitNexus is PolyForm Noncommercial.** Install via `npm install -g gitnexus` only. Never bundle or redistribute.

---

<!-- layer 2: goldfish — superpowers workflow for contributors -->

## Superpowers workflow (required for all contributors)

goldfish uses superpowers skills for all development. When contributing:

- **Before any feature work:** invoke `brainstorming` skill — design before code
- **Before implementation:** invoke `writing-plans` skill — plan before writing
- **All features:** use `test-driven-development` skill — test before implementation
- **Before completing:** invoke `verification-before-completion` skill — verify before claiming done
- **Independent tasks:** use `dispatching-parallel-agents` skill — parallelize when safe

For all code exploration, use the tools in the maintained sections below — not grep or bash.

## What goldfish contributes (don't rebuild this)

goldfish does exactly these things and nothing more:

1. Init wizard that installs all tools via their official methods
2. The Layer 2 coordination block written to every project's CLAUDE.md
3. Processing of Claude Code lifecycle events (SessionStart, UserPromptSubmit, PreCompact, PostToolUse, etc.)
4. The event queue decoupling hook handlers from downstream processing (<10ms guarantee)
5. Vault markdown file writes connecting OMEGA episodic memory to human-readable notes
6. Prompt enrichment fan-out to all three search layers simultaneously
7. Per-project manifest tracking sync state across sessions
8. Wake-up context generation at session start
9. New-vs-existing project distinction at SessionStart

## Further reading

- [docs/architecture.md](docs/architecture.md) — system architecture and runtime flows
- [docs/five-failures.md](docs/five-failures.md) — the framework in detail
- [docs/tool-selection.md](docs/tool-selection.md) — why each tool was chosen
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup and PR process

---

## Tool-Specific Instructions (Layer 1)

These blocks are auto-maintained IN THIS FILE by each tool's CLI (see the `<!-- gitnexus:start/end -->` block below). No action needed — they stay current automatically.

<!-- layer 1: tool blocks — do not edit, maintained by each tool -->
<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **goldfish** (1046 symbols, 1276 relationships, 30 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
