# Repo Public-Ready Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the goldfishh repo for public consumption — clean docs structure, hero README, proper contributor files, MIT license, OMEGA seeded with design history.

**Architecture:** Approach B decompose — internal design docs extracted into purpose-built docs/ files and archived; CLAUDE.md trimmed to Layer 3 operational content; AGENTS.md rewritten as agent constitution; _CLAUDE_MD_BLOCK in init.py optimized to Layer 2 coordination only.

**Tech Stack:** Python (uv), git, GitHub markdown, OMEGA MCP tool, existing goldfishh source unchanged except `src/goldfishh/init.py:25-49`

---

## Three-layer model (governs all content decisions)

- **Layer 1** — Tool-native maintained blocks: GitNexus `<!-- gitnexus:start/end -->`, OMEGA global `~/.claude/CLAUDE.md`, Semble `.claude/agents/semble-search.md`. **Never touch these.**
- **Layer 2** — Goldfish coordination block: `GOLDFISH_SENTINEL` in `claude_md.py`, written from `_CLAUDE_MD_BLOCK` in `init.py`. Project-agnostic. **Edit only the string in init.py.**
- **Layer 3** — Project-specific hand-authored content: sits **above** maintained blocks. **This is what we're writing.**

Rule: authored content = WHY and WHAT; maintained blocks = HOW. No tool API signatures in authored content.

**Correct block order in CLAUDE.md** (current file has Layer 2 and 1 swapped — fix in Task 13):
```
[Layer 3: authored operational content]
[Layer 2: goldfishh coordination block]   ← ## Agent Knowledge Tools (managed by goldfishh)
[Layer 1: GitNexus block]                ← <!-- gitnexus:start --> ... <!-- gitnexus:end -->
```

---

## File map

| Action | File |
|--------|------|
| Create | `assets/goldfishh-logo.png` (move from root) |
| Create | `docs/internal/` directory |
| Create | `docs/internal/PRD.md` (move) |
| Create | `docs/internal/DESIGN-COMPANION.MD` (move) |
| Create | `LICENSE` |
| Modify | `pyproject.toml` — add `[project.urls]` |
| Create | `docs/architecture.md` |
| Create | `docs/five-failures.md` |
| Create | `docs/tool-selection.md` |
| Create | `docs/design-decisions.md` |
| Create | `docs/obsidian.md` |
| Modify | `src/goldfishh/init.py:25-49` — `_CLAUDE_MD_BLOCK` string only |
| Rewrite | `CLAUDE.md` — Layer 3 authored (~80 lines) + new Layer 2 + Layer 1 preserved |
| Rewrite | `AGENTS.md` — Layer 3 agent constitution above existing Layer 1 GitNexus block |
| Rewrite | `README.md` |
| Create | `CONTRIBUTING.md` |
| Create | `SECURITY.md` |
| Delete | `PRD.md` (root — moved to docs/internal/) |
| Delete | `DESIGN-COMPANION.MD` (root — moved to docs/internal/) |
| Delete | `goldfishh-logo.png` (root — moved to assets/) |

---

### Task 1: Pull logo from remote and stage in assets/

**Files:**
- Create: `assets/goldfishh-logo.png`
- Delete: `goldfishh-logo.png` (root)

- [ ] **Step 1: Fetch logo from remote without disturbing local changes**

```bash
git fetch origin
git checkout origin/main -- goldfishh-logo.png
```

Expected: `goldfishh-logo.png` appears at repo root.

- [ ] **Step 2: Create assets/ and move logo**

```bash
mkdir -p assets
mv goldfishh-logo.png assets/goldfishh-logo.png
```

- [ ] **Step 3: Verify**

```bash
ls assets/goldfishh-logo.png
```

Expected: file exists, non-zero size.

- [ ] **Step 4: Commit**

```bash
git add assets/goldfishh-logo.png
git commit -m "chore: add assets/ directory with goldfishh logo"
```

---

### Task 2: Create docs/internal/ and copy internal docs

**Files:**
- Create: `docs/internal/PRD.md`
- Create: `docs/internal/DESIGN-COMPANION.MD`

Note: We copy (not move) here. The originals stay at root until after OMEGA seeding in Task 10, then get deleted in Task 11.

