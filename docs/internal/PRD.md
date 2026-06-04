> **Archived.** This is the original design specification. Current architecture reference: [docs/architecture.md](../architecture.md), [docs/five-failures.md](../five-failures.md), [docs/tool-selection.md](../tool-selection.md).

---

# Goldfish — Product Requirements Document

**Status:** Final · **Version:** 2.0 · **Date:** May 2026

---

## Executive Summary

Goldfish is an agent knowledge operating system for Claude Code — a thin orchestration layer that selects, installs, and wires together a curated set of best-in-class open-source tools to give AI agents persistent, structured, and searchable memory across every session.

**The central principle:** Goldfish is an Ansible playbook, not an application. It does not build memory engines, search indexes, or knowledge graphs. Those problems are already solved by people smarter than us. goldfishh selects the right tools, installs them via their official methods, configures them to communicate, and routes Claude Code lifecycle events between them. Its code is ~400–600 lines of Python. Every function is either a subprocess call, a file write, or a config read.

**The five context failures it solves:**

```
1. Session amnesia     — agent starts blank every session
2. Codebase blindness  — agent doesn't know the shape of the code
3. Decision blindness  — agent doesn't know why things are built this way
4. Impact blindness    — agent doesn't know what breaks when it changes something
5. Prompt deafness     — agent gets generic context, not prompt-specific context
```

**Installed in one command. Zero cloud. Zero always-on services. Fully offline.**

---

## Problem Statement

Claude Code agents are stateless. Every new session starts from zero. A developer using Claude Code daily loses 10–30 minutes per session re-explaining context that was already established. Agents repeat mistakes. They violate decisions already committed to. They ask questions already answered. They change a function without knowing 47 other functions depended on it.

The tools to solve each of these problems exist in the open-source ecosystem. No single tool solves all five failures. No wiring layer connects them into a coherent system. That is the gap goldfishh fills.

A secondary problem is auditability. Whatever an agent learns is locked inside opaque binary formats or in-process state. A developer cannot open it, read it, or audit it. goldfishh writes all accumulated knowledge to a folder of plain markdown files — readable with `cat`, searchable with `grep`, versionable with `git`, and optionally visualized as a graph in Obsidian.

---

## Solution

goldfishh is installed with `uvx goldfishh init`. An interactive wizard detects and installs each dependency via its official method, registers Claude Code hooks globally, scaffolds a per-project vault, and writes the CLAUDE.md agent instructions. After init, the developer works in Claude Code normally. Everything else is invisible.

**The chain of record:**

```
Claude Code JSONL logs          ← source of truth (immutable, append-only)
        ↓ mined by
OMEGA SQLite                    ← episodic memory (decisions, lessons, errors)
        ↓ written by goldfishh
~/.goldfishh/vaults/{project}/  ← markdown vault (human-readable knowledge graph)
        ↑ indexed by
GitNexus LadybugDB              ← code knowledge graph (per-project, in .gitnexus/)
        ↑ searched by
Semble                          ← semantic code + vault search
        ↑ decomposed by
Chonkie                         ← prompt sentence chunking
```

**What each tool owns:**

```
GitNexus  → codebase blindness + impact blindness
            code graph, clusters, processes, blast radius
            auto-installs hooks, skills, CLAUDE.md block
            npx gitnexus analyze (one command, zero config)

OMEGA     → session amnesia
            episodic memory across sessions, SQLite, local

vault     → decision blindness (the conversational layer)
            plain markdown files, temporal frontmatter
            human-readable, Obsidian-viewable, grep-searchable

Semble    → prompt deafness (code + vault retrieval)
            semantic search over code (default) and vault (--content docs)

Chonkie   → prompt deafness (decomposition)
            splits complex multi-topic prompts into discrete search queries

goldfishh → thin orchestrator
            init wizard, event queue, event routing, vault file writes
            wake-up context, prompt enrichment fan-out
```

---

## Approaches Considered

Three approaches were evaluated in depth before the current design.

**Approach A — Fork mempalace-rs**
Rewrite MemPalace in Rust, add Obsidian sync and SurrealDB as the graph backend. Full control, highest performance. Eliminated because: expensive to maintain against upstream changes, SurrealDB is always-on, and the fork bet means perpetual catch-up against fast-moving tooling.

