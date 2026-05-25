# Memory Tuning — Diagnostic Run 3 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all 6 YELLOW findings from memory diagnostic Run 3, tighten the diagnostic framework so intentional design choices don't re-flag as gaps, and store architectural rationale as OMEGA decisions.

**Architecture:** Four files receive instruction edits (no Python logic changes). `goldfish/CLAUDE.md` and `src/goldfish/init.py`'s `_CLAUDE_MD_BLOCK` must be kept in sync — edit CLAUDE.md first, then apply identical text changes to `_CLAUDE_MD_BLOCK`. A stale reference sweep follows all targeted edits. Six OMEGA decisions reinforce the architectural rationale via CLI.

**Tech Stack:** Python (goldfish), Markdown instruction files, OMEGA CLI (`omega store`), shell grep for stale reference sweep.

---

### Task 1: Remove stale `omega flush` from PreCompact flow

**Files:**
- Modify: `docs/architecture.md:185`

- [ ] **Step 1: Confirm the stale line exists**

```bash
grep -n "omega flush" /home/tchawes/goldfish/docs/architecture.md
```

Expected output:
```
185:omega flush(session_snapshot)
```

- [ ] **Step 2: Remove the stale line**

In `docs/architecture.md`, find the PreCompact flow block (around line 180) and remove the `omega flush(session_snapshot)` line. The block should change from:

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

to:

```
Claude's context window approaches capacity
        ↓
PreCompact fires (Claude waits)
        ↓
vault.write("Memory/Checkpoints/{session_id}.md", summary)
        ↓
PreCompact returns → compaction proceeds
```

- [ ] **Step 3: Verify no `omega flush` remains in docs**

```bash
grep -rn "omega flush" /home/tchawes/goldfish/docs/ /home/tchawes/goldfish/CLAUDE.md /home/tchawes/goldfish/AGENTS.md
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture.md
git commit -m "fix: remove stale omega flush from PreCompact flow in architecture.md

omega flush was removed in goldfish v1.0 polish. PreCompact now writes
vault checkpoint only.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Update `CLAUDE.md` — Memory Router, boundary blur, arrival gap, staleness UX

**Files:**
- Modify: `CLAUDE.md` (project root — not `~/.claude/CLAUDE.md`)

Four edits to the Agent Knowledge Tools section (managed by goldfish, layer 2). Make them all before committing.

- [ ] **Step 1: Fix the vault row in the Memory Router table**

Find this line in the Memory Router table:
```
| Architectural summaries, design notes | Goldfish vault | `write_note()` via goldfish hooks |
```

Replace with:
```
| Architectural summaries, design notes | Goldfish vault | explicit `write_note()` when human audience warrants it |
```

- [ ] **Step 2: Replace the post-table explanation with routing fog tiebreaker + consumer rule**

Find this block (immediately after the Memory Router table):
```
Vault = human-readable architectural summaries; OMEGA = machine-queryable decision records. The same decision can produce both — one for reading, one for querying.
```

Replace with:
```
For reads: auto-memory is authoritative for user preferences; `omega_profile()` is supplemental — additional signal, not ground truth.

Vault = consumer is human (Obsidian-readable narrative, long-form). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read this note. Architectural decisions may warrant both; session facts warrant OMEGA only. Goldfish hooks automatically write vault notes for task events and session checkpoints — architectural summaries require explicit agent writes.
```

- [ ] **Step 3: Add arrival gap note to Session Start**

Find this block:
```
### Session Start (required)

Steps 2–3 are initialization calls, not task responses. The skill-check in step 4 applies to the user's first request.

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — context briefing and recent activity
3. Call `omega_protocol()` — supplements CLAUDE.md with any session-specific rules; on free tier this is minimal, CLAUDE.md is the authoritative protocol
4. Check for applicable skills before responding to the user's first request
5. Work begins
```

Replace with:
```
### Session Start (required)

Steps 2–3 are initialization calls, not task responses. The skill-check in step 4 applies to the user's first request.

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — context briefing and recent activity
3. Call `omega_protocol()` — supplements CLAUDE.md with any session-specific rules; on free tier this is minimal, CLAUDE.md is the authoritative protocol
4. Check for applicable skills before responding to the user's first request
5. Work begins

