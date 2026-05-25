# Memory Diagnostic Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Six Memory Failure Modes framework — a named diagnostic for the agent memory layer — along with 6 instruction fixes, a new `goldfish-diagnostic` skill, and a retrospective skill update that tracks diagnostic trends across sessions.

**Architecture:** Pure text and skill-file changes — no Python logic modified. Two new files created (`docs/memory-diagnostic.md`, `goldfish-diagnostic` skill), two skills modified, three instruction files patched (`goldfish/CLAUDE.md`, `init.py`, `~/.claude/CLAUDE.md`), one stale memory file updated. All changes to the goldfish repo are committed; skill and global config changes are file-only.

**Tech Stack:** Markdown, Python f-string (for `_CLAUDE_MD_BLOCK`), OMEGA CLI (`omega store`)

**Spec:** `docs/superpowers/specs/2026-05-25-memory-diagnostic-framework-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `docs/memory-diagnostic.md` | Six Failure Modes framework doc — the analytical vocabulary |
| Modify | `goldfish/CLAUDE.md` (goldfish block only) | Layer table split, Memory Router, omega_protocol step fix |
| Modify | `src/goldfish/init.py` (`_CLAUDE_MD_BLOCK`) | Mirror all goldfish/CLAUDE.md changes for new installs |
| Modify | `~/.claude/CLAUDE.md` (OMEGA block) | Remove conflicting routing line, fix omega_protocol framing |
| Modify | `~/.claude/projects/-home-tchawes-goldfish/memory/project_goldfish.md` | Fix stale "design phase" claim |
| Create | `~/.claude/skills/goldfish-diagnostic/SKILL.md` | New diagnostic skill |
| Modify | `~/.claude/skills/goldfish-session-retrospective/SKILL.md` | Add Section 4.5 Memory Layer Health |

---

## Task 1: Create `docs/memory-diagnostic.md`

**Files:**
- Create: `docs/memory-diagnostic.md`

- [ ] **Step 1: Write the framework document**

Create `/home/tchawes/goldfish/docs/memory-diagnostic.md` with this exact content:

```markdown
# Six Memory Failure Modes

A diagnostic framework for goldfish's agent memory layer. Sibling to `docs/five-failures.md` — same design language, applied to memory architecture instead of agent context failures.

**Use:** Run `/goldfish-diagnostic` to score each dimension against the current instruction set. Track scores across sessions to measure improvement direction.

---

## The Six Failure Modes

| Failure | Symptom | Diagnostic Question | Remedy Class | Layer Focus |
|---------|---------|--------------------|-----------|----|
| **Routing fog** | Agent asks "which system?" or writes to wrong store | For each memory type, is there exactly one authoritative system? | Add routing decision table | L0/L1 boundary |
| **Dark corner** | Agent re-derives same context each session from scratch | Is every important context type captured by at least one system? | Add coverage entry | Any |
| **Arrival gap** | Agent makes worse early decisions; context arrives after it's needed | Does each memory type land before the first decision it informs? | Promote to earlier layer or system | L0 vs L1 timing |
| **Stale signal** | Agent acts on outdated facts; contradictions between layers | Can outdated memory be detected before it informs a decision? | Add validation cadence | All layers |
| **Boundary blur** | Same content type has two homes; layers bleed into each other | Are layer responsibilities distinct enough that no content type fits two layers? | Write a scope rule | L0–L3 |
| **Instruction fiction** | Agent follows documented behavior that system doesn't exhibit | Does the documented behavior match what the system actually does? | Fix the doc or fix the system | L2/L3 |

---

## Scoring Rubric

- 🟢 **GREEN** — no instances found in current instruction set
- 🟡 **YELLOW** — partial coverage, edge cases, or judgment-dependent gaps
- 🔴 **RED** — structural gap — agents will misroute without correction

---

## Current State Assessment

*Updated by `/goldfish-diagnostic` each time it runs.*

**Last diagnostic:** 2026-05-25

