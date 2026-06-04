# Instruction Architecture Design

**Date:** 2026-05-25
**Status:** Approved
**Topic:** Four-layer agent instruction stack, session start sequence, memory scope rules, CLAUDE.md vs AGENTS.md split

---

## Problem

goldfishh's instruction surfaces had accumulated structural tensions:

1. Two memory systems (OMEGA, auto-memory files) with no written scope — agents defaulted to OMEGA for everything, auto-memory sat empty
2. Session start ordering conflict — `using-superpowers` skill said "check skills first"; global CLAUDE.md said "call omega_welcome() first"
3. GitNexus block duplicated in both CLAUDE.md and AGENTS.md — only CLAUDE.md gets auto-maintained; AGENTS.md drifts
4. Three-layer model described tools but not MEMORY.md — agents had no model for the zero-latency baseline
5. Layer 2 goldfishh block contained tool API signatures that belong in Layer 1 tool blocks

---

## Design

### The Four-Layer Stack

```
Layer 0   MEMORY.md          Zero-latency static baseline — loads before any tool call
Layer 1   Tool blocks        Tool-maintained instruction blocks (GitNexus, OMEGA, Semble)
Layer 2   Goldfish block     Additive coordination — stack description, session sequence
Layer 3   Project block      Project-specific constitution — constraints, rules, five failures
```

| Layer | Owner | Update mechanism | Edit rule |
|-------|-------|-----------------|-----------|
| 0 — MEMORY.md | Claude Code harness | Write tool, file-based | User prefs, feedback, references only. Never episodic. |
| 1 — Tool blocks | Each tool | Tool CLI (e.g., `gitnexus analyze`) | Never hand-edit. Sentineled blocks. |
| 2 — Goldfish block | goldfishh | `goldfishh init`, version bump | Coordination only. No tool API signatures. |
| 3 — Project block | Project team | Human-maintained | Constraints, five failures, architecture rules. |

### Session Start Sequence

Lower layers load first:

```
1. Layer 0 loads (automatic)     MEMORY.md injected into context by harness — zero action needed
2. Layer 1 activates (tool call) omega_welcome() → omega_protocol()
3. Skills check (superpowers)    Check for applicable skill before any response
4. Work begins
```

**Ordering rule written into Layer 2:** MEMORY.md loads before you can do anything. Call `omega_welcome()` next to get episodic context. Then check for skills. User instructions (global CLAUDE.md) take precedence over skill rules — OMEGA wins the ordering tie because it is a user instruction.

### MEMORY.md Scope

**Write to MEMORY.md (Layer 0):**
- User preferences ("prefer concise responses", "this user is a senior Go dev")
- Behavioral feedback ("don't mock the database — we got burned", "no trailing summaries")
- Reference pointers ("bugs tracked in Linear project INGEST", "oncall dashboard at X")
- Stable project facts ("merge freeze begins date X", "legal requirement drives auth rewrite")

**Write to OMEGA (Layer 1 episodic):**
- Decisions made ("chose X approach for Y problem")
- Lessons learned ("fixed bug Z by doing W")
- Session history and active reminders
- Anything time-stamped and episodic

**Write to neither:**
- Code patterns, file paths, architecture — read the code
- Git history, who changed what — use `git log`
- In-progress task state — use TaskCreate

**Decision test:** "Would this still be true in 6 months without any code changes?" → MEMORY.md. "Did this happen?" → OMEGA. "Is this derivable from the code?" → neither.

### CLAUDE.md vs AGENTS.md

**CLAUDE.md** — Claude Code-specific, owns all four layers:
- Layer 0: implicit (MEMORY.md loads automatically)
- Layer 1: tool blocks with sentinels (`<!-- gitnexus:start/end -->`, etc.) — auto-maintained
- Layer 2: goldfishh block — goldfishh-maintained
- Layer 3: project constitution — human-maintained

