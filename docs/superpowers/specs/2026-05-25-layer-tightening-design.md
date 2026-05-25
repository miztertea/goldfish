# Layer Tightening Design

**Date:** 2026-05-25  
**Scope:** Full 3-file audit — `src/goldfish/init.py`, `CLAUDE.md`, `AGENTS.md`  
**Goal:** All context layers work in concert: no redundancy, clear boundaries, explicit memory division, unambiguous session start ordering.

---

## Problems Being Solved

Five issues identified through post-implementation context review:

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | GitNexus block duplicated verbatim | `CLAUDE.md` Layer 1 | Token waste, ambiguity about which is authoritative |
| 2 | Two memory systems (OMEGA + file-based) with no stated division | `_CLAUDE_MD_BLOCK` | Agent may conflate or misuse them |
| 3 | Session start ordering conflict: OMEGA-first vs superpowers skill-check-first | `_CLAUDE_MD_BLOCK` | Ambiguity about which runs first |
| 4 | Layer 1/2 boundary not visible in rendered context | `CLAUDE.md` | Agent can't tell where goldfish coordination ends and tool blocks begin |
| 5 | Hook routing table is developer docs, not agent instruction | `CLAUDE.md` Layer 3 | Loads every session for information an agent never acts on |

Bonus: `_CLAUDE_MD_BLOCK` in `init.py` has drifted from what's actually in `CLAUDE.md` — resync required.

---

## Design

### Fix 1 — Remove orphaned GitNexus block from CLAUDE.md

**Root cause:** At some point the `<!-- gitnexus:start -->` marker was stripped from the first block, leaving orphaned content (no open marker, just a `gitnexus:end`). GitNexus then wrote a fresh properly-marked second block below it.

**Fix:** Delete lines 79–116 of `CLAUDE.md` (the orphaned block without a `gitnexus:start`). Move the `<!-- layer 1: tool blocks -->` comment to sit directly above the properly-marked block (lines 118–160). The result is one clean pair: `gitnexus:start` → content → `gitnexus:end`.

**Invariant:** Never touch content inside `<!-- gitnexus:start/end -->` — GitNexus owns that.

---

### Fix 2+3+4 — New `_CLAUDE_MD_BLOCK` (source of truth in `init.py`)

Replace the current `_CLAUDE_MD_BLOCK` string in `src/goldfish/init.py` with:

```
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
```

**What this fixes:**
- Issue 2: Explicit "Memory systems" note distinguishes MEMORY.md (static, Layer 0) from OMEGA (episodic MCP, Layer 1)
- Issue 3: "Steps 2–3 are initialization calls, not task responses" resolves the ordering conflict with using-superpowers
- Issue 4: Closing line "…in its own auto-maintained block below (Layer 1)" makes the Layer 2→1 handoff explicit in rendered context

**After updating `init.py`:** Re-apply to `CLAUDE.md` by manual replacement — edit the content between the goldfish sentinel (`## Agent Knowledge Tools (managed by goldfish)`) and the `<!-- layer 1: tool blocks -->` comment. Manual edit is preferred here because the same pass fixes the orphaned gitnexus block and removes the hook routing section; doing all three edits together avoids multiple file rewrites.

---

### Fix 5 — Delete hook routing table from CLAUDE.md

Remove this section from `CLAUDE.md` Layer 3:

```markdown
## Hook event routing

Synchronous (Claude waits for stdout): `SessionStart`, `UserPromptSubmit`, `PreCompact`
Async (`async: true`): `PostToolUse`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `SessionEnd`

goldfish registers `PostToolUse` so GitNexus hooks coexist cleanly. GitNexus registers its own `PreToolUse` and `PostToolUse` during `gitnexus analyze` — both sets coexist without conflict.
```

**Rationale:** This is implementation detail an agent never acts on. It already exists in `docs/architecture.md` (lines 115, 124). Removing it reduces per-session token load with no information loss.

---

### AGENTS.md Layer Boundary Correction

**Current problem:** "What goldfish contributes" and "Further reading" sit inside the `<!-- layer 2: goldfish -->` block, but they're project-level facts — Layer 3 material.

**Fix:** Move those two sections above the layer 2 comment marker so Layer 3 is self-contained.

**Target structure:**

```
<!-- layer 3: project — maintained by project team -->

## What you're working in        ← project fact
## The five failures              ← project fact
## Non-negotiable constraints     ← project fact
## What goldfish contributes      ← MOVED HERE (was in layer 2)
## Further reading                ← MOVED HERE (was in layer 2)

---

<!-- layer 2: goldfish — superpowers workflow for contributors -->

## Superpowers workflow (required for all contributors)   ← goldfish coordination only

---

## Tool-Specific Instructions (Layer 1)
<!-- layer 1: tool blocks — do not edit, maintained by each tool -->
<!-- gitnexus:start -->
[single gitnexus block — unchanged]
<!-- gitnexus:end -->
```

**Principle:** Layer 3 = what this project is and its constraints. Layer 2 = how goldfish coordinates the agent's workflow. Layer 1 = tool-native auto-maintained blocks.

---

## Files Changed

| File | Change |
|------|--------|
| `src/goldfish/init.py` | Replace `_CLAUDE_MD_BLOCK` string with new version |
| `CLAUDE.md` | Delete hook routing section; replace goldfish block with new content; remove orphaned gitnexus block |
| `AGENTS.md` | Move "What goldfish contributes" + "Further reading" above layer 2 marker |

No logic changes. No new functions. All changes are string content in files.

---

## What Stays the Same

- `claude_md.py` logic — `append_claude_md_block` and `register_hooks` are unchanged
- `GOLDFISH_SENTINEL` value — changing it would break existing installs
- All gitnexus block content — owned by GitNexus, never touched
- Layer numbering (0–3) — stable across the system
- AGENTS.md Layer 1 — single properly-marked gitnexus block, correct as-is

---

## Success Criteria

After implementation:
- `CLAUDE.md` has exactly one `gitnexus:start/end` pair
- `CLAUDE.md` has no hook routing section
- `_CLAUDE_MD_BLOCK` in `init.py` matches what appears in `CLAUDE.md`'s goldfish block
- An agent reading `CLAUDE.md` can distinguish MEMORY.md from OMEGA without inferring
- An agent reading `CLAUDE.md` understands OMEGA calls are initialization, not task responses
- An agent reading `CLAUDE.md` can identify where Layer 2 ends and Layer 1 begins
- `AGENTS.md` Layer 2 contains only goldfish workflow coordination (no project facts)