| Failure | Score | Key Evidence |
|---------|-------|-------------|
| Routing fog | 🔴 RED | No routing decision table; user prefs claimed by both auto-memory and OMEGA quick reference |
| Dark corner | 🟡 YELLOW | Tool health state + KPI timeseries have no home |
| Arrival gap | 🟡 YELLOW | `omega_protocol()` framing misleading; CLAUDE.md guaranteed by goldfish init so absence not a real failure |
| Stale signal | 🟡 YELLOW | `project_goldfish.md` stale; no structured validation cadence |
| Boundary blur | 🔴 RED | Layer 0/OMEGA user-pref overlap; vault vs OMEGA scope undefined |
| Instruction fiction | 🔴 RED | `omega_protocol` framing aspirational vs thin free-tier reality; OMEGA labeled "on demand" but required |

**Summary:** 3 RED / 3 YELLOW / 0 GREEN (baseline, 2026-05-25)

---

## Further Reading

- `docs/five-failures.md` — agent context failure modes (the original framework)
- `docs/architecture.md` — runtime flows and layer wiring
- `.claude/skills/goldfish-diagnostic/SKILL.md` — how to run the diagnostic
```

- [ ] **Step 2: Verify the document has all required sections**

```bash
grep -n "Six Failure Modes\|Scoring Rubric\|Current State Assessment\|Further Reading" /home/tchawes/goldfish/docs/memory-diagnostic.md
```

Expected: 4 matches, one per section heading.

- [ ] **Step 3: Commit**

```bash
git -C /home/tchawes/goldfish add docs/memory-diagnostic.md
git -C /home/tchawes/goldfish commit -m "docs: add Six Memory Failure Modes framework document

Sibling to five-failures.md — named diagnostic for the agent memory layer.
Includes 6 failure modes, scoring rubric, and baseline assessment (3 RED / 3 YELLOW).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Fix `goldfish/CLAUDE.md` — layer table + Memory Router + step 3

**Files:**
- Modify: `/home/tchawes/goldfish/CLAUDE.md` (the "Agent Knowledge Tools" section only)

- [ ] **Step 1: Read the current goldfish block to orient**

```bash
grep -n "Layer 0\|Layer 1\|Layer 2\|Layer 3\|omega_protocol\|Memory systems" /home/tchawes/goldfish/CLAUDE.md
```

Expected: lines showing the current 4-row table and session start sequence.

- [ ] **Step 2: Replace the layer table and add Memory Router**

Find and replace the entire block from `goldfish coordinates four layers` through `Layer 0 is static (loads automatically)` with the new content below.

**Old text** (exact match):
```
goldfish coordinates four layers of agent intelligence. All four are available from session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — Tool blocks | GitNexus (code graph), OMEGA (episodic memory), Semble (semantic search) | MCP on demand; OMEGA via omega_welcome() |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

Layer 0 is static (loads automatically); Layer 1 tools are dynamic (called on demand).
```

