# Goldfish — Repo Public-Ready Design

**Date:** 2026-05-24  
**Status:** Approved  
**Scope:** Documentation restructure, repo hygiene, and public release prep. CI/CD and release process are explicitly out of scope — addressed separately.

---

## Problem

The goldfish repo contains excellent internal design artifacts (PRD.md at 38KB, DESIGN-COMPANION.MD at 26KB) written as working documents during the design phase. These served their purpose but are now:
- Mixed audience (spec + rationale + user stories + history all combined)
- Too heavy for the repo root
- Not decomposed into purpose-built files for external contributors or agents

The README references an Obsidian integration without instructions, uses PyPI-style install commands before PyPI listing exists, and lacks a hero image, badges, platform notes, or proper contributor files.

CLAUDE.md is bloated — it includes full reference content (five failures, tool stack, frontmatter schemas, vault layout) that duplicates what's in PRD.md and should live in docs/.

AGENTS.md is currently just the GitNexus managed block with no goldfish-specific agent constitution.

---

## Three-Layer Agent Instruction Architecture

A key architectural insight that governs all file design decisions:

**Layer 1 — Tool-native maintained blocks** (each tool manages its own content)
- OMEGA → global `~/.claude/CLAUDE.md` (episodic memory instructions)
- GitNexus → project `CLAUDE.md` + `AGENTS.md` inside `<!-- gitnexus:start/end -->` sentinels
- Semble → `.claude/agents/semble-search.md` (sub-agent file)

**Layer 2 — Goldfish coordination block** (project-agnostic, installed in every project)
- `## Agent Knowledge Tools (managed by goldfish)` sentinel in `init.py`
- Purpose: cross-tool orchestration. Tells agents to query all three layers before any non-trivial task.
- Must work coherently with Layer 1 in any codebase, not just goldfish itself.
- Open design note: current block lists per-tool API signatures — these are Layer 1 content. A future revision should focus this block purely on cross-tool coordination, leaving specific API usage to each tool's own block.

**Layer 3 — Project-specific hand-authored content** (goldfish repo only)
- Module map, non-negotiable constraints, five failures as design guardrail, hook routing, testing approach, superpowers contributor workflow
- Lives in the hand-authored sections above the maintained blocks in CLAUDE.md and AGENTS.md

**Rule:** Our authored content provides the WHY and the WHAT. Maintained blocks provide the HOW. Never duplicate tool API signatures in hand-authored content — reference the maintained sections instead.

---

## Repo Root Layout (final state)

```
goldfish/
├── README.md              ← hero, badges, quick start, how it works, CLI ref, dev, contributing
├── CLAUDE.md              ← Layer 3 operational content + Layer 2 goldfish block + Layer 1 GitNexus block
├── AGENTS.md              ← Layer 3 agent constitution + Layer 1 GitNexus block (goldfish block not written here)
├── CONTRIBUTING.md        ← human contributor guide: setup, tests, PR process, code style
├── SECURITY.md            ← scope, responsible disclosure
├── LICENSE                ← MIT
├── assets/
│   └── goldfish-logo.png  ← moved from repo root
├── docs/
│   ├── architecture.md    ← from PRD: system architecture, runtime flows, module definitions
│   ├── five-failures.md   ← the framework as a standalone reference
│   ├── tool-selection.md  ← why each tool was chosen (selection gates + decisions)
│   ├── obsidian.md        ← optional viewer: open the folder, no plugins, no API key
│   ├── design-decisions.md ← decisions table from DESIGN-COMPANION Part 12 (durable record)
│   ├── internal/
│   │   ├── PRD.md              ← archived original (moved from root)
│   │   └── DESIGN-COMPANION.MD ← archived after OMEGA seeding
│   ├── tools/
│   │   ├── gitnexus.md    ← existing, unchanged
│   │   ├── omega.md       ← existing, unchanged
│   │   └── semble.md      ← existing, unchanged
│   └── superpowers/       ← existing plans/specs, unchanged
├── src/goldfish/          ← unchanged
├── tests/                 ← unchanged
└── pyproject.toml         ← add [project.urls] Homepage + Repository
```

---

## README

Modeled on clean AI CLI tools (uv, ruff, aider). One job per section.

### Structure

Get to Quick Start immediately — hero, one-liner, badges, then the action. Explanation follows.

