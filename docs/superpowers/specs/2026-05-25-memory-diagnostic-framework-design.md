# Memory Diagnostic Framework Design

**Date:** 2026-05-25
**Scope:** New framework doc, 6 instruction fixes, new skill, retrospective skill update
**Goal:** Replace reactive instruction tuning with a repeatable diagnostic framework — named failure modes, scored assessments, trend tracking across sessions.

---

## Problems Being Solved

Four cycles of memory layer tuning have been reactive (fix what hurts) rather than systematic (find what's wrong before it hurts). Two root causes:

1. **No diagnostic language.** No shared vocabulary for what "good" memory layer architecture looks like. Fixes address symptoms without checking whether the system is healthy across all dimensions.
2. **Specific gaps still open.** Even after the 2026-05-25 layer-tightening session, three RED-scored failure modes remain in the current instruction set.

**Baseline diagnostic (run 2026-05-25):**

| # | Failure Mode | Score | Key Evidence |
|---|-------------|-------|-------------|
| 1 | Routing fog | 🔴 RED | No routing decision table; user prefs claimed by both auto-memory and OMEGA |
| 2 | Dark corner | 🟡 YELLOW | Tool health state + KPI timeseries have no home |
| 3 | Arrival gap | 🟡 YELLOW | `omega_protocol()` thinness — CLAUDE.md absence not a concern (goldfish ensures it) |
| 4 | Stale signal | 🟡 YELLOW | `project_goldfish.md` stale; no structured validation cadence |
| 5 | Boundary blur | 🔴 RED | Layer 0/OMEGA user-pref overlap; vault vs OMEGA scope undefined |
| 6 | Instruction fiction | 🔴 RED | `omega_protocol` framing; OMEGA labeled "on demand" but is mandatory |

Target: move all RED → YELLOW or GREEN; establish the framework so future sessions can track direction not just state.

---

## Design

### Part 1 — The Six Memory Failure Modes (`docs/memory-diagnostic.md`)

A sibling document to `docs/five-failures.md`. Same design language: named failure modes, symptom, diagnostic question, remedy class. Scored GREEN / YELLOW / RED.

**The Six Failure Modes:**

| Failure | Symptom | Diagnostic Question | Remedy Class | Layer Focus |
|---------|---------|--------------------|-----------|----|
| **Routing fog** | Agent asks "which system?" or writes to wrong store | For this memory type, is there exactly one authoritative system? | Add routing decision table | L0/L1 boundary |
| **Dark corner** | Agent re-derives same context each session from scratch | Is every important context type captured by at least one system? | Add coverage entry | Any |
| **Arrival gap** | Agent makes worse early decisions; context arrives after it's needed | Does this memory type land before the first decision it informs? | Promote to earlier layer or system | L0 vs L1 timing |
| **Stale signal** | Agent acts on outdated facts; contradictions between layers | Can outdated memory be detected before it informs a decision? | Add validation cadence | All layers |
| **Boundary blur** | Same content type has two homes; layers bleed into each other | Are layer responsibilities distinct enough that no content type fits two layers? | Write a scope rule | L0–L3 |
| **Instruction fiction** | Agent follows documented behavior that system doesn't exhibit | Does the documented behavior match what the system actually does? | Fix the doc or fix the system | L2/L3 |

**Scoring rubric:**
- 🟢 GREEN: no instances found in current instruction set
- 🟡 YELLOW: partial coverage, edge cases, or judgment-dependent gaps
- 🔴 RED: structural gap — agents will misroute without correction

**Current State Assessment section:** A table with the 6 rows, score, and one line of key evidence. Updated by the `goldfish-diagnostic` skill each time it runs and committed to the doc.

---

### Part 2 — Instruction Fixes

Six targeted changes. RED findings addressed first.

#### Fix 1 — Routing fog: Add Memory Router table to CLAUDE.md

Add a **Memory Router** table to the CLAUDE.md quick reference section. Three rows, no ambiguity:

| Content type | System | How |
|---|---|---|
| User preferences, behavioral feedback, reference pointers | Auto-memory (Write tool → `memory/*.md`) | Write file directly |
| Session decisions, lessons, known issues | OMEGA | `omega_store()` |
| Architectural summaries, design notes | Goldfish vault | `write_note()` via goldfish hooks |

Remove the line `"User says 'remember': omega_store(text, 'user_preference')"` from the CLAUDE.md quick reference. User preferences route to auto-memory, not OMEGA.

#### Fix 2 — Boundary blur: Define vault scope in CLAUDE.md

Add one sentence to the memory division note:

> "Vault = human-readable architectural summaries; OMEGA = machine-queryable decision records. The same decision can produce both — one for reading, one for querying."

#### Fix 3 — Instruction fiction: Reframe `omega_protocol()` in CLAUDE.md

Change the current framing from:
> "Call `omega_protocol()` — it's your coordination playbook"

To:
> "Call `omega_protocol()` — supplements CLAUDE.md with any session-specific rules. On free tier this is minimal; CLAUDE.md is the authoritative protocol."

#### Fix 4 — Instruction fiction: Fix Layer 1 table OMEGA entry

In the Layer 1 table, OMEGA currently appears in the same row as GitNexus and Semble with "When it loads" = "MCP on demand." This is wrong — OMEGA is required at session start.

Split OMEGA into its own row:

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — OMEGA | Episodic memory: decisions, sessions, known issues | Required at session start (step 2) |
| Layer 1 — GitNexus / Semble | Code graph + semantic search | MCP on demand |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

#### Fix 5 — Stale signal: Update `project_goldfish.md`

Update the auto-memory file to reflect current state: goldfish has shipped v0.9.6+ with full code implementation. The "design phase — no code written yet" claim is stale and would mislead a fresh agent.

Also add a staleness note to the CLAUDE.md quick reference under the Memory Router table:
> "Before acting on a project memory that makes code-specific claims (file paths, function names, shipped state), verify against `git log` or a file read."

#### Fix 6 — Instruction fiction: Clarify "project-agnostic" in Layer 2 description

Clarify Layer 2's "project-agnostic" label:
> "project-agnostic in the sense that goldfish generates this block for any project it initializes; the referenced tools are goldfish's contribution to every project, not goldfish-specific content."

#### Mirror all CLAUDE.md fixes in `init.py` `_CLAUDE_MD_BLOCK`

`_CLAUDE_MD_BLOCK` in `src/goldfish/init.py` is the source of truth for new installs. All fixes to CLAUDE.md must be reflected there so newly initialized projects get the correct text.

---

### Part 3 — `goldfish-diagnostic` Skill

**Location:** `.claude/skills/goldfish/goldfish-diagnostic/SKILL.md`

**Trigger:** User invokes `/goldfish-diagnostic` — manual, not automatic.

**Sequence when invoked:**

1. **Announce:** "Running memory diagnostic using the Six Memory Failure Modes framework."

2. **Load evidence:** Read CLAUDE.md, AGENTS.md, MEMORY.md index. Use `omega_welcome()` output if already called this session; if not, call it now.

3. **Assess each dimension:** For each of the 6 failure modes, apply the diagnostic question against the loaded evidence. Assign GREEN / YELLOW / RED with one specific line of evidence (not generic commentary).

4. **Present scorecard:** The 6-row table with scores and evidence. This is the primary output the user sees.

5. **Store to OMEGA:** `omega_store()` with the scorecard as structured content, typed as `"diagnostic"`. The retrospective skill will query this.

6. **Emit session KPI instructions:** A short block the agent follows for the rest of the session — which KPIs to track, any session-specific flags from RED findings (e.g., "watch for routing decisions and note which system was chosen").

7. **List priority actions:** RED items with specific fix descriptions, in priority order. These are the candidate tasks for the session's work.

**Scope:** Assessment-only. Does not modify any files. Surfaces, scores, stores, and instructs. All fixes happen via separate plan and implementation.

---

### Part 4 — `goldfish-session-retrospective` Skill Update

Add a new **Memory Layer Health** section after the KPI Scorecard (Section 4), before "What Worked / What Didn't" (Section 5).

**New Section 4.5 — Memory Layer Health:**

```
### 4.5 Memory Layer Health

[Call omega_query("diagnostic") to retrieve any diagnostic stored this session.]

If diagnostic found this session:
| Failure | Score | Key Evidence |
|---------|-------|-------------|
| Routing fog | [score] | [evidence] |
| Dark corner | [score] | [evidence] |
| Arrival gap | [score] | [evidence] |
| Stale signal | [score] | [evidence] |
| Boundary blur | [score] | [evidence] |
| Instruction fiction | [score] | [evidence] |

[If prior-session diagnostic exists in OMEGA: show delta per dimension]
↑ = improved  ↓ = degraded  → = stable

**Headline:** Memory layer: X RED / Y YELLOW / Z GREEN [↑↓→ vs last diagnostic]

If no diagnostic was run this session:
"No diagnostic run this session — invoke /goldfish-diagnostic to establish baseline."
```

---

## Files Changed

| File | Change |
|------|--------|
| `docs/memory-diagnostic.md` | New — the Six Failure Modes framework doc |
| `CLAUDE.md` | Fix 1–4, 6: Memory Router table, vault scope, omega_protocol framing, Layer 1 table split, project-agnostic clarification |
| `src/goldfish/init.py` | Mirror all CLAUDE.md changes in `_CLAUDE_MD_BLOCK` |
| `memory/project_goldfish.md` | Fix 5: Update stale "design phase" claim |
| `.claude/skills/goldfish/goldfish-diagnostic/SKILL.md` | New skill |
| `.claude/skills/goldfish-session-retrospective/SKILL.md` | Add Section 4.5 Memory Layer Health |

No logic changes to any Python module. No new Python functions.

---

## Success Criteria

After implementation:

- Running `/goldfish-diagnostic` produces a 6-row scorecard with GREEN/YELLOW/RED scores and specific evidence for each dimension
- The diagnostic output is stored in OMEGA and retrievable by the retrospective skill
- CLAUDE.md contains a Memory Router table — a fresh agent can determine the correct system for any content type without inferring
- Layer 1 table correctly shows OMEGA as "Required at session start" not "on demand"
- `omega_protocol()` is framed as a supplement to CLAUDE.md, not the authoritative playbook
- `project_goldfish.md` reflects goldfish's shipped state (v0.9.6+, full code)
- The retrospective skill includes a Memory Layer Health section that shows trend vs prior session when a diagnostic exists
- All CLAUDE.md changes are mirrored in `init.py` `_CLAUDE_MD_BLOCK`
- Diagnostic baseline recorded: 3 RED / 3 YELLOW / 0 GREEN (2026-05-25)