> GitNexus/Semble load on-demand — intentional just-in-time delivery, not a gap. Targeted context arrives exactly when the relevant question is asked.
```

- [ ] **Step 4: Add GitNexus staleness cadence note + worktree guidance to Before Any Non-Trivial Task**

Find this block:
```
### Before Any Non-Trivial Task

Query all three intelligence tools:
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes
```

Replace with:
```
### Before Any Non-Trivial Task

Query all three intelligence tools:
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

> **GitNexus staleness:** The stale warning fires after every commit — expected during active development. Re-analyze (`npx gitnexus analyze`) before code intelligence tasks (impact analysis, exploration), not after every commit. Prefer worktrees for feature development — each worktree has its own `.gitnexus/` index. See `superpowers:using-git-worktrees`.
```

- [ ] **Step 5: Verify all four edits are present**

```bash
grep -n "authoritative for user preferences\|consumer is human\|just-in-time delivery\|stale warning fires after every commit" CLAUDE.md
```

Expected: 4 lines found, one for each edit.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "fix: tighten Memory Router — routing fog tiebreaker, boundary blur rule, arrival gap note, GitNexus staleness cadence

- Routing fog: auto-memory authoritative for reads, omega_profile supplemental
- Boundary blur: consumer-driven rule (vault=human, OMEGA=agent)
- Vault row: explicit write vs automatic hooks now distinguished
- Arrival gap: on-demand = just-in-time, documented as intentional
- GitNexus staleness: re-analyze before tasks, not after every commit
- Worktree guidance: each worktree has own .gitnexus/ index

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Sync `_CLAUDE_MD_BLOCK` in `src/goldfish/init.py`

**Files:**
- Modify: `src/goldfish/init.py:25-69`

`_CLAUDE_MD_BLOCK` is the template goldfish writes to new project CLAUDE.md files. It must mirror the Agent Knowledge Tools section in `goldfish/CLAUDE.md`. Apply identical text changes to the four sections edited in Task 2.

- [ ] **Step 1: Apply the vault row fix**

In `src/goldfish/init.py`, find:
```python
| Architectural summaries, design notes | Goldfish vault | `write_note()` via goldfish hooks |
```

Replace with:
```python
| Architectural summaries, design notes | Goldfish vault | explicit `write_note()` when human audience warrants it |
```

- [ ] **Step 2: Apply the post-table explanation fix**

In `src/goldfish/init.py`, find:
```python
Vault = human-readable architectural summaries; OMEGA = machine-queryable decision records. The same decision can produce both — one for reading, one for querying.
```

Replace with:
```python
For reads: auto-memory is authoritative for user preferences; `omega_profile()` is supplemental — additional signal, not ground truth.

Vault = consumer is human (Obsidian-readable narrative, long-form). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read this note. Architectural decisions may warrant both; session facts warrant OMEGA only. Goldfish hooks automatically write vault notes for task events and session checkpoints — architectural summaries require explicit agent writes.
```

- [ ] **Step 3: Apply the session start arrival gap note**

In `src/goldfish/init.py`, find:
```python
4. Check for applicable skills before responding to the user's first request
5. Work begins
```

Replace with:
```python
4. Check for applicable skills before responding to the user's first request
5. Work begins

> GitNexus/Semble load on-demand — intentional just-in-time delivery, not a gap. Targeted context arrives exactly when the relevant question is asked.
```

- [ ] **Step 4: Apply the staleness cadence note**

In `src/goldfish/init.py`, find:
```python
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

Before spawning subagents:
```

Replace with:
```python
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

> **GitNexus staleness:** The stale warning fires after every commit — expected during active development. Re-analyze (`npx gitnexus analyze`) before code intelligence tasks (impact analysis, exploration), not after every commit. Prefer worktrees for feature development — each worktree has its own `.gitnexus/` index. See `superpowers:using-git-worktrees`.

Before spawning subagents:
```

- [ ] **Step 5: Run the test suite**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/ -q
```

Expected: all tests pass (≈100 tests, ~0.3s). No failures.

- [ ] **Step 6: Verify _CLAUDE_MD_BLOCK matches CLAUDE.md**

```bash
grep -c "authoritative for user preferences\|consumer is human\|just-in-time delivery\|stale warning fires after every commit" /home/tchawes/goldfish/src/goldfish/init.py
```