```
[Hero image — centered goldfish-logo.png, width 280]
[One-line pitch in bold]
[License badge] [Python 3.13+ badge] [Platform badge]

## Quick start          ← SECOND after hero — action before explanation
[Three commands or fewer]

## The problem          ← five failures table, now below Quick Start
[Five failures table — kept verbatim, it's the pitch]

## How it works         ← introduce the three-layer model here
[Brief intro: "goldfish installs three layers of intelligence into Claude Code"]
[Layer 1 table: GitNexus / OMEGA / Semble — what each does]
[Layer 2 note: goldfish ties them together via a coordination block]
[Layer 3 note: your project-specific instructions layer on top]
[Hook lifecycle table — what fires when]

## Vault
[Directory tree + frontmatter snippet — trimmed]

## CLI reference
[Current table, unchanged]

## Platform support
[New section]

## Development
[git clone, uv sync, uv run pytest — current, kept]

## Contributing
[One-liner + links to CONTRIBUTING.md and AGENTS.md]

## License
[MIT one-liner]
```

**The three-layer model in "How it works":** This is where the layer terminology earns its place in user docs. It explains *why* goldfish is only ~500 lines — it's not reimplementing memory or search, it's wiring three maintained layers together. The table makes this concrete:

| Layer | Installed by | What it provides |
|-------|-------------|-----------------|
| Layer 1 — Tool-native | GitNexus, OMEGA, Semble (via `goldfish init`) | Each tool's own hooks, MCP server, and agent instructions |
| Layer 2 — Coordination | goldfish | A single block that tells agents to query all three layers before acting |
| Layer 3 — Project-specific | You (or your agent) | Codebase-specific guardrails, architecture context, contributor workflow |

### Quick start (key change — uvx from repo, not PyPI)

```bash
# Run directly from GitHub (PyPI listing coming soon)
uvx --from git+https://github.com/miztertea/goldfish goldfish init

# Or install as a persistent tool
uv tool install git+https://github.com/miztertea/goldfish
goldfish init
```

### Platform support section

> Tested on a clean install of **Ubuntu 26.04 LTS**. Expected to work on other Linux distributions and macOS — not yet verified. Windows is out of scope for v1.

### Obsidian treatment

One sentence at the end of the Vault section: *"Want a visual graph of the knowledge store? See [docs/obsidian.md](docs/obsidian.md)."* Not mentioned elsewhere.

### Badges

```
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](pyproject.toml)
[![Platform: Linux](https://img.shields.io/badge/platform-linux-lightgrey.svg)]()
```

---

## CLAUDE.md (trimmed to ~80 lines of Layer 3 content)

Layer 3 content only — sits above the maintained blocks. No tool API signatures.

```
# CLAUDE.md

## What this is
[2 lines: goldfish is an orchestration layer (~500 lines Python) that installs and
connects GitNexus, OMEGA, and Semble. It does not build search, embeddings, or graphs.]

## Module map
[table: filename → one-sentence job]

## Non-negotiable constraints
[4 bullets: no search/embedding/graph code; no always-on processes;
hooks <10ms; GitNexus via npm only, never bundle]

## Hook event routing
[synchronous/async table — unchanged from current]

## Testing approach
[4 bullets: boundaries only; stub subprocess + OMEGA API; no live installs;
~100 tests ~0.3s]

## Docs
Architecture → docs/architecture.md
Five failures → docs/five-failures.md
Tool selection → docs/tool-selection.md
Design decisions → docs/design-decisions.md

---
[Layer 2: goldfish coordination block — maintained by goldfish]
[Layer 1: GitNexus block — maintained by gitnexus]
```

The five failures framework, tool stack table, vault layout, frontmatter schema, and further notes all move to their appropriate docs/ files and are removed from CLAUDE.md.

---

## AGENTS.md (full rewrite — Layer 3 agent constitution)

Sits above the GitNexus managed block. References maintained sections rather than repeating their content.