- [ ] **Step 1: Create docs/internal/**

```bash
mkdir -p docs/internal
```

- [ ] **Step 2: Copy internal docs**

```bash
cp PRD.md docs/internal/PRD.md
cp DESIGN-COMPANION.MD docs/internal/DESIGN-COMPANION.MD
```

- [ ] **Step 3: Add a notice at the top of each archived file**

Prepend to `docs/internal/PRD.md`:
```markdown
> **Archived.** This is the original design specification. Current architecture reference: [docs/architecture.md](../architecture.md), [docs/five-failures.md](../five-failures.md), [docs/tool-selection.md](../tool-selection.md).

---

```

Prepend to `docs/internal/DESIGN-COMPANION.MD`:
```markdown
> **Archived.** This is the original design session narrative. Design decisions extracted to [docs/design-decisions.md](../design-decisions.md) and seeded into OMEGA episodic memory.

---

```

- [ ] **Step 4: Commit**

```bash
git add docs/internal/
git commit -m "docs: archive PRD and DESIGN-COMPANION to docs/internal/"
```

---

### Task 3: Create LICENSE

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: Write LICENSE**

Create `/home/tchawes/goldfishh/LICENSE` with this exact content:

```
MIT License

Copyright (c) 2026 Thomas Hawes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
git add LICENSE
git commit -m "chore: add MIT license"
```

---

### Task 4: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add project.urls section**

In `pyproject.toml`, after the `[project]` table, add:

```toml
[project.urls]
Homepage = "https://github.com/miztertea/goldfishh"
Repository = "https://github.com/miztertea/goldfishh"
```

- [ ] **Step 2: Verify file is valid TOML**

```bash
uv run python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add project URLs to pyproject.toml"
```

---

### Task 5: Create docs/architecture.md

**Files:**
- Create: `docs/architecture.md`

Draws from PRD.md sections: System Architecture, Runtime Flows, Hook Registration, Module Definitions, Project Identity.

- [ ] **Step 1: Write docs/architecture.md**

```markdown
# Architecture

goldfishh is an orchestration layer (~500 lines of Python). Every function is a subprocess call, a file write, or a config read. It does not build search, embeddings, or graphs.

## Component map

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

## Modules

| File | Responsibility |
|------|---------------|
| `cli.py` | Typer CLI: init, hook, drain, register-hooks, status, doctor, replay, mine |
| `init.py` | Setup wizard: detects/installs deps, scaffolds vault, registers hooks |
| `hook.py` | Reads stdin event → appends to queue.jsonl; enriches UserPromptSubmit synchronously |
| `drain.py` | Time-budgeted queue processor: routes events to subprocess/OMEGA API/file writes |
| `enricher.py` | Chonkie decompose → Semble + OMEGA fan-out per prompt chunk |
| `vault.py` | pathlib-only file writes: write_note(), read_note(), scaffold() |
| `claude_md.py` | Upserts goldfishh block in CLAUDE.md; registers hooks in settings.json |
| `config.py` | Reads/writes ~/.goldfishh/config.toml and per-project .manifest.toml |
| `miner.py` | Replays historical JSONL sessions through OMEGA's own hooks |

## Three-layer agent instruction model

goldfishh installs agent instructions at three layers. Understanding the layers prevents duplication and drift:

| Layer | Maintained by | Where | Content |
|-------|--------------|-------|---------|
| Layer 1 — Tool-native | GitNexus, OMEGA, Semble | `<!-- gitnexus:start/end -->` in project files; `~/.claude/CLAUDE.md` for OMEGA; `.claude/agents/semble-search.md` | Each tool's specific MCP tool signatures and usage examples |
| Layer 2 — Coordination | goldfishh (`init.py` → `claude_md.py`) | `## Agent Knowledge Tools (managed by goldfishh)` sentinel | Cross-tool orchestration: query all three layers before acting |
| Layer 3 — Project-specific | Human or agent | Above maintained blocks in `CLAUDE.md` and `AGENTS.md` | Codebase-specific guardrails, module map, contributor workflow |

Rule: Layer 3 and 2 authored content says WHY and WHAT. Layer 1 blocks say HOW.

## Project identity and vault location

Project identity = `cwd`. This mirrors how Claude Code organizes its own JSONL transcripts at `~/.claude/projects/{encoded-cwd}/`.

Vault location: `~/.goldfishh/vaults/{Path(cwd).name}/`  
GitNexus index: `{cwd}/.gitnexus/`  
Queue: `~/.goldfishh/queue.jsonl`

No scanning, no discovery — everything is deterministic from `cwd`.

## Vault structure

```
~/.goldfishh/vaults/{project}/
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
  SessionStart       → goldfishh hook  (bootstrap or catchup + wake-up)
  UserPromptSubmit   → goldfishh hook  (enrichment → stdout)
  PreCompact         → goldfishh hook  (session snapshot)

Async (Claude does not wait):
  PostToolUse        → goldfishh hook  (registered so GitNexus hooks coexist)
  SubagentStop       → goldfishh hook
  TaskCreated        → goldfishh hook
  TaskCompleted      → goldfishh hook
  Stop               → goldfishh hook
  SessionEnd         → goldfishh hook

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
goldfishh hook: .manifest.toml absent → NEW PROJECT
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
```

- [ ] **Step 2: Verify file was created**

```bash
wc -l docs/architecture.md
```

Expected: 100+ lines

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture.md from PRD system architecture sections"
```

---

### Task 6: Create docs/five-failures.md

**Files:**
- Create: `docs/five-failures.md`

- [ ] **Step 1: Write docs/five-failures.md**

```markdown
# The Five Failures Framework

Every AI agent context failure maps to one of exactly five problems. This framework drives every tool selection and implementation decision in goldfishh. A feature that doesn't address at least one failure doesn't belong in the project.

## The five failures

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

## How each failure is addressed

**Session amnesia → OMEGA**  
OMEGA is a local SQLite + ONNX episodic memory store. It mines Claude Code JSONL transcripts and surfaces past decisions, known issues, and prior context via natural language queries. It achieves 95.4% recall on LongMemEval. No cloud, no daemon, no API key.

**Codebase blindness → GitNexus**  
GitNexus indexes the codebase into LadybugDB (an embedded graph database) via `npx gitnexus analyze`. It provides hybrid BM25+semantic search, 360° symbol context (callers, callees, execution flows), and functional community detection. Query by concept, not by filename.

**Decision blindness → OMEGA + vault**  
OMEGA captures session decisions automatically. goldfishh writes structured vault notes (plain markdown with temporal frontmatter) for architectural decisions, lessons, and errors. Vault notes are searchable by Semble and human-readable without tooling.

**Impact blindness → GitNexus**  
GitNexus `impact()` maps every upstream caller of a symbol with depth grouping and confidence scores. `detect_changes()` maps staged git changes to affected execution flows before a commit. An agent cannot change code without knowing the blast radius.

**Prompt deafness → Chonkie + Semble + OMEGA**  
Chonkie's `SentenceChunker` decomposes multi-topic prompts into discrete queries. Each chunk fans out to Semble (code search), Semble with `--include-text-files` (vault search), and OMEGA (memory search) in parallel. Results arrive before Claude processes the prompt.

## Using the framework as a contributor

Before building any feature, map it to a failure:

1. Which of the five failures does this address?
2. Is there already a tool in the stack that addresses it?
3. If yes: wire to that tool, don't rebuild it.
4. If no: evaluate new tools against the [six selection gates](tool-selection.md#selection-gates).

If a feature doesn't map to any failure — don't build it.
```

- [ ] **Step 2: Commit**

```bash
git add docs/five-failures.md
git commit -m "docs: add five-failures.md standalone reference"
```

---

### Task 7: Create docs/tool-selection.md

**Files:**
- Create: `docs/tool-selection.md`

- [ ] **Step 1: Write docs/tool-selection.md**

```markdown
# Tool Selection

## Selection gates

Every candidate tool must clear all six gates. Fail any gate → eliminated regardless of capability.

```
Gate 1 — NECESSITY       Solves one of the five failures, better than existing?
Gate 2 — LOCAL FIRST     No cloud, no API keys, no data leaving the machine
Gate 3 — NO ALWAYS-ON    No daemon, no server, no Docker
Gate 4 — INSTALL SIMPLE  uvx / npm / brew / single binary. One command.
Gate 5 — NO OVERLAP      Doesn't duplicate a tool already selected
Gate 6 — MAINTAINABLE    Not a one-person 3-star repo. Active. MIT or Apache.
```

## Selected tools

### GitNexus

```
Failures solved: Codebase blindness + Impact blindness
Local:          LadybugDB embedded graph, .gitnexus/ in repo, no cloud
No always-on:   MCP via stdio, started on demand by Claude Code
Install:        npm install -g gitnexus → npx gitnexus analyze
Overlap:        None — structural graph analysis not covered elsewhere
Maintained:     38.7k stars, 265 releases, enterprise backing
License:        PolyForm Noncommercial (personal/non-commercial: install via npm only, never bundle)
```

One command (`npx gitnexus analyze`) indexes the codebase, installs Claude Code hooks, writes CLAUDE.md/AGENTS.md blocks, installs skills, and generates per-community SKILL.md files.

### OMEGA

```
Failures solved: Session amnesia + Decision blindness (conversational layer)
Local:          SQLite, ONNX, no cloud
No always-on:   Opens and closes
Install:        uv tool install "omega-memory[server]" → omega setup --client claude-code
Overlap:        None — episodic memory exclusively
Maintained:     Apache 2.0, active, 95.4% LongMemEval
```

### Semble

```
Failures solved: Prompt deafness (retrieval layer)
Local:          Model2Vec (potion-code-16M) + BM25, CPU only, no API
No always-on:   CLI, exits
Install:        uv tool install semble → claude mcp add semble
Overlap:        GitNexus does structural search; Semble does semantic search. Complementary.
                Also covers vault search via --include-text-files over markdown files.
Maintained:     MIT, MinishLab
```

### Chonkie

```
Failures solved: Prompt deafness (decomposition layer)
Local:          Pure Python, no model download for SentenceChunker
No always-on:   Library call
Install:        Already a transitive Semble dependency — zero marginal cost
Overlap:        None — decomposition before fan-out
Maintained:     MIT, chonkie-inc
```

## Eliminated tools

| Tool | Reason eliminated |
|------|-----------------|
| MemPalace | ChromaDB always-on; OMEGA is superior and overlaps |
| SurrealDB | Always-on server — violates no-always-on gate |
| Graphiti/Zep | Requires Neo4j or FalkorDB server |
| KuzuDB | Archived October 2025, crash reports |
| FalkorDB Lite (in Graphiti) | Unmerged GitHub issue at time of evaluation |
| Obsidian REST API plugin | Eliminated when `semble --include-text-files` was discovered — no vault search plugin needed |
| goldfish_search (custom) | Eliminated when `semble --include-text-files` was discovered |
| spaCy | Chonkie SentenceChunker covers prompt decomposition without a separate NER pipeline |
| SmolLM2-135M | 500ms–3s on CPU — too slow for synchronous UserPromptSubmit hook |
| Model2Vec directly | Already inside Semble and Chonkie — no direct use needed |
| Cymbal | 1 star, 1 contributor, v0.8 — violates maintainability gate |
| Sverklo | Overlaps OMEGA + Semble + GitNexus; good tool, wrong fit for goldfishh |
| tree-sitter-analyzer | 30 stars, solo contributor — GitNexus fills this slot |
| Arbor | Install path unclear, not on PyPI cleanly — GitNexus fills this slot |
| scantool | Less capable than GitNexus for blast radius |
| GitNexus via Docker | Docker is optional; CLI via npm is the right mode for goldfishh |

## The MinishLab coherence note

Semble, Model2Vec, and Chonkie are from closely related teams. They share an embedding space — prompt chunks decomposed by Chonkie and code chunks indexed by Semble are semantically comparable. This coherence is inherited for free by composing these tools.
```

- [ ] **Step 2: Commit**

```bash
git add docs/tool-selection.md
git commit -m "docs: add tool-selection.md with gates and evaluation record"
```

---

### Task 8: Create docs/design-decisions.md

**Files:**
- Create: `docs/design-decisions.md`

Condensed from DESIGN-COMPANION.MD Part 12 (decisions table only — no narrative).

- [ ] **Step 1: Write docs/design-decisions.md**

```markdown
# Design Decisions

The durable record of significant decisions made during goldfishh's design phase.
Full narrative context is archived in [docs/internal/DESIGN-COMPANION.MD](internal/DESIGN-COMPANION.MD).
Each decision is also stored in OMEGA episodic memory and queryable via `omega query`.

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Memory engine | OMEGA | MemPalace | OMEGA has no always-on dependency (ChromaDB); SQLite + ONNX |
| Temporal knowledge graph | Obsidian vault + frontmatter `valid_from`/`superseded_by` | Graphiti/Neo4j | No server required; same expressiveness for our use case |
| Embedded graph DB | GitNexus LadybugDB | SurrealDB, KuzuDB (archived) | Embedded, no server, production-grade, ships with GitNexus |
| Code search | Semble | Custom embedding search | Already built, 1.5ms query, MinishLab team maintains it |
| Prompt decomposition | Chonkie SentenceChunker | Custom NLP, spaCy, SmolLM2 | Already inside Semble as transitive dep; <1ms; no model needed |
| Vault search | Semble `--include-text-files` | Obsidian REST API plugin, custom goldfish_search module | Already in Semble; zero marginal cost; plugin eliminated |
| Obsidian role | Optional viewer only | Required service with REST API | Plugin eliminated; pure `pathlib.write_text()` is sufficient |
| Project isolation | Per-project vault | Single shared vault | No cross-project context bleeding |
| Project identity | `cwd` = identity | Config file | Mirrors Claude Code's own JSONL organization scheme |
| Structural analysis | GitNexus | Cymbal, Arbor, scantool, tree-sitter-analyzer | 38.7k stars, correct architecture, covers two failures |
| Architecture style | Ansible playbook (thin orchestrator) | Custom search/graph/memory code | Don't build what already exists; inherit improvements automatically |
| GitNexus license compliance | Install via `npm install -g gitnexus` | Bundle or redistribute | PolyForm Noncommercial: install from official npm only |
| MCP registration | GitNexus + OMEGA + Semble | Obsidian MCP plugin | Vault search covered by Semble; Obsidian plugin eliminated |
| Event queue format | JSONL append-only | SQLite, Redis | Zero dependencies; atomic appends; human-readable; no locking needed |
```

- [ ] **Step 2: Commit**

```bash
git add docs/design-decisions.md
git commit -m "docs: add design-decisions.md condensed from DESIGN-COMPANION Part 12"
```

---

### Task 9: Create docs/obsidian.md

**Files:**
- Create: `docs/obsidian.md`

- [ ] **Step 1: Write docs/obsidian.md**

```markdown
# Obsidian — Optional Vault Viewer

goldfishh writes your agent's knowledge to plain markdown files in `~/.goldfishh/vaults/{project}/`. You can read these with `cat`, search them with `grep`, and version them with `git`.

If you have [Obsidian](https://obsidian.md) installed, you can also open the vault folder for a visual graph view. This is entirely optional — goldfishh works identically whether Obsidian is open, closed, or not installed.

## How to open the vault in Obsidian

1. Install Obsidian from [obsidian.md](https://obsidian.md) (free)
2. Open Obsidian → **Open folder as vault**
3. Select `~/.goldfishh/vaults/{your-project-name}/`
4. That's it

No plugins. No API key. No configuration.

## What you'll see

Vault notes contain `[[wikilinks]]` in the `related:` frontmatter field. Obsidian renders these as graph edges in the **Graph View** (`Ctrl+G`). You'll see decisions linked to specs, tasks linked to sessions, and lessons linked to errors.

The `_context/wake-up.md` file is regenerated every session — it's the most recently written note and shows what goldfishh briefed Claude at the start of the last session.

## Notes on superseded content

Notes that have been superseded set `superseded_by: <id>` in their frontmatter. These notes remain in the vault (they're historical record) but Semble excludes them from search results. In Obsidian they're still visible — useful for understanding how a decision evolved.

## No bidirectional sync

The vault is a **derived index** — it's generated from Claude Code JSONL transcripts and OMEGA memory. Editing vault files in Obsidian will not update OMEGA. If you want to add a spec or decision manually, create a new note in `Specs/` or `Memory/Decisions/` — Semble will index it automatically.
```

- [ ] **Step 2: Commit**

```bash
git add docs/obsidian.md
git commit -m "docs: add obsidian.md optional viewer guide"
```

---

### Task 10: Seed OMEGA with design decisions

**Files:** None (OMEGA MCP calls only)

Seeds OMEGA with decisions from DESIGN-COMPANION Part 12 (decisions table) and Part 13 (eliminated tools). Run these calls via the OMEGA MCP tool in a Claude Code session.

- [ ] **Step 1: Seed Part 12 — architectural decisions**

Call `omega_store` for each row:

```
omega_store("Chose OMEGA over MemPalace for episodic memory: OMEGA uses SQLite+ONNX with no always-on dependency. MemPalace requires ChromaDB (always-on vector DB). OMEGA achieves 95.4% LongMemEval recall.", event_type="decision")

omega_store("Chose Obsidian vault + YAML frontmatter (valid_from/superseded_by) over Graphiti/Neo4j for temporal knowledge graph: no server required, same expressiveness for goldfishh use case, zero operational overhead.", event_type="decision")

omega_store("GitNexus uses LadybugDB (embedded graph DB, production evolution of KuzuDB). No server. No Docker. Files in .gitnexus/. This resolved the graph DB question — we get a real property graph without operational overhead.", event_type="decision")

omega_store("Chose Semble over custom embedding search for code search: already built, 1.5ms query time, maintained by MinishLab, uses Model2Vec+BM25 with RRF fusion. Zero code to write.", event_type="decision")

omega_store("Chose Chonkie SentenceChunker over custom NLP/spaCy/SmolLM2 for prompt decomposition: already a transitive dependency of Semble, <1ms per chunk, no model download needed.", event_type="decision")

omega_store("Chose Semble --include-text-files for vault search instead of Obsidian REST API plugin or custom goldfish_search module: already in Semble, zero marginal cost, plugin requirement eliminated.", event_type="decision")

omega_store("Obsidian role: optional viewer only, not a required service. goldfishh writes plain markdown files with pathlib. Obsidian watches the directory and picks up changes. No plugins, no API key, no REST client needed.", event_type="decision")

omega_store("Per-project vault isolation: one vault per project, identity = cwd. Mirrors Claude Code's own JSONL organization (~/.claude/projects/{encoded-cwd}/). No cross-project context bleeding.", event_type="decision")

omega_store("Project identity = cwd (not a config file). This is deterministic and mirrors how Claude Code organizes its own session transcripts. Vault at ~/.goldfishh/vaults/{Path(cwd).name}/.", event_type="decision")

omega_store("Chose GitNexus (38.7k stars, 265 releases, enterprise backing) over Cymbal (1 star, 1 contributor), Arbor (unclear install), scantool (less capable), tree-sitter-analyzer (30 stars solo) for structural analysis. GitNexus covers codebase blindness + impact blindness with npx gitnexus analyze.", event_type="decision")

omega_store("Architecture: goldfishh is an Ansible playbook, not an application. It selects tools and wires them. Never builds search, embeddings, graphs, or memory engines. Every function is a subprocess call, file write, or config read.", event_type="decision")

omega_store("GitNexus license compliance: PolyForm Noncommercial. goldfishh installs it via npm install -g gitnexus (official npm channel). Never bundles, redistributes, or includes GitNexus source. Personal/non-commercial use is compliant.", event_type="decision")

omega_store("MCP registration: GitNexus + OMEGA + Semble registered as MCP servers. Obsidian MCP plugin was considered but eliminated when Semble --include-text-files was discovered for vault search.", event_type="decision")

omega_store("Event queue format: JSONL append-only at ~/.goldfishh/queue.jsonl. Chosen over SQLite (dependency) and Redis (always-on server). Atomic appends, no locking, human-readable, zero dependencies.", event_type="decision")
```

- [ ] **Step 2: Seed Part 13 — eliminated tools**

```
omega_store("Eliminated MemPalace: ChromaDB always-on vector DB required. OMEGA is superior and covers the same use case without a daemon.", event_type="decision")

omega_store("Eliminated SurrealDB: always-on server process required. Violates goldfishh no-always-on constraint.", event_type="decision")

omega_store("Eliminated Graphiti/Zep: requires Neo4j or FalkorDB running as a server. FalkorDB Lite embedded option was an unmerged GitHub issue at evaluation time.", event_type="decision")

omega_store("Eliminated KuzuDB: archived October 2025 with crash reports. LadybugDB (in GitNexus) is the production evolution of KuzuDB.", event_type="decision")

omega_store("Eliminated Obsidian Local REST API plugin: required for Obsidian-as-search. Plugin eliminated when Semble --include-text-files was discovered. Obsidian is now optional viewer only.", event_type="decision")

omega_store("Eliminated custom goldfish_search module (Model2Vec+BM25): planned but eliminated when Semble --include-text-files was discovered. Semble already does this.", event_type="decision")

omega_store("Eliminated spaCy for NER in prompt processing: Chonkie SentenceChunker covers the use case without a separate pipeline or model.", event_type="decision")

omega_store("Eliminated SmolLM2-135M for query extraction: 10-50 tokens/sec on CPU = 500ms-3s latency. Too slow for synchronous UserPromptSubmit hook which must return in <10ms.", event_type="decision")

omega_store("Eliminated Model2Vec directly: already inside Semble and Chonkie as a dependency. No need to call it directly.", event_type="decision")

omega_store("Eliminated Cymbal (blast radius tool): structurally correct design but 1 star, 1 contributor, v0.8. Too early-stage for a critical dependency. GitNexus fills this slot.", event_type="decision")

omega_store("Eliminated Sverklo: overlaps OMEGA (memory) + Semble (semantic search) + GitNexus (structural). Good tool, wrong fit — too much overlap with already-selected tools.", event_type="decision")

omega_store("Eliminated tree-sitter-analyzer: 30 stars, solo contributor. Violates maintainability gate. GitNexus fills the structural analysis slot.", event_type="decision")

omega_store("Eliminated Arbor: install path unclear, not on PyPI cleanly. GitNexus fills the blast-radius slot.", event_type="decision")

omega_store("Eliminated scantool: less capable than GitNexus for blast radius. Could be a fallback but GitNexus covers the full need.", event_type="decision")

omega_store("Eliminated GitNexus via Docker: Docker is optional and violates the no-always-on principle. CLI via npm install -g gitnexus is the right mode for goldfishh.", event_type="decision")
```

- [ ] **Step 3: Verify seeding worked**

Query OMEGA to confirm:

```
omega_call(tool="omega_query", args={"query": "why did we choose OMEGA over MemPalace"})
```

Expected: returns the MemPalace decision memory.

- [ ] **Step 4: No commit needed** (OMEGA is external storage)

---

### Task 11: Remove root-level internal docs

**Files:**
- Delete: `PRD.md` (root)
- Delete: `DESIGN-COMPANION.MD` (root)

- [ ] **Step 1: Remove root-level copies**

```bash
git rm PRD.md DESIGN-COMPANION.MD
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove PRD.md and DESIGN-COMPANION.MD from root (moved to docs/internal/)"
```

---

### Task 12: Optimize _CLAUDE_MD_BLOCK in init.py

**Files:**
- Modify: `src/goldfishh/init.py:25-49`

Replaces per-tool API signatures (Layer 1 content) with pure coordination content (Layer 2).

- [ ] **Step 1: Replace _CLAUDE_MD_BLOCK**

In `src/goldfishh/init.py`, replace lines 25–49:

```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

goldfishh wires together three intelligence layers. Query all three before any non-trivial task.

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
"""
```

- [ ] **Step 2: Run tests to confirm no breakage**

```bash
uv run pytest tests/test_claude_md.py tests/test_init.py -v
```

Expected: all pass. The tests check the sentinel presence (`GOLDFISH_SENTINEL`), not the block body.

- [ ] **Step 3: Commit**

```bash
git add src/goldfishh/init.py
git commit -m "refactor: optimize _CLAUDE_MD_BLOCK to Layer 2 coordination only — remove per-tool API signatures"
```

---

### Task 13: Rewrite CLAUDE.md

**Files:**
- Rewrite: `CLAUDE.md`

Replaces the current bloated content. Correct layer order: Layer 3 authored → Layer 2 goldfishh block → Layer 1 GitNexus block.

Note: the current file has Layer 2 and Layer 1 in reversed order (goldfishh block appears after GitNexus block). This task fixes the ordering.

- [ ] **Step 1: Write CLAUDE.md**

The complete file content (the Layer 1 GitNexus block is copied verbatim from the current file lines 112–154):

```markdown
# CLAUDE.md

## What this is

goldfishh is an orchestration layer (~500 lines of Python) that installs and wires together GitNexus, OMEGA, and Semble. It does not build search, embeddings, or graphs — those problems are solved by dedicated tools. Every function is a subprocess call, a file write, or a config read.

## Module map

| File | Responsibility |
|------|---------------|
| `cli.py` | Typer CLI: init, hook, drain, register-hooks, status, doctor, replay, mine |
| `init.py` | Setup wizard: detects/installs deps, scaffolds vault, registers hooks |
| `hook.py` | Reads stdin event → appends to queue.jsonl; enriches UserPromptSubmit synchronously |
| `drain.py` | Time-budgeted queue processor: routes events to subprocess/OMEGA API/file writes |
| `enricher.py` | Chonkie decompose → Semble + OMEGA fan-out per prompt chunk |
| `vault.py` | pathlib-only file writes: write_note(), read_note(), scaffold() |
| `claude_md.py` | Upserts goldfishh block in CLAUDE.md; registers hooks in settings.json |
| `config.py` | Reads/writes ~/.goldfishh/config.toml and per-project .manifest.toml |
| `miner.py` | Replays historical JSONL sessions through OMEGA's own hooks |

## Non-negotiable constraints

- **Never write search, embedding, or graph code.** Find the right tool and call it.
- **No always-on processes.** Every tool opens, executes, and closes. No daemons.
- **Hook handlers return in <10ms.** Write to queue.jsonl and exit. Never block Claude.
- **GitNexus is PolyForm Noncommercial.** Install via `npm install -g gitnexus` only. Never bundle.

## Hook event routing

Synchronous (Claude waits for stdout): `SessionStart`, `UserPromptSubmit`, `PreCompact`
Async (`async: true`): `PostToolUse`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `SessionEnd`

goldfishh registers `PostToolUse` so GitNexus hooks coexist cleanly. GitNexus registers its own `PreToolUse` and `PostToolUse` during `gitnexus analyze` — both sets coexist without conflict.

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

## Agent Knowledge Tools (managed by goldfishh)

goldfishh wires together three intelligence layers. Query all three before any non-trivial task.

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

This project is indexed by GitNexus as **goldfishh** (821 symbols, 1034 relationships, 30 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| `gitnexus://repo/goldfishh/context` | Codebase overview, check index freshness |
| `gitnexus://repo/goldfishh/clusters` | All functional areas |
| `gitnexus://repo/goldfishh/processes` | All execution flows |
| `gitnexus://repo/goldfishh/process/{name}` | Step-by-step execution trace |

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
```

- [ ] **Step 2: Verify tests still pass**

```bash
uv run pytest tests/test_claude_md.py -v
```

Expected: all pass (tests check sentinel presence, not block body).

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: trim CLAUDE.md to Layer 3 operational content, fix layer ordering"
```

---

### Task 14: Rewrite AGENTS.md

**Files:**
- Rewrite: `AGENTS.md`

Layer 3 agent constitution above the existing Layer 1 GitNexus block.

- [ ] **Step 1: Write AGENTS.md**

```markdown
# AGENTS.md

This is the agent constitution for goldfishh development. Read this before touching any code.

## What you're working in

goldfishh is an orchestration layer (~500 lines of Python, 9 modules). Every function is a subprocess call, a file write, or a config read. There is no search code, no embedding code, no graph code — those problems are solved by GitNexus, OMEGA, and Semble. goldfishh wires them together.

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

goldfishh uses superpowers skills for all development. When contributing:

- **Before any feature work:** invoke `brainstorming` skill — design before code
- **Before implementation:** invoke `writing-plans` skill — plan before writing
- **All features:** use `test-driven-development` skill — test before implementation
- **Before completing:** invoke `verification-before-completion` skill — verify before claiming done
- **Independent tasks:** use `dispatching-parallel-agents` skill — parallelize when safe

For all code exploration, use the tools in the maintained sections below — not grep or bash.

## What goldfishh contributes (don't rebuild this)

goldfishh does exactly these things and nothing more:

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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **goldfishh** (821 symbols, 1034 relationships, 30 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| `gitnexus://repo/goldfishh/context` | Codebase overview, check index freshness |
| `gitnexus://repo/goldfishh/clusters` | All functional areas |
| `gitnexus://repo/goldfishh/processes` | All execution flows |
| `gitnexus://repo/goldfishh/process/{name}` | Step-by-step execution trace |

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
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: rewrite AGENTS.md as Layer 3 agent constitution with superpowers workflow"
```

---

### Task 15: Rewrite README.md

**Files:**
- Rewrite: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
<p align="center">
  <img src="assets/goldfishh-logo.png" alt="goldfishh — persistent memory for Claude Code" width="280">
</p>

<h1 align="center">goldfishh</h1>

<p align="center">
  <strong>Persistent memory for Claude Code agents.</strong><br>
  One command installs and wires together GitNexus, OMEGA, and Semble so your AI agent<br>
  never starts a session from scratch again.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.13+-blue.svg" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/platform-linux-lightgrey.svg" alt="Platform: Linux">
</p>

---

## Quick start

**Prerequisites:** Python 3.13+, Node.js 18+, [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

```bash
# Run directly from GitHub (PyPI listing coming soon)
uvx --from git+https://github.com/miztertea/goldfishh goldfishh init
```

Or install as a persistent tool:

```bash
uv tool install git+https://github.com/miztertea/goldfishh
goldfishh init
```

The init wizard detects and installs all dependencies, indexes your codebase, scaffolds your memory vault, and registers Claude Code hooks. Re-running is safe — it reports health and skips what's already installed.

If you have prior Claude Code sessions in this project, seed OMEGA with their history:

```bash
goldfishh mine
```

---

## The problem

Claude Code agents are stateless. Every session starts from zero. You spend 10–30 minutes re-explaining context that was established yesterday. The agent repeats mistakes it already made, asks questions already answered, and changes a function without knowing 47 others depend on it.

The tools to fix this exist. Nothing connects them. That's the gap goldfishh fills.

| Failure | Cause | Solution |
|---------|-------|---------|
| Session amnesia | Agent starts blank every session | OMEGA episodic memory mines JSONL logs |
| Codebase blindness | Agent doesn't know the shape of the code | GitNexus code knowledge graph |
| Decision blindness | Agent doesn't know why things are built this way | Vault markdown notes + OMEGA |
| Impact blindness | Agent doesn't know what breaks when it changes something | GitNexus blast-radius analysis |
| Prompt deafness | Agent gets generic context, not prompt-specific context | Chonkie + Semble + OMEGA fan-out |

---

## How it works

goldfishh installs three layers of intelligence into Claude Code — each maintained by a dedicated open-source tool.

| Layer | Installed by | What it provides |
|-------|-------------|-----------------|
| **Layer 1 — Tool-native** | GitNexus, OMEGA, Semble (via `goldfishh init`) | Each tool's own hooks, MCP server, and agent instructions |
| **Layer 2 — Coordination** | goldfishh | A single block telling agents to query all three layers before acting |
| **Layer 3 — Project-specific** | You (or your agent) | Codebase-specific guardrails, architecture context, contributor workflow |

goldfishh itself is ~500 lines of Python — a thin orchestration layer with no search, embedding, or graph code. Every function is a subprocess call, a file write, or a config read.

### How the tools connect

```
Claude Code JSONL logs         ← source of truth
       ↓ mined by OMEGA
SQLite episodic store          ← past decisions, lessons, errors
       ↓ written by goldfishh
~/.goldfishh/vaults/{project}/  ← plain markdown vault (human-readable)
       ↑ indexed by GitNexus
Code knowledge graph           ← symbols, callers, execution flows
       ↑ searched by Semble
Prompt enrichment              ← context injected before every task
       ↑ decomposed by Chonkie
```

### Hook lifecycle

| Event | What happens |
|-------|-------------|
| `SessionStart` | Drains queue, generates wake-up context from vault + OMEGA |
| `UserPromptSubmit` | Decomposes prompt → fans out to Semble (code + vault) + OMEGA → injects context |
| `PreCompact` | Drains queue, writes checkpoint note to vault |
| `TaskCreated` / `TaskCompleted` | Writes task notes to vault |
| `Stop` / `SessionEnd` | Advances JSONL offset in manifest |

All async events write to `~/.goldfishh/queue.jsonl` first and return in <10ms so Claude never blocks.

---

## Vault

All knowledge is plain markdown — readable with `cat`, searchable with `grep`, versionable with `git`.

```
~/.goldfishh/vaults/{project}/
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

Each note uses temporal frontmatter so agents can tell what's current and what's superseded:

```yaml
---
id: decision-jwt-auth-2026-05-24
type: decision
valid_from: 2026-05-24
superseded_by: null
confidence: 0.94
source_session: abc123
---
```

Want a visual graph of the knowledge store? See [docs/obsidian.md](docs/obsidian.md).

---

## CLI reference

```
goldfishh init              Run the setup wizard
goldfishh mine              Seed OMEGA from historical JSONL session logs (run once on onboarding)
goldfishh status            Show queue depth, manifest state, and sync timestamps
goldfishh doctor            Check all dependencies and report with fix instructions
goldfishh register-hooks    Re-register hooks with the correct binary path
goldfishh replay            Rebuild vault from JSONL transcripts (resumable)
goldfishh hook              Handle a hook event from stdin (called by Claude Code)
goldfishh drain             Process queued events from ~/.goldfishh/queue.jsonl
```

---

## Platform support

Tested on a clean install of **Ubuntu 26.04 LTS**. Expected to work on other Linux distributions and macOS — not yet verified. Windows is out of scope for v1.

---

## Development

```bash
git clone https://github.com/miztertea/goldfishh
cd goldfishh
uv sync
uv run pytest
```

Tests stub all subprocess calls and run without live tool installations. ~100 tests, ~0.3s.

```bash
uv run pytest -v          # verbose test output
uv run goldfishh --help    # run CLI from source
```

---

## Contributing

Human contributors: [CONTRIBUTING.md](CONTRIBUTING.md)  
AI agent contributors: [AGENTS.md](AGENTS.md)

---

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 2: Verify hero image path**

```bash
ls assets/goldfishh-logo.png
```

Expected: file exists (from Task 1).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README — hero image, quick start first, three-layer model, platform note"
```

---

### Task 16: Create CONTRIBUTING.md

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Write CONTRIBUTING.md**

```markdown
# Contributing to goldfishh

## Prerequisites

- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Dev setup

```bash
git clone https://github.com/miztertea/goldfishh
cd goldfishh
uv sync
uv run pytest
```

Tests stub all subprocess calls and the OMEGA API. You do not need GitNexus, OMEGA, or Semble installed to run tests. ~100 tests, ~0.3s.

## Running tests

```bash
uv run pytest -v                           # verbose output
uv run pytest tests/test_hook.py -v       # single module
uv run goldfishh --help                    # run CLI from source
```

## Project structure

See [CLAUDE.md](CLAUDE.md) for the module map and operational constraints.  
See [docs/architecture.md](docs/architecture.md) for the full system design and runtime flows.

## Code style

- No comments unless the WHY is non-obvious (a hidden constraint, a subtle invariant, a workaround for a specific bug)
- No docstrings
- Test at module boundaries — input/output assertions, not internal calls
- Stub subprocess calls and the OMEGA API in tests

## PR process

1. Branch from `main`
2. Tests must pass: `uv run pytest`
3. PR description covers the why, not just the what
4. If the change touches architecture or adds a dependency, link to the relevant design doc

## AI agent contributors

If you are an AI agent contributing to goldfishh, read [AGENTS.md](AGENTS.md) first. It contains the agent constitution, superpowers workflow, five failures guardrail, and goldfishh-specific constraints.
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md for human contributors"
```

---

### Task 17: Create SECURITY.md

**Files:**
- Create: `SECURITY.md`

- [ ] **Step 1: Write SECURITY.md**

```markdown
# Security

## Scope

goldfishh is a local CLI orchestration tool. It:
- Does not handle user authentication or store credentials
- Does not transmit data over the network
- Does not run as a server or daemon
- Writes files only to `~/.goldfishh/` and the project directory

The primary security surface is the **hook integration**: goldfishh registers shell commands that Claude Code executes on lifecycle events. A compromised goldfishh binary or malicious `CLAUDE.md` could execute arbitrary commands in your shell.

## Responsible disclosure

Please report security vulnerabilities via GitHub's private vulnerability reporting:

**[github.com/miztertea/goldfishh/security/advisories/new](https://github.com/miztertea/goldfishh/security/advisories/new)**

Do not open public issues for security vulnerabilities.

## What's in scope

- Vulnerabilities in goldfishh's Python dependencies
- Hook command injection via malformed event payloads from stdin
- Vault path traversal (writing outside `~/.goldfishh/vaults/`)
- Any scenario where goldfishh execution could escalate privileges

## What's out of scope

- Vulnerabilities in GitNexus, OMEGA, or Semble — report to their maintainers
- Issues requiring physical access to the machine
- Social engineering

## Response

We aim to acknowledge reports within 48 hours and provide a fix or workaround within 14 days for confirmed issues.
```

- [ ] **Step 2: Commit**

```bash
git add SECURITY.md
git commit -m "docs: add SECURITY.md with responsible disclosure process"
```

---

### Task 18: Final verification

**Files:** None

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass. No regressions from `init.py` change in Task 12.

- [ ] **Step 2: Check all internal links in README**

Verify these paths exist:
```bash
ls assets/goldfishh-logo.png    # hero image
ls docs/obsidian.md            # obsidian link
ls LICENSE                     # license link
ls CONTRIBUTING.md             # contributing link
ls AGENTS.md                   # agents link
```

Expected: all exist.

- [ ] **Step 3: Check all internal links in CLAUDE.md docs table**

```bash
ls docs/architecture.md docs/five-failures.md docs/tool-selection.md docs/design-decisions.md docs/obsidian.md
```

Expected: all exist.

- [ ] **Step 4: Verify CLAUDE.md layer ordering is correct**

```bash
grep -n "gitnexus:start\|gitnexus:end\|managed by goldfishh" CLAUDE.md
```

Expected output (in this order):
```
<line N>:## Agent Knowledge Tools (managed by goldfishh)
<line M>:<!-- gitnexus:start -->
<line P>:<!-- gitnexus:end -->
```

Where N < M < P (goldfishh block before GitNexus block).

- [ ] **Step 5: Verify root is clean**

```bash
ls *.md *.png 2>/dev/null
```

Expected: `README.md CLAUDE.md AGENTS.md CONTRIBUTING.md SECURITY.md` — no PRD.md, DESIGN-COMPANION.MD, or goldfishh-logo.png.

- [ ] **Step 6: Final commit**

```bash
git add -A
git status   # review what's staged — should be empty if each task committed
git log --oneline -20
```

If everything looks clean, optionally create a summary commit:

```bash
git commit -m "chore: repo public-ready — docs restructure, agent constitution, license, contributing files" --allow-empty
```

---

## Self-review notes

**Spec coverage check:**
- ✅ Logo moved to assets/
- ✅ LICENSE created
- ✅ CONTRIBUTING.md created
- ✅ SECURITY.md created
- ✅ pyproject.toml urls added
- ✅ README: Quick Start first, three-layer model, hero image, platform note, correct uvx command, Obsidian → docs/obsidian.md link only
- ✅ AGENTS.md: agent constitution with superpowers workflow, five failures, non-negotiables, what goldfishh contributes
- ✅ CLAUDE.md: trimmed to ~80 lines Layer 3, layer ordering fixed, maintained blocks preserved
- ✅ init.py _CLAUDE_MD_BLOCK: Layer 2 coordination only, no per-tool API signatures
- ✅ docs/architecture.md, five-failures.md, tool-selection.md, design-decisions.md, obsidian.md all created
- ✅ PRD.md + DESIGN-COMPANION.MD archived to docs/internal/ and removed from root
- ✅ OMEGA seeded with Part 12 + Part 13 decisions

**Ordering constraint:** Task 10 (OMEGA seeding) must run before Task 11 (delete root-level DESIGN-COMPANION.MD). All other tasks are independent within their phase.
