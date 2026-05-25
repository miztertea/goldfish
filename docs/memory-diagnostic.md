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