**AGENTS.md** — universal agent constitution, owns Layers 2-3 only:
- Layer 2: goldfishh coordination block (identical to CLAUDE.md Layer 2)
- Layer 3: project constitution (five failures, constraints, superpowers workflow)
- Single pointer for Layer 1: *"Tool-specific instructions (GitNexus, OMEGA, Semble) are auto-maintained in CLAUDE.md by each tool."*

No duplication. No drift. Claude Code agents get the full stack from CLAUDE.md. Other agents get Layers 2-3 from AGENTS.md and a pointer for tool blocks.

### Updated Layer 2 Goldfish Block

The `_CLAUDE_MD_BLOCK` written by `goldfishh init` to every user project becomes. The sentinel heading (`## Agent Knowledge Tools (managed by goldfishh)`) stays as-is — it is the match key used by `append_claude_md_block` to find and replace the block:

```
## Agent Knowledge Tools (managed by goldfishh)

## goldfishh — Agent Coordination Layer

goldfishh wires together four layers of agent intelligence. All four activate at session start.

### The Stack

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| 0 — MEMORY.md | Static baseline: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| 1 — Tool blocks | GitNexus (code), OMEGA (episodic), Semble (semantic) — auto-maintained | Call omega_welcome() |
| 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

### Session Start (required)

1. MEMORY.md loads automatically — no action needed
2. Call omega_welcome() → omega_protocol() — activates episodic context
3. Check for applicable skills before any response
4. Work begins

### Before Any Non-Trivial Task

Query all three intelligence tools:
- GitNexus — call graph, blast radius, execution flows
- OMEGA — prior decisions, session history, known issues
- Semble — code by meaning, vault notes

Each tool's full usage instructions are in its own maintained section in this file.

```

---

## What Changes

### In this repo (goldfishh development)

| File | Change |
|------|--------|
| `CLAUDE.md` | Layer 2 section (goldfishh block) updated to describe four-layer stack. Layer 3 (project constitution) separated by a `---` rule and a `<!-- layer 3: project -->` comment so the boundary is visible without being a code sentinel. Layer 1 tool blocks remain tool-maintained and untouched. |
| `AGENTS.md` | Layer boundary markers added (matching CLAUDE.md). GitNexus auto-manages its block in AGENTS.md too — block kept. "Tool-Specific Instructions (Layer 1)" section updated to say blocks are auto-maintained in this file. |
| `src/goldfishh/init.py` | `_CLAUDE_MD_BLOCK` updated to four-layer table + session sequence. No other Python changes. |
| `~/.claude/CLAUDE.md` (global, manual) | User updates their own global CLAUDE.md: session start sequence simplified to defer to the Layer 2 block in each project. goldfishh does NOT write to this file — it is the user's private global config. |

### In every user project (deployed)

| File | Change |
|------|--------|
| `CLAUDE.md` | Layer 2 goldfishh block updated on next `goldfishh init` run (or manual update). |
| `MEMORY.md` | Gets populated — agents now have explicit rules for what belongs there. |

---

## Non-Goals

- This does not change any goldfishh Python code beyond `_CLAUDE_MD_BLOCK` in `init.py`. The sentinel string (`GOLDFISH_SENTINEL`) in `claude_md.py` is unchanged.
- This does not change GitNexus, OMEGA, or Semble — they continue to maintain their own blocks.
- This does not add a goldfishh sync command to mirror tool blocks from CLAUDE.md to AGENTS.md (accepted limitation — AGENTS.md gets a pointer instead).

## Post-Implementation Notes

**GitNexus manages both CLAUDE.md and AGENTS.md.** The original design assumed GitNexus only wrote its block to CLAUDE.md. In practice, `gitnexus analyze` also maintains its block in AGENTS.md. This means AGENTS.md is fully self-contained for any agent framework — no pointer to CLAUDE.md is needed for Layer 1. The layer marker approach was applied to both files identically.

**Global `~/.claude/CLAUDE.md` (manual, optional).** The OMEGA startup rule in the global CLAUDE.md is now reinforced by the Layer 2 goldfishh block in every project. No breaking change. The global rule may be simplified to remove redundancy, but is not required for the system to work correctly.
