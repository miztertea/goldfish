# Layer Tightening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 context-layer problems (GitNexus duplication, memory division ambiguity, session-start ordering, invisible layer boundary, dev docs in agent instructions) across `init.py`, `CLAUDE.md`, and `AGENTS.md`.

**Architecture:** Pure content edits — no Python logic changes, no new functions. Each task is a file edit followed by grep verification. The existing test suite (`pytest`) serves as a regression guard after the `init.py` change.

**Tech Stack:** Python (init.py string constant), Markdown (CLAUDE.md, AGENTS.md), Edit tool for precision replacements, grep for verification.

---

### Task 1: Update `_CLAUDE_MD_BLOCK` in `src/goldfish/init.py`

**Files:**
- Modify: `src/goldfish/init.py:25-52`

This is the source-of-truth for the goldfish Layer 2 block installed into every project's CLAUDE.md. The current version has stale content that predates the 4-layer model and lacks the memory division note, session-start clarification, and Layer 1 handoff line.

- [ ] **Step 1: Replace `_CLAUDE_MD_BLOCK`**

Use the Edit tool. `old_string`:
```
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

goldfish wires together four layers of agent intelligence. All four activate at session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | Static baseline: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — Tool blocks | GitNexus (code), OMEGA (episodic), Semble (semantic) — auto-maintained | On demand (MCP); OMEGA via omega_welcome() |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

### Session Start (required)

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — briefing and recent activity
3. Call `omega_protocol()` — operating instructions
4. Check for applicable skills before any response
5. Work begins

### Before Any Non-Trivial Task

Query all three intelligence tools:
- GitNexus — call graph, blast radius, execution flows
- OMEGA — prior decisions, session history, known issues
- Semble — code by meaning, vault notes

Each tool's full usage instructions are in its own maintained section in this file.
"""
```

`new_string`:
```
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

goldfish wires together four layers of agent intelligence. All four activate at session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — Tool blocks | GitNexus (code graph), OMEGA (episodic memory), Semble (semantic search) | MCP on demand; OMEGA via omega_welcome() |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

**Memory systems:** Layer 0 (MEMORY.md) is static file-based memory — user preferences, feedback, references — loaded automatically. Layer 1 OMEGA is episodic MCP memory — decisions, session history, known issues — requires omega_welcome().

### Session Start (required)

Steps 2–3 are initialization calls, not task responses. The skill-check in step 4 applies to the user's first request.

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — context briefing and recent activity
3. Call `omega_protocol()` — operating rules for this session
4. Check for applicable skills before responding to the user's first request
5. Work begins

### Before Any Non-Trivial Task

Query all three intelligence tools:
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

Each tool's full usage instructions are in its own auto-maintained block below (Layer 1).
"""
```

- [ ] **Step 2: Verify the change looks correct**

```bash
grep -n "Memory systems\|initialization calls\|auto-maintained block below" src/goldfish/init.py
```

Expected output (3 lines):
```
37:| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
42:**Memory systems:** Layer 0 (MEMORY.md) is static file-based memory...
55:Each tool's full usage instructions are in its own auto-maintained block below (Layer 1).
```
(Line numbers approximate — just confirm all three strings appear.)

- [ ] **Step 3: Run existing tests**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/ -q
```

Expected: all tests pass. `_CLAUDE_MD_BLOCK` is a string constant — no test directly asserts its content, but `test_claude_md.py` exercises `append_claude_md_block` which uses `GOLDFISH_SENTINEL`. That sentinel is unchanged so tests must still pass.

- [ ] **Step 4: Commit**

```bash
git add src/goldfish/init.py
git commit -m "fix: update _CLAUDE_MD_BLOCK with memory division, session-start clarification, layer boundary"
```

---

### Task 2: Apply three edits to `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

Three changes in one commit: (A) delete hook routing section, (B) replace stale goldfish block with new content, (C) remove orphaned gitnexus block. All three are in the same file; committing together keeps the file in a consistent state at every commit.

- [ ] **Step 1: Delete the hook routing section (Edit A)**

Use the Edit tool. `old_string`:
```
## Hook event routing

Synchronous (Claude waits for stdout): `SessionStart`, `UserPromptSubmit`, `PreCompact`
Async (`async: true`): `PostToolUse`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `SessionEnd`

goldfish registers `PostToolUse` so GitNexus hooks coexist cleanly. GitNexus registers its own `PreToolUse` and `PostToolUse` during `gitnexus analyze` — both sets coexist without conflict.

## Testing approach
```

`new_string`:
```
## Testing approach
```

- [ ] **Step 2: Replace the stale goldfish block (Edit B)**

Use the Edit tool. `old_string`:
```
<!-- layer 2: goldfish — do not edit, maintained by goldfish init -->

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


---

<!-- layer 1: tool blocks — do not edit, maintained by each tool -->
```

