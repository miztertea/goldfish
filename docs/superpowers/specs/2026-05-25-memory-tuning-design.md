# Memory Tuning — Diagnostic Run 3 Fixes

**Date:** 2026-05-25  
**Diagnostic baseline:** 0 RED / 6 YELLOW / 0 GREEN (Run 3)  
**Target:** 0 RED / 3 YELLOW / 3 GREEN

## Background

Following three diagnostic runs on 2026-05-25, all REDs were resolved. This session addresses the remaining YELLOWs using a two-pronged strategy:

1. **Fix the instructions** — tighten Memory Router language, correct stale doc references
2. **Tighten the diagnostic framework** — amend `memory-diagnostic.md` so future runs don't flag intentional design choices as gaps, and store architectural rationale in OMEGA

## Scope

### Files to modify

| File | Change |
|------|--------|
| `goldfish/CLAUDE.md` | Memory Router: routing fog tiebreaker, boundary blur consumer rule, arrival gap note, vault automation clarity |
| `src/goldfish/init.py` | Sync `_CLAUDE_MD_BLOCK` to match updated CLAUDE.md |
| `docs/architecture.md` | Fix PreCompact flow: remove stale `omega flush` call |
| `docs/memory-diagnostic.md` | Tighten diagnostic questions, update Current State Assessment |

### OMEGA stores (5 decisions)

Architectural rationale stored as machine-queryable decisions so future diagnostics have context before scoring.

### Stale reference sweep

Review all instruction and doc files for references that may have become stale alongside the targeted fixes. Specifically look for: `omega flush`, "three-layer", removed CLI commands.

## Section 1 — Instruction Fixes

### A. Routing fog tiebreaker (`goldfish/CLAUDE.md`)

Add one line to the Memory Router, below the table:

> "For reads: auto-memory is authoritative for user preferences; `omega_profile()` is supplemental and may overlap — it is additional signal, not ground truth."

### B. Instruction fiction (`docs/architecture.md`)

In the PreCompact runtime flow, remove the `omega flush(session_snapshot)` line. The `vault.write("Memory/Checkpoints/{session_id}.md", summary)` line is correct and stays. `omega flush` was removed in goldfish v1.0 polish.

### C. Boundary blur (`goldfish/CLAUDE.md`)

Two changes to the Memory Router vault row:

1. Replace "via goldfish hooks" with "explicit agent write when human audience warrants it" — distinguishes automated vault writes (task events, session checkpoints, which happen via hooks) from explicit architectural notes (which require agent action).

2. Add consumer-driven rule as a callout below the table:

> "Vault = consumer is human (Obsidian-readable narrative, long-form). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read this note. Both systems for architectural decisions with lasting human relevance."

### D. Arrival gap note (`goldfish/CLAUDE.md`)

Add one line in the session start sequence:

> "GitNexus/Semble load on-demand — intentional just-in-time delivery, not a gap. Targeted context arrives exactly when the relevant question is asked."

## Section 2 — Diagnostic Framework Tightening (`docs/memory-diagnostic.md`)

### Amended failure mode descriptions

**Arrival gap** — add qualifier to diagnostic question:
> *(just-in-time on-demand delivery counts as arrival; pre-loading is not required if targeted delivery is the architectural intent)*

**Dark corner** — add "justified absence" concept to scoring rubric notes:
> A context type is NOT a dark corner if: (a) it is re-derivable on demand in <1 second, and (b) a CLI diagnostic command exists. Document the CLI, close the finding.

**Stale signal** — add clarifying note:
> A "verify before acting" instruction in the agent's constitution is a valid validation mechanism. Absence of an automated cadence is not automatically YELLOW.

### Updated Current State Assessment

| Failure | Score | Key Evidence |
|---------|-------|-------------|
| Routing fog | 🟡 YELLOW | Read-side tiebreaker added; omega_profile supplemental framing in place |
| Dark corner | 🟢 GREEN | Tools assumed installed; `goldfish doctor` CLI is the diagnostic path — justified absence |
| Arrival gap | 🟢 GREEN | On-demand = just-in-time; intentional architectural design, documented |
| Stale signal | 🟢 GREEN | "Verify code claims before acting" instruction is the validation cadence |
| Boundary blur | 🟡 YELLOW | Consumer-driven rule added; explicit vs automatic vault write distinction in place |
| Instruction fiction | 🟡 YELLOW | PreCompact flow fixed; ongoing vigilance as code evolves |

**Summary: 0 RED / 3 YELLOW / 3 GREEN**

## Section 3 — OMEGA Decision Reinforcement

Store five decisions with type `"decision"`:

1. **Arrival gap closed**: GitNexus/Semble load on-demand by design — just-in-time delivery of targeted context, not a gap. Arrival gap diagnostic scores GREEN for this architecture.

2. **Dark corner closed**: Tool health state has no persistent memory home by design. Tools assumed installed; `goldfish doctor` CLI handles diagnosis. Re-derivation <1s. Dark corner diagnostic scores GREEN for this architecture.

3. **Boundary blur rule**: Vault vs OMEGA routing is consumer-driven. Vault = human consumer (Obsidian-readable narrative). OMEGA = agent consumer (machine-queryable, episodic). Architectural decisions may warrant both; session facts warrant OMEGA only.

4. **Routing fog tiebreaker**: For user preference reads, auto-memory (`memory/*.md`) is authoritative. `omega_profile()` is supplemental — additional signal, not ground truth. Auto-memory wins on conflicts.

5. **Instruction fiction guard**: PreCompact no longer calls `omega flush` — removed in goldfish v1.0 polish. PreCompact writes vault checkpoint via `vault.write()` only. Any doc showing `omega flush` in PreCompact flow is stale.

## Success Criteria

- `/goldfish-diagnostic` Run 4 scores 0 RED / 3 YELLOW / 3 GREEN
- No `omega flush` references remain in docs or instruction blocks
- `_CLAUDE_MD_BLOCK` in `init.py` matches `goldfish/CLAUDE.md` exactly
- Five OMEGA decisions stored and queryable
- Stale reference sweep complete, findings documented or fixed