**Approach B — Companion proxy**
A proxy MCP server sitting between Claude and MemPalace, mirroring writes to Obsidian. Cleaner than a fork, but still depends on MemPalace/ChromaDB. Obsidian becomes a mirror, not the interface. Eliminated: fragile coupling, wrong data ownership.

**Approach C — Orchestration layer (selected)**
Treat every specialized tool as a black-box component. goldfishh is only the wiring. Each component is maintained by its own team. goldfishh inherits improvements automatically. The tool never needs to be a memory engine because it never is one.

**On the knowledge graph question:**
Graphiti (Zep) was evaluated for temporal knowledge graphs. It requires Neo4j or FalkorDB (Docker). FalkorDB Lite support in Graphiti is an unmerged GitHub issue. KuzuDB (the only embedded option) was archived in October 2025. Obsidian vault + YAML frontmatter temporal fields cover the same expressiveness for our use case — zero operational overhead, fully local.

**On code intelligence:**
Semble alone covers semantic code search. GitNexus was initially dismissed based on a misidentified fork (abhigyanpatwari/GitNexus is the real repo — 38.7k stars, 265 releases, enterprise backing at akonlabs.com). Once correctly identified: GitNexus uses `npx gitnexus analyze` (no Docker, MCP over stdio, index stored in `.gitnexus/` inside the repo). It covers codebase blindness and impact blindness completely, with auto-installed Claude Code hooks, SKILL.md files per functional community, and CLAUDE.md instructions. It uses LadybugDB (an embedded graph database, the evolution of KuzuDB) — no server required.

---

## Core Design Principles

These are not preferences. Violating any of them changes what the product is.

**Ansible playbook, not an application.** goldfishh selects tools and wires them. It does not build search, embeddings, graphs, or memory. Every problem that can be solved by an existing tool must be solved by that tool.

**No always-on processes.** Every dependency (OMEGA's SQLite, Semble's file index, the event queue, vault markdown files) is opened, used, and closed. GitNexus's MCP server is stdio — Claude Code starts it on demand. No daemons, no Docker containers, no cron jobs.

**Event-driven, not polling.** All synchronization is triggered by Claude Code hook events. No timers, no file watchers.

**Queue-decoupled.** Hook handlers write to a JSONL queue and exit immediately. Claude's execution is never blocked by downstream processing.

**One vault per project.** Project identity is `cwd`. Claude Code organizes JSONL transcripts at `~/.claude/projects/{encoded-cwd}/`. goldfishh mirrors this: one vault at `~/.goldfishh/vaults/{project-name}/`. No cross-project context. No filtering needed.

**Single source of truth.** The JSONL transcripts are the canonical record. All other stores are derived indices. `goldfishh replay` rebuilds everything from the JSONL source.

**Official install methods only.** goldfishh never bundles a dependency. It calls `npm install -g gitnexus`, `uv tool install semble`, `pip install omega-memory`. Each tool is installed and updated through its own official channel.

**Obsidian is optional.** The vault is a folder of plain markdown files. Obsidian provides a beautiful visual graph if the developer has it installed, but nothing in the pipeline requires it. Zero plugins. Zero API keys. Just open the folder.

---

## The Five Failures Framework

This framework drives every tool selection and every implementation decision. Each tool must map to at least one failure. Tools that don't solve a failure are not included.

```
┌─────────────────────┬──────────────────────────────┬──────────────┐
│ Context Failure     │ Symptom                      │ Tool         │
├─────────────────────┼──────────────────────────────┼──────────────┤
│ 1. Session amnesia  │ "We discussed this last week" │ OMEGA        │
│                     │ "You already fixed that bug"  │              │
├─────────────────────┼──────────────────────────────┼──────────────┤
│ 2. Codebase         │ 15 tool calls to find one fn  │ GitNexus     │
│    blindness        │ Missing a module entirely     │              │
├─────────────────────┼──────────────────────────────┼──────────────┤
│ 3. Decision         │ "I'll use Redis for sessions" │ OMEGA        │
│    blindness        │ (we decided against that)     │ + vault      │
├─────────────────────┼──────────────────────────────┼──────────────┤
│ 4. Impact           │ Changes verify_jwt()          │ GitNexus     │
│    blindness        │ breaks 4 callers silently     │              │
├─────────────────────┼──────────────────────────────┼──────────────┤
│ 5. Prompt           │ "Fix the auth bug" →          │ Chonkie      │
│    deafness         │ agent searches from zero      │ + Semble     │
│                     │                               │ + OMEGA      │
└─────────────────────┴──────────────────────────────┴──────────────┘
```