**New text**:
```
goldfish coordinates four layers of agent intelligence. All four are available from session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — OMEGA | Episodic memory: decisions, sessions, known issues | Required at session start (step 2) |
| Layer 1 — GitNexus / Semble | Code graph + semantic search | MCP on demand |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

### Memory Router

| Content type | System | How |
|---|---|---|
| User preferences, behavioral feedback, reference pointers | Auto-memory (Write tool → `memory/*.md`) | Write file directly |
| Session decisions, lessons, known issues | OMEGA | `omega_store()` |
| Architectural summaries, design notes | Goldfish vault | `write_note()` via goldfish hooks |

Vault = human-readable architectural summaries; OMEGA = machine-queryable decision records. The same decision can produce both — one for reading, one for querying.

Before acting on a project memory that makes code-specific claims (file paths, function names, shipped state), verify against `git log` or a file read.
```

- [ ] **Step 3: Fix step 3 of the Session Start sequence**

Find and replace the omega_protocol line in the session start sequence.

**Old text** (exact match):
```
3. Call `omega_protocol()` — operating rules for this session
```

**New text**:
```
3. Call `omega_protocol()` — supplements CLAUDE.md with any session-specific rules; on free tier this is minimal, CLAUDE.md is the authoritative protocol
```

- [ ] **Step 4: Verify the changes**

```bash
grep -n "Memory Router\|Required at session start\|supplements CLAUDE.md\|Write file directly" /home/tchawes/goldfish/CLAUDE.md
```

Expected: 4 matches — one per new element added.

```bash
grep -n "MCP on demand; OMEGA via\|Layer 0 is static\|operating rules for this session" /home/tchawes/goldfish/CLAUDE.md
```

Expected: 0 matches — the old text is gone.

- [ ] **Step 5: Commit**

```bash
git -C /home/tchawes/goldfish add CLAUDE.md
git -C /home/tchawes/goldfish commit -m "fix: update goldfish CLAUDE.md — layer table split, Memory Router, omega_protocol framing

- Split Layer 1 into OMEGA (required) and GitNexus/Semble (on demand) rows
- Add Memory Router table: one authoritative system per content type
- Fix omega_protocol step: CLAUDE.md is the authoritative protocol on free tier
- Add staleness validation note for code-specific memory claims

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Mirror changes in `src/goldfish/init.py`

**Files:**
- Modify: `src/goldfish/init.py` (lines 25–56, the `_CLAUDE_MD_BLOCK` f-string)

- [ ] **Step 1: Read the current `_CLAUDE_MD_BLOCK`**

```bash
sed -n '25,57p' /home/tchawes/goldfish/src/goldfish/init.py
```

Confirm the block matches the old CLAUDE.md content (4-row table, old step 3).

- [ ] **Step 2: Replace `_CLAUDE_MD_BLOCK` with the updated content**

Replace the entire `_CLAUDE_MD_BLOCK` definition (lines 25–56) with:

```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

goldfish coordinates four layers of agent intelligence. All four are available from session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — OMEGA | Episodic memory: decisions, sessions, known issues | Required at session start (step 2) |
| Layer 1 — GitNexus / Semble | Code graph + semantic search | MCP on demand |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

### Memory Router

| Content type | System | How |
|---|---|---|
| User preferences, behavioral feedback, reference pointers | Auto-memory (Write tool → `memory/*.md`) | Write file directly |
| Session decisions, lessons, known issues | OMEGA | `omega_store()` |
| Architectural summaries, design notes | Goldfish vault | `write_note()` via goldfish hooks |

Vault = human-readable architectural summaries; OMEGA = machine-queryable decision records. The same decision can produce both — one for reading, one for querying.

Before acting on a project memory that makes code-specific claims (file paths, function names, shipped state), verify against `git log` or a file read.

### Session Start (required)

Steps 2–3 are initialization calls, not task responses. The skill-check in step 4 applies to the user's first request.

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — context briefing and recent activity
3. Call `omega_protocol()` — supplements CLAUDE.md with any session-specific rules; on free tier this is minimal, CLAUDE.md is the authoritative protocol
4. Check for applicable skills before responding to the user's first request
5. Work begins

### Before Any Non-Trivial Task

Query all three intelligence tools:
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

GitNexus usage instructions are in the auto-maintained block below. OMEGA and Semble deliver their instructions via MCP server context at session start.
"""
```

- [ ] **Step 3: Verify the block matches goldfish/CLAUDE.md**

```bash
grep -n "Memory Router\|Required at session start\|supplements CLAUDE.md" /home/tchawes/goldfish/src/goldfish/init.py
```

Expected: 3 matches — same elements added in Task 2.

```bash
grep -n "MCP on demand; OMEGA via\|Layer 0 is static\|operating rules for this session" /home/tchawes/goldfish/src/goldfish/init.py
```

Expected: 0 matches — old text gone.

- [ ] **Step 4: Run the test suite to confirm no regressions**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/ -q
```

Expected: all tests pass. The `_CLAUDE_MD_BLOCK` change is a string content change only — no logic changes.

- [ ] **Step 5: Commit**

```bash
git -C /home/tchawes/goldfish add src/goldfish/init.py
git -C /home/tchawes/goldfish commit -m "fix: sync _CLAUDE_MD_BLOCK in init.py with updated CLAUDE.md

Mirrors Task 2 changes so new goldfish installs get the correct layer table,
Memory Router, and omega_protocol framing.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Fix `~/.claude/CLAUDE.md` — global OMEGA block

**Files:**
- Modify: `/home/tchawes/.claude/CLAUDE.md` (lines 6 and 14, inside the OMEGA-managed block)

> **Note:** This block is labeled `managed by omega setup, do not edit`. Running `omega setup` in the future may overwrite these edits. The routing fix is also covered durably by the Memory Router table in goldfish/CLAUDE.md (Task 2), so this task removes the conflict in the global config.

- [ ] **Step 1: Read the current OMEGA block**

```bash
sed -n '1,25p' /home/tchawes/.claude/CLAUDE.md
```

Confirm lines match the expected content (omega_protocol "coordination playbook" on line 6, "User says remember" on line 14).

- [ ] **Step 2: Fix the `omega_protocol` framing (line 6)**

**Old text** (exact match):
```
2. Call `omega_protocol()` for your operating instructions — it's your coordination playbook
```

**New text**:
```
2. Call `omega_protocol()` — supplements CLAUDE.md with session-specific rules; on free tier this is minimal, CLAUDE.md is the authoritative protocol
```

- [ ] **Step 3: Remove the conflicting routing line (line 14)**

**Old text** (exact match — remove this entire line):
```
- User says "remember": `omega_store(text, "user_preference")`
```

**New text**: *(line deleted — no replacement)*

- [ ] **Step 4: Verify**

```bash
grep -n "coordination playbook\|User says.*remember.*omega_store" /home/tchawes/.claude/CLAUDE.md
```

Expected: 0 matches — both old lines gone.

```bash
grep -n "supplements CLAUDE.md" /home/tchawes/.claude/CLAUDE.md
```

Expected: 1 match — new omega_protocol framing present.

---

## Task 5: Fix `project_goldfish.md` — stale content

**Files:**
- Modify: `/home/tchawes/.claude/projects/-home-tchawes-goldfish/memory/project_goldfish.md`

- [ ] **Step 1: Read the current file**

The file currently says: "Goldfish is a Python CLI tool (uvx goldfish init) in the design phase — PRD.md and DESIGN-COMPANION.MD exist but no code has been written yet."

This is stale. goldfish has shipped v0.9.6+ with full implementation.

- [ ] **Step 2: Update the stale claim**

**Old text** (exact match):
```
Goldfish is a Python CLI tool (uvx goldfish init) in the design phase — PRD.md and DESIGN-COMPANION.MD exist but no code has been written yet. It is an orchestration layer ("Ansible playbook") that wires together GitNexus, OMEGA, Semble, and Chonkie to give Claude Code agents persistent memory across sessions.
```

**New text**:
```
Goldfish is a shipped Python CLI tool (uvx goldfish init, v0.9.6+). It is an orchestration layer ("Ansible playbook") that wires together GitNexus, OMEGA, Semble, and Chonkie to give Claude Code agents persistent memory across sessions. ~500 lines across 9 modules (cli, init, hook, drain, enricher, vault, claude_md, config, miner).
```

- [ ] **Step 3: Verify**

```bash
grep -n "design phase\|no code has been written" /home/tchawes/.claude/projects/-home-tchawes-goldfish/memory/project_goldfish.md
```

Expected: 0 matches — stale claim gone.

```bash
grep -n "v0.9.6" /home/tchawes/.claude/projects/-home-tchawes-goldfish/memory/project_goldfish.md
```

Expected: 1 match — updated state present.

---

## Task 6: Create `goldfish-diagnostic` skill

**Files:**
- Create: `/home/tchawes/.claude/skills/goldfish-diagnostic/SKILL.md`

- [ ] **Step 1: Create the skill directory and file**

```bash
mkdir -p /home/tchawes/.claude/skills/goldfish-diagnostic
```

Then write `/home/tchawes/.claude/skills/goldfish-diagnostic/SKILL.md` with this exact content:

```markdown
---
name: goldfish-diagnostic
description: Use when you want to assess the memory layer architecture for gaps, routing ambiguities, or instruction fictions. Outputs a scored 6-dimension assessment using the Six Memory Failure Modes framework and stores it to OMEGA for retrospective trend tracking.
---

# Goldfish Memory Diagnostic

Assess the current memory layer instruction set against the Six Memory Failure Modes framework. Assessment-only — does not modify any files. Surfaces gaps, scores dimensions, stores to OMEGA, emits session KPI instructions.

## When to Invoke

- Before sessions focused on memory layer tuning
- When context quality feels degraded (high NEEDS_CONTEXT rate, routing confusion, stale answers)
- To establish a baseline before and after instruction changes

## Sequence

### Step 1 — Announce

State: "Running memory diagnostic using the Six Memory Failure Modes framework."

### Step 2 — Load Evidence

Read in parallel:
- `/home/tchawes/goldfish/CLAUDE.md` — project instructions (layer table, Memory Router, session start)
- `/home/tchawes/.claude/CLAUDE.md` — global instructions (OMEGA quick reference, omega_protocol framing)
- `/home/tchawes/.claude/projects/-home-tchawes-goldfish/memory/MEMORY.md` — memory index

If `omega_welcome()` was already called this session, use that output. If not, call it now.

### Step 3 — Assess Each Dimension

For each failure mode, apply the diagnostic question to the loaded evidence. Assign GREEN / YELLOW / RED with exactly one line of specific evidence (file and line quote, or exact phrase).

Reference: `docs/memory-diagnostic.md` for full failure mode definitions and scoring rubric.

**The Six Failure Modes:**

| # | Failure | Diagnostic Question |
|---|---------|-------------------|
| 1 | Routing fog | For each memory type, is there exactly one authoritative system? |
| 2 | Dark corner | Is every important context type captured by at least one system? |
| 3 | Arrival gap | Does each memory type land before the first decision it informs? |
| 4 | Stale signal | Can outdated memory be detected before it informs a decision? |
| 5 | Boundary blur | Are layer responsibilities distinct enough that no content type fits two layers? |
| 6 | Instruction fiction | Does the documented behavior match what the system actually does? |

**Scoring rubric:**
- 🟢 GREEN: no instances found in current instruction set
- 🟡 YELLOW: partial coverage, edge cases, or judgment-dependent gaps
- 🔴 RED: structural gap — agents will misroute without correction

### Step 4 — Present Scorecard

Output this table with scores and evidence filled in:

```
| Failure | Score | Key Evidence |
|---------|-------|-------------|
| Routing fog | [score] | [specific evidence] |
| Dark corner | [score] | [specific evidence] |
| Arrival gap | [score] | [specific evidence] |
| Stale signal | [score] | [specific evidence] |
| Boundary blur | [score] | [specific evidence] |
| Instruction fiction | [score] | [specific evidence] |

Summary: X RED / Y YELLOW / Z GREEN
```

### Step 5 — Store to OMEGA

```bash
omega store "Memory diagnostic [YYYY-MM-DD]: X RED / Y YELLOW / Z GREEN. RED: [failure names]. YELLOW: [failure names]. GREEN: [failure names]." "diagnostic"
```

The retrospective skill queries this via `omega_query("diagnostic")`.

### Step 6 — Emit Session KPI Instructions

Based on RED findings, state what to track for the rest of the session:

> "For this session, actively track:
> - NEEDS_CONTEXT escalations — note what was missing
> - Routing decisions — which system you wrote to and why
> - [Additional KPIs derived from RED failure modes found]"

### Step 7 — List Priority Actions

```
Priority fixes (RED → action required):
1. [Failure name]: [specific fix from docs/memory-diagnostic.md]
2. ...

Candidate improvements (YELLOW → consider addressing):
1. [Failure name]: [specific action]
```

These become the candidate task list for the session's implementation work.
```

- [ ] **Step 2: Verify the skill has all required sections**

```bash
grep -n "name:\|description:\|When to Invoke\|Step 1\|Step 2\|Step 3\|Step 4\|Step 5\|Step 6\|Step 7" /home/tchawes/.claude/skills/goldfish-diagnostic/SKILL.md
```

Expected: all 9 sections present.

- [ ] **Step 3: Verify the skill appears in the available skills list**

The skill loads automatically on next session start from `~/.claude/skills/`. No registration required. Confirm the directory exists:

```bash
ls /home/tchawes/.claude/skills/goldfish-diagnostic/
```

Expected: `SKILL.md`

---

## Task 7: Update `goldfish-session-retrospective` skill — add Memory Layer Health section

**Files:**
- Modify: `/home/tchawes/.claude/skills/goldfish-session-retrospective/SKILL.md`

- [ ] **Step 1: Read the current skill to find the insertion point**

```bash
grep -n "What Worked\|KPI Scorecard\|OMEGA Storage" /home/tchawes/.claude/skills/goldfish-session-retrospective/SKILL.md
```

Expected: line numbers for sections 4 (KPI Scorecard), 5 (What Worked / What Didn't), and 7 (OMEGA Storage). The new section 4.5 inserts between 4 and 5.

- [ ] **Step 2: Insert Section 4.5 after the KPI Scorecard section**

Find and replace the `### 5. What Worked / What Didn't` heading (and its description) to insert section 4.5 before it.

**Old text** (exact match):
```
### 5. What Worked / What Didn't

Two bullet lists, max 3 items each. Concrete — not "the process was good."
```

**New text**:
```
### 4.5 Memory Layer Health

Call `omega_query("diagnostic")` to retrieve any diagnostic stored this session.

**If diagnostic found:**

| Failure | Score | Key Evidence |
|---------|-------|-------------|
| Routing fog | [score] | [evidence] |
| Dark corner | [score] | [evidence] |
| Arrival gap | [score] | [evidence] |
| Stale signal | [score] | [evidence] |
| Boundary blur | [score] | [evidence] |
| Instruction fiction | [score] | [evidence] |

If a prior-session diagnostic exists in OMEGA, show delta per dimension:
↑ = improved  ↓ = degraded  → = stable

**Headline:** `Memory layer: X RED / Y YELLOW / Z GREEN [↑↓→ vs last diagnostic on YYYY-MM-DD]`

**If no diagnostic was run this session:**
> "No diagnostic run this session — invoke `/goldfish-diagnostic` to establish baseline."

---

### 5. What Worked / What Didn't

Two bullet lists, max 3 items each. Concrete — not "the process was good."
```

- [ ] **Step 3: Update the Required Sections list in the Overview to include 4.5**

Find and replace the overview text that lists required sections:

**Old text** (exact match):
```
## Required Sections (in order)

### 1. Header
```

**New text**:
```
## Required Sections (in order)

Sections: 1 Header, 2 What We Built, 3 Layer Attribution, 4 KPI Scorecard, **4.5 Memory Layer Health**, 5 What Worked/Didn't, 6 Durable Decisions, 7 Open Questions, OMEGA Storage.

### 1. Header
```

- [ ] **Step 4: Verify**

```bash
grep -n "Memory Layer Health\|omega_query.*diagnostic\|goldfish-diagnostic" /home/tchawes/.claude/skills/goldfish-session-retrospective/SKILL.md
```

Expected: 3 matches — section heading, the query call, and the skill reference.

---

## Post-Implementation Checklist

Run these after all tasks complete to confirm the implementation is correct end-to-end:

```bash
# 1. Git log — confirm 3 commits on main
git -C /home/tchawes/goldfish log --oneline -5

# 2. Framework doc exists with all sections
grep -c "##" /home/tchawes/goldfish/docs/memory-diagnostic.md

# 3. Memory Router present in both CLAUDE.md and init.py
grep -c "Memory Router" /home/tchawes/goldfish/CLAUDE.md /home/tchawes/goldfish/src/goldfish/init.py

# 4. OMEGA on-demand label gone from both files
grep -rn "MCP on demand; OMEGA via" /home/tchawes/goldfish/

# 5. Both skills exist
ls /home/tchawes/.claude/skills/goldfish-diagnostic/SKILL.md
ls /home/tchawes/.claude/skills/goldfish-session-retrospective/SKILL.md

# 6. Tests still pass
cd /home/tchawes/goldfish && python -m pytest tests/ -q
```

All 6 checks must pass before calling this implementation complete.