Expected: `4`

- [ ] **Step 7: Commit**

```bash
git add src/goldfish/init.py
git commit -m "fix: sync _CLAUDE_MD_BLOCK in init.py with updated CLAUDE.md

Mirrors all four edits from goldfish/CLAUDE.md: routing fog tiebreaker,
boundary blur consumer rule, arrival gap note, GitNexus staleness guidance.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Update `docs/memory-diagnostic.md` — Framework tightening + Current State Assessment

**Files:**
- Modify: `docs/memory-diagnostic.md`

Three framework amendments, then update the Current State Assessment table.

- [ ] **Step 1: Add Goldfish Architecture Notes section after the failure modes table**

Find this line (just after the failure modes table, before the Scoring Rubric section):
```
---

## Scoring Rubric
```

Insert before it:
```
### Goldfish Architecture Notes

These qualifiers apply when scoring goldfish's instruction set specifically:

**Arrival gap:** Just-in-time on-demand delivery counts as arrival — pre-loading is not required if targeted delivery is the architectural intent. GitNexus/Semble loading on-demand when a code question is asked satisfies the arrival gap criterion.

**Dark corner:** A context type is NOT a dark corner if: (a) it is re-derivable on demand in <1 second, and (b) a CLI diagnostic command exists (e.g., `goldfish doctor`). Document the CLI, close the finding. Tool health state meets both criteria.

**Stale signal:** A "verify before acting" instruction in the agent's constitution is a valid validation mechanism. Absence of an automated cadence is not automatically YELLOW if explicit verification is instructed.

---

```

- [ ] **Step 2: Update the Current State Assessment table**

Find the entire Current State Assessment section:
```
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
```

Replace with:
```
**Last diagnostic:** 2026-05-25 (Run 4)

| Failure | Score | Key Evidence |
|---------|-------|-------------|
| Routing fog | 🟡 YELLOW | Read-side tiebreaker added (auto-memory authoritative, omega_profile supplemental); write routing clear |
| Dark corner | 🟢 GREEN | Tools assumed installed; `goldfish doctor` CLI is the diagnostic path — justified absence |
| Arrival gap | 🟢 GREEN | On-demand = just-in-time; intentional architectural design, documented in coordination block |
| Stale signal | 🟢 GREEN | "Verify code claims before acting" instruction is the validation cadence |
| Boundary blur | 🟡 YELLOW | Consumer-driven rule added; explicit vs automatic vault write distinction documented |
| Instruction fiction | 🟡 YELLOW | PreCompact flow fixed; ongoing vigilance as code evolves |

**Summary:** 0 RED / 3 YELLOW / 3 GREEN (2026-05-25 Run 4)
```

- [ ] **Step 3: Verify the table updated correctly**

```bash
grep -n "GREEN\|YELLOW\|RED" /home/tchawes/goldfish/docs/memory-diagnostic.md | tail -10
```

Expected: 3 GREEN lines, 3 YELLOW lines, 0 RED lines in the assessment table.

- [ ] **Step 4: Commit**

```bash
git add docs/memory-diagnostic.md
git commit -m "docs: tighten memory-diagnostic framework + update Run 4 scorecard

Add Goldfish Architecture Notes section with qualifiers for arrival gap,
dark corner, and stale signal — prevents false positives from intentional
design choices. Update assessment to 0 RED / 3 YELLOW / 3 GREEN.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Stale reference sweep

**Files:** All docs and instruction files — read-only scan, fix findings in place.

- [ ] **Step 1: Grep for `omega flush`**

```bash
grep -rn "omega flush" /home/tchawes/goldfish/ --include="*.md" --include="*.py" --include="*.toml"
```

Expected: no output (Task 1 removed the only instance).

- [ ] **Step 2: Grep for three-layer references**

```bash
grep -rni "three-layer\|three layer\|3-layer" /home/tchawes/goldfish/ --include="*.md" --include="*.py"
```

Expected: no output. If any found, update them to "four-layer" with appropriate context.

- [ ] **Step 3: Grep for removed CLI commands**

```bash
grep -rn "omega mine\|omega note\|semble reindex\|semble index\b" /home/tchawes/goldfish/ --include="*.md" --include="*.py"
```

Expected: no output. If any found in docs, remove or replace with the current correct command.