---

## Tool Selection

### Selection Framework

Every candidate tool must clear six gates. Fail any gate, eliminated regardless of capability.

```
Gate 1 — NECESSITY       Solves one of the five failures, better than existing?
Gate 2 — LOCAL FIRST     No cloud, no API keys, no data leaving the machine
Gate 3 — NO ALWAYS-ON    No daemon, no server, no Docker
Gate 4 — INSTALL SIMPLE  uvx / npm / brew / single binary. One command.
Gate 5 — NO OVERLAP      Doesn't duplicate a tool already selected
Gate 6 — MAINTAINABLE    Not a one-person 3-star repo. Active. MIT or Apache.
```

### Selected Tools

**GitNexus** (github.com/abhigyanpatwari/GitNexus)
```
Failure solved: Codebase blindness + Impact blindness
Local:          LadybugDB embedded graph, .gitnexus/ in repo, no cloud
No always-on:   MCP via stdio, started on demand by Claude Code
Install:        npm install -g gitnexus → npx gitnexus analyze
Overlap:        None — structural graph analysis not covered elsewhere
Maintained:     38.7k stars, 265 releases, v1.6.5, enterprise backing
License:        PolyForm Noncommercial (personal/non-commercial use is fine,
                do not bundle, install via npm)
```
One command (`npx gitnexus analyze`) indexes the codebase, installs Claude Code hooks (PreToolUse + PostToolUse), writes CLAUDE.md/AGENTS.md blocks, installs agent skills in `.claude/skills/gitnexus/`, and generates repo-specific SKILL.md per functional community via Leiden clustering. Provides: `query` (hybrid BM25+semantic+RRF), `context` (360° symbol view), `impact` (blast radius with depth + confidence), `detect_changes` (pre-commit), `rename` (multi-file). 14 languages.

**OMEGA** (omega-memory)
```
Failure solved: Session amnesia + Decision blindness (conversational layer)
Local:          SQLite, ONNX, no cloud
No always-on:   Opens and closes
Install:        pip install omega-memory
Overlap:        None — episodic memory exclusively
Maintained:     Apache 2.0, active, 95.4% LongMemEval
```

**Semble** (MinishLab/semble)
```
Failure solved: Prompt deafness (retrieval layer)
Local:          Model2Vec (potion-code-16M) + BM25, CPU only, no API
No always-on:   CLI, exits
Install:        uv tool install semble
Overlap:        GitNexus does structural search; Semble does semantic search.
                Complementary: different search modalities, different indexes.
                Also covers vault search via --content docs over markdown files.
Maintained:     MIT, MinishLab
```

**Chonkie** (chonkie-inc/chonkie)
```
Failure solved: Prompt deafness (decomposition layer)
Local:          Pure Python, no model download for SentenceChunker
No always-on:   Library call
Install:        pip install chonkie (already inside Semble)
Overlap:        Already a transitive Semble dependency — zero marginal cost
Maintained:     MIT, chonkie-inc
```

### Explicitly Eliminated Tools

**Graphiti/Zep** — requires running server (Neo4j or FalkorDB). FalkorDB Lite integration unmerged. Eliminated: violates no-always-on.

**MemPalace** — OMEGA covers the episodic memory need. MemPalace uses ChromaDB. Eliminated: overlap + heavier dependency.

**SurrealDB** — always-on server. Eliminated: violates no-always-on.

**Obsidian Local REST API plugin** — required for Obsidian-as-search. Eliminated: vault search covered by `semble --content docs`. Obsidian is now an optional viewer only.

**Cymbal** — structurally correct for blast radius, but 1 star, 1 contributor. Eliminated: violates maintainability gate. GitNexus fills this slot with production trust.