`new_string`:
```
<!-- layer 2: goldfish — do not edit, maintained by goldfish init -->

## Agent Knowledge Tools (managed by goldfish)

goldfish wires together four layers of agent intelligence. All four activate at session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — Tool blocks | GitNexus (code graph), OMEGA (episodic memory), Semble (semantic search) | MCP on demand; OMEGA via omega_welcome() |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

**Memory systems:** Layer 0 (MEMORY.md) is static file-based memory — user preferences, feedback, references — loaded automatically. Layer 1 OMEGA is episodic MCP memory — decisions, session history, known issues — requires omega_welcome().

### Session Start (required)

Steps 2–3 are initialization calls, not task responses. The skill-check in step 4 applies to the user's first request.

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — context briefing and recent activity
3. Call `omega_protocol()` — operating rules for this session
4. Check for applicable skills before responding to the user's first request
5. Work begins

### Before Any Non-Trivial Task

Query all three intelligence tools:
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

Each tool's full usage instructions are in its own auto-maintained block below (Layer 1).

---

<!-- layer 1: tool blocks — do not edit, maintained by each tool -->
```

- [ ] **Step 3: Remove the orphaned gitnexus block (Edit C)**

The orphaned block is everything between `<!-- layer 1: tool blocks -->` and the properly-marked `<!-- gitnexus:start -->` (the second one). Use the Edit tool. `old_string`:
```
<!-- layer 1: tool blocks — do not edit, maintained by each tool -->

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

<!-- gitnexus:start -->
```

`new_string`:
```
<!-- layer 1: tool blocks — do not edit, maintained by each tool -->
<!-- gitnexus:start -->
```

- [ ] **Step 4: Verify CLAUDE.md structure**

```bash
grep -n "gitnexus:start\|gitnexus:end\|Hook event routing\|Memory systems\|initialization calls\|layer 1\|layer 2\|layer 3" CLAUDE.md
```

Expected output — confirm:
- `gitnexus:start` appears exactly once
- `gitnexus:end` appears exactly once
- `Hook event routing` does NOT appear
- `Memory systems` appears once (in Layer 2 block)
- `initialization calls` appears once (in Session Start)
- `layer 1`, `layer 2`, `layer 3` appear as comment markers

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "fix: tighten CLAUDE.md layers — remove hook routing, refresh goldfish block, drop orphaned gitnexus duplicate"
```

---

### Task 3: Fix `AGENTS.md` layer boundary

**Files:**
- Modify: `AGENTS.md`

"What goldfish contributes" and "Further reading" are project-level facts (Layer 3) but currently sit inside the `<!-- layer 2: goldfish -->` block. Move them above the layer 2 marker. The superpowers workflow (goldfish coordination instruction) stays in Layer 2.

- [ ] **Step 1: Restructure AGENTS.md layer boundary**

Use the Edit tool. `old_string`:
```
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
```

`new_string`:
```
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

<!-- layer 2: goldfish — superpowers workflow for contributors -->

## Superpowers workflow (required for all contributors)

goldfish uses superpowers skills for all development. When contributing:

- **Before any feature work:** invoke `brainstorming` skill — design before code
- **Before implementation:** invoke `writing-plans` skill — plan before writing
- **All features:** use `test-driven-development` skill — test before implementation
- **Before completing:** invoke `verification-before-completion` skill — verify before claiming done
- **Independent tasks:** use `dispatching-parallel-agents` skill — parallelize when safe

For all code exploration, use the tools in the maintained sections below — not grep or bash.

---
```

- [ ] **Step 2: Verify AGENTS.md layer boundary**

```bash
grep -n "layer 2\|layer 3\|What goldfish contributes\|Further reading\|Superpowers workflow" AGENTS.md
```

Expected output — confirm `What goldfish contributes` and `Further reading` appear at lower line numbers than `<!-- layer 2:`, and `Superpowers workflow` appears after it:
```
1:  <!-- layer 3: project — maintained by project team -->
~30: ## What goldfish contributes (don't rebuild this)
~44: ## Further reading
~50: ---
~52: <!-- layer 2: goldfish — superpowers workflow for contributors -->
~56: ## Superpowers workflow (required for all contributors)
```
(Line numbers approximate; what matters is the order.)

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "fix: move 'What goldfish contributes' and 'Further reading' to Layer 3 in AGENTS.md"
```

---

### Task 4: Final verification

- [ ] **Step 1: Confirm CLAUDE.md has exactly one gitnexus block**

```bash
grep -c "gitnexus:start" CLAUDE.md
```

Expected: `1`

- [ ] **Step 2: Confirm `_CLAUDE_MD_BLOCK` matches CLAUDE.md goldfish content**

The goldfish block in CLAUDE.md (between the sentinel and `<!-- layer 1:`) must match `_CLAUDE_MD_BLOCK` in `init.py`. Quick check — both should contain "auto-maintained block below (Layer 1)":

```bash
grep "auto-maintained block below" CLAUDE.md src/goldfish/init.py
```

Expected: appears in both files.

- [ ] **Step 3: Run full test suite**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Confirm no "Hook event routing" in CLAUDE.md**

```bash
grep "Hook event routing" CLAUDE.md && echo "FAIL — still present" || echo "PASS — removed"
```

Expected: `PASS — removed`
