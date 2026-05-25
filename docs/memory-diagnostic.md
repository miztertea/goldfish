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

### Goldfish Architecture Notes

These qualifiers apply when scoring goldfish's instruction set specifically:

**Arrival gap:** Just-in-time on-demand delivery counts as arrival — pre-loading is not required if targeted delivery is the architectural intent. GitNexus/Semble loading on-demand when a code question is asked satisfies the arrival gap criterion.

**Dark corner:** A context type is NOT a dark corner if: (a) it is re-derivable on demand in <1 second, and (b) a CLI diagnostic command exists (e.g., `goldfish doctor`). Document the CLI, close the finding. Tool health state meets both criteria.

**Stale signal:** A "verify before acting" instruction in the agent's constitution is a valid validation mechanism. Absence of an automated cadence is not automatically YELLOW if explicit verification is instructed.

---

## Scoring Rubric

- 🟢 **GREEN** — no instances found in current instruction set
- 🟡 **YELLOW** — partial coverage, edge cases, or judgment-dependent gaps
- 🔴 **RED** — structural gap — agents will misroute without correction

---

## Current State Assessment

*Updated by `/goldfish-diagnostic` each time it runs.*

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

---

## Further Reading

- `docs/five-failures.md` — agent context failure modes (the original framework)
- `docs/architecture.md` — runtime flows and layer wiring
- `.claude/skills/goldfish-diagnostic/SKILL.md` — how to run the diagnostic