**Sverklo** — overlaps OMEGA (memory) + Semble (semantic search) + GitNexus (structural). Good tool, wrong fit. Eliminated: overlap.

**tree-sitter-analyzer** — 30 stars, solo contributor. Eliminated: maintainability gate. GitNexus covers structural analysis.

---

## System Architecture

### Component Map

```
┌──────────────────────────────────────────────────────────┐
│                     CLAUDE CODE                          │
│           27 hook events, global settings.json           │
└────────────────────────┬─────────────────────────────────┘
                         │ stdin JSON on every event
              ┌──────────▼──────────┐
              │   goldfishh hook    │  fast: append to queue, exit
              └──────────┬──────────┘
                         │
              ~/.goldfishh/queue.jsonl   append-only, atomic
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

### What Goldfish's Code Actually Is

```
cli.py          ← typer CLI: init, hook, status, doctor, replay
init.py         ← wizard: detects, installs, configures all tools
hook.py         ← reads stdin, appends to queue.jsonl, exits (<5ms)
drain.py        ← processes queue: subprocess calls + omega API + file writes
vault.py        ← pathlib file writes only, no other dependencies
claude_md.py    ← writes/appends CLAUDE.md block + settings.json hooks
config.py       ← reads/writes ~/.goldfishh/config.toml
```

Total: ~400–600 lines of Python. No algorithms. No models. No search. Every function is a subprocess call, a file write, or a config read.

### Vault Structure Per Project

```
~/.goldfishh/vaults/my-project/
├── .manifest.toml          ← sync state: JSONL offset, bootstrap status
├── Memory/
│   ├── Decisions/          ← OMEGA-derived: why choices were made
│   ├── Lessons/            ← OMEGA-derived: what worked and what didn't
│   ├── Errors/             ← OMEGA-derived: bugs found and fixed
│   └── Checkpoints/        ← session snapshots before compaction
├── Specs/                  ← human + agent authored ADRs, specs
├── Tasks/                  ← one note per task, linked to sessions
└── _context/               ← ephemeral: wake-up.md written each session
```

Note: Code/ directory removed. GitNexus owns code intelligence via its own `.gitnexus/` index inside the project directory. No duplication.

### Temporal Metadata on Every Memory Note

```yaml
---
id: decision-jwt-auth-2026-03-01
type: decision
valid_from: 2026-03-01
superseded_by: null
confidence: 0.94
source_session: abc123
source_offset: 48291
related:
  - "[[Specs/auth-spec]]"
---
```

Enrichment excludes notes where `superseded_by` is non-null. Old notes are never deleted — set `superseded_by` and move on. Historical accuracy preserved at zero cost.

### Project Identity

Project identity is `cwd`. Claude Code organizes transcripts at `~/.claude/projects/{encoded-cwd}/` where encoding is `/Users/dev/my-project` → `-Users-dev-my-project`. goldfishh mirrors this. Vault lives at `~/.goldfishh/vaults/{Path(cwd).name}/`. GitNexus index lives at `{cwd}/.gitnexus/`. No scanning, no discovery — everything is deterministic from `cwd`.

---

## Runtime Flows

### Flow 1 — SessionStart (new project, first time)

```
Claude Code launches from /Users/dev/my-project
        ↓
goldfishh hook fires: .manifest.toml absent → NEW PROJECT
        ↓
subprocess: npx gitnexus analyze
  → indexes code into .gitnexus/
  → installs PreToolUse + PostToolUse hooks
  → writes .claude/skills/gitnexus/ skills
  → updates CLAUDE.md
        ↓
subprocess: semble index ./src   (~250ms, code search ready)
omega.mine(jsonl_dir)            (async background)
        ↓
