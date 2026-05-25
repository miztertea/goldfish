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

GitNexus, OMEGA, and Semble each maintain their own instruction blocks automatically. These blocks are kept current in `CLAUDE.md` by each tool's CLI. If you are using Claude Code, those blocks are already in your context. If you are using another agent framework, read the relevant sections from `CLAUDE.md` directly.