```
# AGENTS.md

## What you're working in
[1 paragraph: goldfish is an orchestration layer, ~500 lines Python, 9 modules.
Every function is a subprocess call, a file write, or a config read. No algorithms.]

## The five failures (your contribution guardrail)
[table — every change must map to at least one failure; if it doesn't, don't build it]

## Non-negotiable constraints
[same 4 as CLAUDE.md]

## Superpowers workflow (required for all contributors)
Before any feature: invoke brainstorming skill
Before implementation: invoke writing-plans skill
All features: use test-driven-development skill
Before completing: invoke verification-before-completion skill
Independent tasks: use dispatching-parallel-agents skill

For all code exploration, use the tools in the maintained sections below — not grep or bash.

## What goldfish contributes (don't rebuild this)
[9-item list: init wizard, coordination CLAUDE.md block, event processing,
queue decoupling, vault writes, prompt enrichment fan-out, manifest tracking,
wake-up context generation, new vs existing project distinction]

## Further reading
docs/architecture.md — system architecture and runtime flows
docs/five-failures.md — the framework in detail
docs/tool-selection.md — why each tool was chosen
CONTRIBUTING.md — dev setup and PR process

---
[Layer 1: GitNexus managed block — tool-specific instructions live here]
```

---

## CONTRIBUTING.md (new, human-focused)

```
# Contributing to goldfish

## Prerequisites
[Python 3.13+, Node.js 18+, uv]

## Dev setup
git clone https://github.com/miztertea/goldfish
cd goldfish
uv sync
uv run pytest          # ~100 tests, ~0.3s, no live installs needed

## Running tests
uv run pytest -v
uv run goldfish --help  # run CLI from source

## Project structure
[brief module map pointing to CLAUDE.md for detail]

## Code style
No comments unless the WHY is non-obvious. No docstrings.
Tests at module boundaries — input/output assertions, not internal calls.
Stub subprocess calls and the OMEGA API in tests.

## PR process
[standard: branch, tests pass, description covers the why]

## AI agents contributing
See AGENTS.md for the agent constitution, superpowers workflow, and goldfish-specific guardrails.
```

---

## SECURITY.md (new)

```
# Security

## Scope
goldfish is a local CLI orchestration tool. It does not handle user authentication,
store credentials, transmit data over the network, or run as a server.

The primary security surface is the hook integration: goldfish registers shell
commands that Claude Code executes on lifecycle events. A compromised goldfish
binary or malicious CLAUDE.md could execute arbitrary commands.

## Responsible disclosure
Report security issues via GitHub's private vulnerability reporting:
https://github.com/miztertea/goldfish/security/advisories/new

Please do not open public issues for security vulnerabilities.

## What's in scope
- Dependency vulnerabilities in goldfish's own dependencies
- Hook command injection via malformed event payloads
- Vault path traversal
- Any scenario where goldfish could be used to escalate privileges

## What's out of scope
- Vulnerabilities in GitNexus, OMEGA, or Semble themselves (report to their maintainers)
- Issues requiring physical access to the machine
```

---

## LICENSE

MIT. Create `/LICENSE` with the standard MIT text, year 2026, author Thomas Hawes.

---

## DESIGN-COMPANION.MD → OMEGA Seeding

The DESIGN-COMPANION is structured design session history — the right format for OMEGA's episodic memory, not for a docs/ file.

**What gets seeded:** Part 12 (decisions table, ~15 rows) and Part 13 (eliminated tools, ~15 entries). Each row becomes one `omega_store(content=..., event_type="decision")` call.

**What stays as docs:** A condensed `docs/design-decisions.md` containing only the decisions table (Part 12) — the durable human-readable record.

**What gets archived:** The full DESIGN-COMPANION.MD moves to `docs/internal/DESIGN-COMPANION.MD`. PRD.md moves to `docs/internal/PRD.md`.

**Seeding approach:** Implementation plan includes a step to call omega_store for each decision. This can be done manually via MCP tool calls in a single session — no script needed.

---

## Layer 2 Block Optimization — `init.py` `_CLAUDE_MD_BLOCK`

The current block lists per-tool API signatures that duplicate Layer 1 content already maintained by each tool's own block. The optimized version focuses purely on Layer 2 coordination: what each layer knows, when to query all three, and where to find usage specifics.

**Optimized `_CLAUDE_MD_BLOCK`:**

```
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
```

This block works coherently in any project goldfish is installed in. The tool blocks below it supply the specific call signatures and examples — no duplication.

---

## pyproject.toml additions

```toml
[project.urls]
Homepage = "https://github.com/miztertea/goldfish"
Repository = "https://github.com/miztertea/goldfish"
```

---

## Out of scope for this task

- CI/CD pipeline and GitHub Actions — addressed separately
- Automated installation testing — addressed separately
- PyPI listing — addressed when ready
- Changelog / release notes — addressed with first formal release
- Windows support — v1 is Linux/macOS only