vault.write("_context/wake-up.md",
  "⚠️ First session. Code + structural search ready.
   Memory index building in background.
   Context improves as session progresses.")
        ↓
stdout: wake-up.md path → injected as Claude context
```

### Flow 2 — SessionStart (existing project)

```
.manifest.toml exists → EXISTING PROJECT
  last_byte_offset: 48291
  last_jsonl_file:  abc123.jsonl
        ↓
omega.mine(new bytes from offset)    (~5ms for normal gap)
semble reindex changed files          (changed since manifest.semble_indexed_at)
        ↓
omega.query("current project state") → wake-up content
vault.write("_context/wake-up.md",
  current open tasks, recent decisions, active files)
        ↓
stdout: full context, no warning
Total: ~50-200ms
```

### Flow 3 — UserPromptSubmit (synchronous enrichment)

```
Developer types:
  "fix the auth middleware and the JWT rotation policy,
   also the CI tests are broken and Sarah mentioned
   something about the rate limiter"
        ↓
Chonkie.SentenceChunker(prompt) →
  chunk_1: "fix auth middleware JWT rotation policy"
  chunk_2: "CI tests broken"
  chunk_3: "Sarah rate limiter"
        ↓
Parallel fan-out per chunk:
  semble search chunk ./src              → code hits
  semble search chunk vault --content docs → vault hits
  omega.query(chunk)                     → memory hits
        ↓
Collect, deduplicate by source path, format
        ↓
stdout: enriched context block → Claude sees it before acting
Total: ~25ms
```

### Flow 4 — PostToolUse / file edit (async)

```
Claude edits src/auth.rs
        ↓
PostToolUse(Write, async:true) → goldfishh appends to queue, exits
Claude continues immediately
        ↓
Next drain cycle picks up FileEdit event:
  subprocess: semble reindex src/auth.rs
  omega.note(file_changed, session_id)
  update manifest.semble_indexed_at
```

### Flow 5 — PreCompact (snapshot before context loss)

```
Claude's context window approaches capacity
        ↓
PreCompact hook fires (Claude waits)
        ↓
omega.flush(session_snapshot)
vault.write("Memory/Checkpoints/{session_id}-{ts}.md",
  frontmatter={valid_from, confidence, source_session},
  body=formatted_session_summary)
        ↓
PreCompact returns → compaction proceeds
        ↓
PostCompact: _context/ refreshed from vault, reinjected into Claude
```

---

## Hook Registration

Registered globally at `~/.claude/settings.json` — fires for every Claude Code session regardless of launcher (terminal, Cursor, Windsurf, CI, subagents, Agent Teams).

```
Synchronous (Claude waits):
  SessionStart       → goldfishh hook  (bootstrap or catchup + wake-up)
  UserPromptSubmit   → goldfishh hook  (enrichment → stdout)
  PreCompact         → goldfishh hook  (session snapshot)

Async (Claude does not wait, async: true):
  PostToolUse(Write|Edit)           → goldfishh hook (reindex)
  PostToolUse(Bash(git commit*))    → goldfishh hook (checkpoint)
  SubagentStop                      → goldfishh hook (flush agent memory)
  TaskCreated                       → goldfishh hook (scaffold task note)
  TaskCompleted                     → goldfishh hook (mark done)
  Stop                              → goldfishh hook (full session flush)
  SessionEnd                        → goldfishh hook (cleanup _context/)

GitNexus registers its own hooks during gitnexus analyze:
  PreToolUse         → gitnexus hook  (enrich searches with graph context)
  PostToolUse        → gitnexus hook  (detect stale index after commits)
```

---

## Init Wizard Flow

```
goldfishh init

── Checking dependencies ─────────────────────────────────
✓ uv found
✓ Node.js found (required for GitNexus)
? npm install -g gitnexus → installing... ✓
? uv tool install semble  → installing... ✓
? pip install omega-memory → installing... ✓

── Configuring GitNexus ──────────────────────────────────
Running: npx gitnexus analyze
  ✓ Code graph indexed
  ✓ Claude Code hooks registered
  ✓ Agent skills installed
  ✓ CLAUDE.md updated

── Configuring OMEGA ─────────────────────────────────────
Running: omega setup
  ✓ MCP server registered
  ✓ CLAUDE.md block appended

── Configuring vault ─────────────────────────────────────
Vault location: ~/.goldfishh/vaults/my-project/ [Enter to confirm]
  ✓ Vault scaffolded
  ✓ .manifest.toml written

── Optional: Obsidian visualization ──────────────────────
Want a visual graph of your agent's knowledge? (free at obsidian.md)
Open ~/.goldfishh/vaults/my-project/ as an Obsidian vault.
No plugins needed. No API key. Just open the folder.
[Enter to continue]

── Done ──────────────────────────────────────────────────
goldfishh is ready. Launch Claude Code to begin.
```

---

## The CLAUDE.md Active Layer

goldfishh appends this block to `.claude/CLAUDE.md` (GitNexus writes its own block; these are additive):

```markdown
## Agent Knowledge Tools (managed by goldfishh)

### Before any non-trivial task — query all three layers:

#### Code + Impact Intelligence — GitNexus (MCP)
query({query})                         # semantic + structural search
context({name})                        # 360° view of any symbol
impact({target, direction:"upstream"}) # blast radius before ANY change
detect_changes({scope:"all"})          # pre-commit impact check

#### Episodic Memory — OMEGA (MCP)
omega_query("why did we choose JWT")   # past decisions
omega_query("rate limiter bug")        # known issues
omega_query("Sarah rate limiter")      # person + topic references

#### Semantic Search — Semble (MCP)
semble_search(query, path=./src)                           # code by meaning
semble_search(query, path=~/.goldfishh/vaults/X, content=docs)  # vault notes

### Mandatory workflow before refactoring:
1. gitnexus context({name})  → understand the symbol
2. gitnexus impact({target}) → know what breaks
3. omega_query(topic)        → check past decisions
4. Then act.
```

---

## Module Definitions

Each module is a deep module: significant functionality behind a simple, stable interface.

**cli.py** — Entry point for all user-facing commands: `init`, `hook`, `process`, `status`, `doctor`, `replay`. Owns startup, argument parsing, config loading, and exit codes.

**init.py** — Interactive setup wizard. Detects Node.js and npm. Installs GitNexus, Semble, OMEGA via their official methods. Runs `npx gitnexus analyze` and `omega setup`. Scaffolds vault. Appends CLAUDE.md blocks. Writes MCP registrations. Idempotent.

**hook.py** — Receives Claude Code event JSON on stdin. Appends to `queue.jsonl`. Exits. For `UserPromptSubmit` only: calls the prompt enricher synchronously before returning.

**drain.py** — Reads queue with time budget (default 200ms). Routes by event type. Calls subprocess tools or OMEGA API. Writes vault files. Updates manifest. Handles partial drain gracefully.

**vault.py** — Pure `pathlib` file operations. `write_note(path, frontmatter, body)`, `read_note(path)`, `scaffold(structure)`. No network. No dependencies beyond stdlib. Owns the YAML frontmatter schema.

**claude_md.py** — Reads and surgically appends/updates CLAUDE.md. Reads and updates `~/.claude/settings.json`. Never overwrites. Always appends or updates in-place.

**config.py** — Reads and writes `~/.goldfishh/config.toml`. Provides defaults. Owns the manifest read/write for per-project state (`last_byte_offset`, `bootstrap_complete`, etc.).

---

## User Stories

### Installation

1. As a developer, I want to run `uvx goldfishh init` from my project directory and have a wizard guide me through the full setup, so I don't have to read documentation.
2. As a developer, I want the wizard to detect which dependencies are already installed and only prompt about missing ones, so that setup is as short as possible.
3. As a developer, I want GitNexus installed via `npm install -g gitnexus` and OMEGA via `pip install omega-memory`, so that each tool is maintained through its own official channel.
4. As a developer, I want `npx gitnexus analyze` to run automatically during init, so that code intelligence is ready from my first session.
5. As a developer, I want init to be idempotent, so that running it again verifies health rather than overwriting working configuration.
6. As a developer, I want the wizard to tell me I can open my vault folder in Obsidian for a visual graph, without requiring me to install any plugins or provide an API key.

### Session Context

7. As a developer, I want every Claude Code session to start with a wake-up context note summarizing current tasks, recent decisions, and active files, so I don't have to re-explain project state.
8. As a developer starting a new project, I want code search and structural analysis to be ready immediately even while episodic memory is still indexing, so the first session is useful from the first prompt.
9. As a developer, I want the agent's context note to tell me when memory indexing is still in progress for a new project, so I understand why historical context may be thin early on.

### Prompt Enrichment

10. As a developer, I want multi-topic prompts like "fix the auth bug and also CI is broken" to surface context for each topic independently, so complex prompts get complete enrichment.
11. As a developer, I want short conversational prompts like "yes" and "do that" to skip enrichment entirely, so quick follow-ups are not slowed down.
12. As a developer, I want prompt enrichment to search code semantically (Semble), search vault notes (Semble --content docs), and search episodic memory (OMEGA) in parallel, so context arrives from all three layers before Claude acts.

### Code Intelligence (via GitNexus)

13. As a developer, I want to call `gitnexus impact({target})` and receive a structured list of every upstream caller with depth and confidence scores, so I understand blast radius before any refactor.
14. As a developer, I want GitNexus to generate a SKILL.md file for each functional community in my codebase, so my agent arrives at any module with targeted context about its structure.
15. As a developer, I want `gitnexus query` to use hybrid BM25 + semantic + RRF search over my code graph, so code search is both keyword-precise and semantically aware.
16. As a developer, I want `gitnexus detect_changes` to map my staged git changes to affected processes before a commit, so I know what I'm actually shipping.

### Episodic Memory (via OMEGA)

17. As a developer, I want every git commit during a Claude session to create an episodic snapshot in OMEGA, so I have an auditable timeline of what was built and when.
18. As a developer, I want session state captured before context compaction, so accumulated session knowledge is never lost to context compression.
19. As a developer, I want OMEGA to surface past decisions in response to natural language queries like "why did we choose JWT over sessions", so the agent arrives at decisions with full historical context.

### Vault as Knowledge Graph

20. As a developer, I want to open my vault folder in Obsidian and see a graph view of decisions linked to specs and tasks, without installing any plugins or providing any API key.
21. As a developer, I want each memory note to display clearly when it was created and whether it has been superseded, so I can tell at a glance whether information is current.
22. As a developer, I want vault files to be plain markdown readable with `cat` and searchable with `grep`, so I can inspect the agent's knowledge without any tooling.
23. As a developer, I want to place handwritten spec files in `Specs/` and have them automatically searchable by agents via Semble, so my own documentation is first-class knowledge.

### Operational

24. As a developer, I want `goldfishh status` to show queue depth, last sync time per tool, and bootstrap completion, so I can verify the system is working at any time.
25. As a developer, I want `goldfishh doctor` to check OMEGA health, Semble index freshness, GitNexus index status, queue depth, and hook registration, with specific fix instructions for any failure.
26. As a developer, I want `goldfishh replay` to rebuild my vault from the JSONL source, so I can recover from vault corruption or install goldfishh into a project with existing history.
27. As a developer, I want replay to be resumable, so that replaying a large project's history doesn't restart from the beginning after an interruption.

---

## Implementation Decisions

**The Ansible principle.** Every implementation decision starts with: can an existing tool do this? If yes, call that tool. Only write code for the routing and coordination between tools.

**GitNexus hooks are additive.** GitNexus registers its own PreToolUse and PostToolUse hooks during `gitnexus analyze`. goldfishh registers SessionStart, UserPromptSubmit, PreCompact, Stop, and async PostToolUse for OMEGA-related events. Both hook sets coexist in `~/.claude/settings.json`. No conflict.

**Queue design.** The queue is `~/.goldfishh/queue.jsonl`. Atomic JSONL appends, no locking. Drain processes higher-priority events first (session-lifecycle > tool events > file-change events) within a 200ms budget. Interrupted drains leave remaining lines for the next cycle.

**Prompt decomposition is the only logic goldfishh writes.** Chonkie's `SentenceChunker` decomposes multi-topic prompts into discrete queries. This is routing logic, not search logic. Each chunk is passed to existing tool CLIs.

**Vault writes are pathlib only.** The Obsidian bridge is 30 lines of `pathlib.Path.write_text()` with YAML frontmatter rendering. No HTTP client. No plugin. No API key. Obsidian watches the directory and picks up changes automatically.

**Manifest per project.** `.manifest.toml` inside each vault tracks `last_byte_offset`, `last_jsonl_file`, `bootstrap_complete`, and `semble_indexed_at`. The manifest drives the new-vs-existing branch at SessionStart.

**GitNexus license compliance.** GitNexus uses PolyForm Noncommercial. goldfishh installs it via `npm install -g gitnexus` — the user installs it from the official npm registry. goldfishh does not bundle, redistribute, or include GitNexus source. This is compliant with PolyForm Noncommercial for personal/non-commercial use.

**Node.js is a required runtime.** GitNexus requires Node.js. The init wizard checks for Node.js before proceeding and directs the user to nodejs.org if absent. This is the only non-Python runtime dependency.

---

## Testing Decisions

Tests verify external behavior at module boundaries, not internal implementation. A good test provides a hook event payload as input and asserts on vault file state, queue file state, or subprocess call records. A bad test asserts that a specific internal function was called.

Tests run without live tool installations by stubbing subprocess calls and the OMEGA API.

**hook.py:** Given any event payload on stdin, queue.jsonl gains exactly one line. Given a UserPromptSubmit payload below the word threshold, stdout is empty and the queue gains one line.

**drain.py:** Given five queued events and a 200ms budget that allows three, two remain after drain in priority order. Given a drain interrupted mid-write, remaining lines survive uncorrupted.

**vault.py:** Given a decision payload, the correct file appears at the correct path with all required frontmatter fields. Given a note with `superseded_by` set, Semble search excludes it (verified by not writing it to a path Semble indexes).

**config.py / manifest:** Given no manifest, `is_new_project()` returns true. Given a manifest with an offset, `get_sync_state()` returns the correct value. Given a completed drain, the manifest offset advances correctly.

**init.py:** Given all dependencies installed, init completes without error. Given Node.js absent, init reports the gap with install instructions before touching any files. Given an existing configuration, re-running init reports health without overwriting.

**claude_md.py:** Given an existing CLAUDE.md, the goldfishh block is appended without modifying existing content. Given a second init run, the block is updated in place rather than duplicated.

---

## Out of Scope

- Multi-user or team-shared vaults. Single-developer, local-first only.
- Windows support in v1. macOS and Linux only.
- Any tool that requires a running server process. No Graphiti, Neo4j, FalkorDB, SurrealDB.
- Bidirectional sync (Obsidian edits flowing back into OMEGA). Vault is a derived index.
- Cross-project wikilinks or knowledge reuse across repositories.
- Integration with non-Claude Code agents (Codex, Gemini CLI, Cursor agents).
- Automatic ingestion of external documentation. `External/` populated manually.
- A GUI installer. Init wizard is terminal-only.
- Plugin or extension APIs for third parties.
- Any custom search, embedding, or graph code. Always use the tool.
- Bundling GitNexus or any other dependency. Always install via official methods.

---

## Further Notes

**On the MinishLab ecosystem.** Semble, Model2Vec, and Chonkie are all from MinishLab or closely related teams. Semble uses Chonkie internally for code-aware file chunking, and Model2Vec for embeddings. goldfishh uses Chonkie for prompt decomposition. This means prompt chunks and indexed code chunks share an embedding space — semantic similarity between them is meaningful and coherent. This coherence is inherited for free.

**On GitNexus and the graph database.** GitNexus uses LadybugDB (the production evolution of KuzuDB — rebranded after KuzuDB was archived). It is an embedded graph database with vector support, running entirely inside the `.gitnexus/` directory. No server. No configuration. This resolves the graph database question that led us to consider Graphiti/Neo4j — we get a real property graph without any operational overhead.

**On the vault's role.** The vault stores the conversational and decision layer — things humans said, decisions made in sessions, lessons learned from errors. GitNexus stores the structural layer — what the code does, how it's connected, what breaks what. These are genuinely different knowledge types. Both are needed. Neither replaces the other.

**On what goldfishh actually contributes.** The five tools (GitNexus, OMEGA, Semble, Chonkie, Obsidian) each solve one or two of the five failures independently. What none of them do is: run a wizard that installs all of them, write the CLAUDE.md that explains all of them together, process the 27 Claude Code lifecycle events that should trigger each of them, maintain the queue that decouples those events from blocking Claude, write the vault notes that connect OMEGA memory to human-readable markdown, and enrich prompts by fanning out to all three search layers simultaneously. That is what goldfishh does. It is modest work. It is the right work.