- [ ] **Step 4: Commit if any findings were fixed**

Only commit if step 2 or 3 found and fixed something:
```bash
git add -p   # stage only the specific fixes
git commit -m "fix: remove stale references found in sweep

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

If no findings: skip this commit.

---

### Task 6: Store 6 OMEGA decisions

**Files:** None — CLI only.

- [ ] **Step 1: Store arrival gap decision**

```bash
omega store "Arrival gap: GitNexus/Semble load on-demand by design — just-in-time delivery of targeted context, not a gap. Pre-loading would deliver bulk context, not right context. Arrival gap diagnostic scores GREEN for this architecture." "decision"
```

- [ ] **Step 2: Store dark corner decision**

```bash
omega store "Dark corner: Tool health state (gitnexus/omega/semble installed?) has no persistent memory home by design. Assumption is goldfish is installed and running. User diagnoses with goldfish doctor CLI when needed. Re-derivation <1s. Dark corner diagnostic scores GREEN for this architecture." "decision"
```

- [ ] **Step 3: Store boundary blur decision**

```bash
omega store "Boundary blur: Vault vs OMEGA routing is consumer-driven. Vault = consumer is human (Obsidian-readable narrative). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read the note. Architectural decisions may warrant both; session facts warrant OMEGA only. Goldfish hooks auto-write vault notes for task events and checkpoints — architectural summaries require explicit agent writes." "decision"
```

- [ ] **Step 4: Store routing fog tiebreaker decision**

```bash
omega store "Routing fog tiebreaker: For user preference reads, auto-memory (memory/*.md) is authoritative. omega_profile() is supplemental — additional signal, not ground truth. Auto-memory wins on conflicts." "decision"
```

- [ ] **Step 5: Store instruction fiction guard decision**

```bash
omega store "Instruction fiction guard: PreCompact no longer calls omega flush — removed in goldfish v1.0 polish. PreCompact writes vault checkpoint via vault.write() only. Any doc showing omega flush in PreCompact flow is stale." "decision"
```

- [ ] **Step 6: Store GitNexus staleness decision**

```bash
omega store "GitNexus staleness: The stale warning fires after every commit via PostToolUse hook — correct, expected behavior during active development. Re-analyze (npx gitnexus analyze) before code intelligence tasks (impact analysis, exploration), not after every commit. One analyze per work session is the right cadence. Worktrees isolate .gitnexus/ indices — each worktree has its own index, keeping main branch analysis clean." "decision"
```

- [ ] **Step 7: Verify decisions are queryable**

```bash
omega query "arrival gap dark corner boundary blur routing fog" | head -30
```

Expected: recent entries mentioning the decisions just stored.

---

### Task 7: Final verification

- [ ] **Step 1: Run the full test suite**

```bash
cd /home/tchawes/goldfish && python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 2: Verify no omega flush remains anywhere**

```bash
grep -rn "omega flush" /home/tchawes/goldfish/ --include="*.md" --include="*.py"
```

Expected: no output.

- [ ] **Step 3: Verify _CLAUDE_MD_BLOCK and CLAUDE.md are in sync**

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/tchawes/goldfish/src')
from goldfish.init import _CLAUDE_MD_BLOCK
block_lines = set(_CLAUDE_MD_BLOCK.split('\n'))
markers = [
    'authoritative for user preferences',
    'consumer is human',
    'just-in-time delivery',
    'stale warning fires after every commit',
]
for m in markers:
    found = any(m in line for line in block_lines)
    print(f'  {\"OK\" if found else \"MISSING\"}: {m}')
"
```

Expected: all four markers print `OK`.

- [ ] **Step 4: Run goldfish-diagnostic**

In Claude Code, invoke: `/goldfish-diagnostic`

Expected scorecard:
```
| Routing fog      | YELLOW |
| Dark corner      | GREEN  |
| Arrival gap      | GREEN  |
| Stale signal     | GREEN  |
| Boundary blur    | YELLOW |
| Instruction fiction | YELLOW |
Summary: 0 RED / 3 YELLOW / 3 GREEN
```

- [ ] **Step 5: Commit if any final cleanup was needed**

Only if step 2-3 found something not caught earlier:
```bash
git add -p
git commit -m "fix: final cleanup from verification pass

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
