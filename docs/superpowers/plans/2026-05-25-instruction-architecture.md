# Instruction Architecture Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the four-layer instruction architecture across `_CLAUDE_MD_BLOCK`, `CLAUDE.md`, and `AGENTS.md`.

**Architecture:** Three files change. `_CLAUDE_MD_BLOCK` in `init.py` gets the new four-layer table and session start sequence. `CLAUDE.md` gets visual layer separators between Layers 2 and 3. `AGENTS.md` has the duplicated GitNexus block stripped and replaced with a pointer to `CLAUDE.md`. No changes to `claude_md.py` or the `GOLDFISH_SENTINEL` string.

**Tech Stack:** Python 3.13, pytest, pathlib. No new dependencies.

---

### Task 1: Write failing test for updated `_CLAUDE_MD_BLOCK` content

**Files:**
- Modify: `tests/test_init.py`

The current `_CLAUDE_MD_BLOCK` describes "three intelligence layers." The new block must describe four layers, include a session start sequence, and reference `omega_welcome()`. Write the test before touching `init.py`.

- [ ] **Step 1: Add the failing test to `tests/test_init.py`**

Add at the end of the file:

```python
def test_claude_md_block_describes_four_layer_stack():
    from goldfishh.init import _CLAUDE_MD_BLOCK
    assert "Layer 0" in _CLAUDE_MD_BLOCK, "Must reference Layer 0 (MEMORY.md)"
    assert "MEMORY.md" in _CLAUDE_MD_BLOCK, "Must name MEMORY.md explicitly"
    assert "omega_welcome()" in _CLAUDE_MD_BLOCK, "Session start must call omega_welcome()"
    assert "Session Start" in _CLAUDE_MD_BLOCK, "Must have Session Start section"
    assert "Layer 1" in _CLAUDE_MD_BLOCK, "Must reference Layer 1 (tool blocks)"
    assert "Layer 2" in _CLAUDE_MD_BLOCK, "Must reference Layer 2 (goldfishh)"
    assert "Layer 3" in _CLAUDE_MD_BLOCK, "Must reference Layer 3 (project)"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/tchawes/goldfishh && python -m pytest tests/test_init.py::test_claude_md_block_describes_four_layer_stack -v
```

Expected output: `FAILED tests/test_init.py::test_claude_md_block_describes_four_layer_stack`
Expected failure message: `AssertionError: Must reference Layer 0 (MEMORY.md)`

- [ ] **Step 3: Run the full test suite to confirm baseline**

```bash
cd /home/tchawes/goldfishh && python -m pytest --tb=short -q
```

Expected: All existing tests pass (only the new test fails).

- [ ] **Step 4: Commit the failing test**

```bash
git add tests/test_init.py
git commit -m "test: add failing test for four-layer _CLAUDE_MD_BLOCK"
```

---

### Task 2: Update `_CLAUDE_MD_BLOCK` in `src/goldfishh/init.py`

**Files:**
- Modify: `src/goldfishh/init.py:25-42`

Replace the `_CLAUDE_MD_BLOCK` string. The sentinel heading (`GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfishh)"`) stays unchanged — `append_claude_md_block` uses it as the match key.

- [ ] **Step 1: Replace `_CLAUDE_MD_BLOCK` in `src/goldfishh/init.py`**

Replace lines 25–42 (the entire `_CLAUDE_MD_BLOCK = f"""..."""` block):

```python
_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

goldfishh wires together four layers of agent intelligence. All four activate at session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| 0 — MEMORY.md | Static baseline: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| 1 — Tool blocks | GitNexus (code), OMEGA (episodic), Semble (semantic) — auto-maintained | Call omega_welcome() |
| 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

### Session Start (required)

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` → `omega_protocol()` — activates episodic context
3. Check for applicable skills before any response
4. Work begins

### Before Any Non-Trivial Task

Query all three intelligence tools:
- GitNexus — call graph, blast radius, execution flows
- OMEGA — prior decisions, session history, known issues
- Semble — code by meaning, vault notes

Each tool's full usage instructions are in its own maintained section in this file.
"""
```

- [ ] **Step 2: Run the new test to verify it passes**

```bash
cd /home/tchawes/goldfishh && python -m pytest tests/test_init.py::test_claude_md_block_describes_four_layer_stack -v
```

Expected: `PASSED`

- [ ] **Step 3: Run the full test suite**

```bash
cd /home/tchawes/goldfishh && python -m pytest --tb=short -q
```

Expected: All tests pass. Count should be unchanged from baseline (one new test added in Task 1, now passing).

- [ ] **Step 4: Commit**

```bash
git add src/goldfishh/init.py
git commit -m "feat: update _CLAUDE_MD_BLOCK to four-layer model with session start sequence"
```

---

### Task 3: Add layer separators to `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

The file currently has three logical layers with no visual boundaries. Add a `<!-- layer 3: project -->` comment and `---` rule before the Layer 3 project section (top of file), and a `<!-- layer 2: goldfishh — do not edit, maintained by goldfishh -->` comment before the goldfishh block. Layer 1 (GitNexus) already has `<!-- gitnexus:end -->` — add `<!-- layer 1: tool blocks — do not edit, maintained by tools -->` before it.

No content is moved or rewritten in this task — only separators are added.

- [ ] **Step 1: Add layer markers to `CLAUDE.md`**

The file currently starts with `# CLAUDE.md`. Add the Layer 3 marker at the very top:

```
<!-- layer 3: project — maintained by project team -->

# CLAUDE.md
```

Before the line `## Agent Knowledge Tools (managed by goldfishh)`, add the Layer 2 marker:

```
---

<!-- layer 2: goldfishh — do not edit, maintained by goldfishh init -->

## Agent Knowledge Tools (managed by goldfishh)
```

Before the `## Always Do` section (which is the start of the GitNexus tool block), add the Layer 1 marker:

```
---

<!-- layer 1: tool blocks — do not edit, maintained by each tool -->

## Always Do
```

- [ ] **Step 2: Verify the file renders as expected**

```bash
grep -n "layer 1\|layer 2\|layer 3\|gitnexus:end" /home/tchawes/goldfishh/CLAUDE.md
```

Expected output (approximate line numbers):
```
1:<!-- layer 3: project — maintained by project team -->
55:<!-- layer 2: goldfishh — do not edit, maintained by goldfishh init -->
74:<!-- layer 1: tool blocks — do not edit, maintained by each tool -->
110:<!-- gitnexus:end -->
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add layer boundary markers to CLAUDE.md"
```

---

### Task 4: Rewrite `AGENTS.md` — strip Layer 1, keep Layers 2-3

**Files:**
- Modify: `AGENTS.md`

Currently `AGENTS.md` ends with a duplicated copy of the GitNexus block (lines 62–106, from `<!-- gitnexus:start -->` to `<!-- gitnexus:end -->`). Remove it and replace with a one-line pointer. The project constitution content (lines 1–60) stays unchanged.

- [ ] **Step 1: Remove the GitNexus block from `AGENTS.md` and add pointer**

Delete everything from `<!-- gitnexus:start -->` to the end of file. Replace with:

```markdown
---

## Tool-Specific Instructions (Layer 1)

GitNexus, OMEGA, and Semble each maintain their own instruction blocks automatically. These are kept current in `CLAUDE.md` by each tool's CLI. If you are using Claude Code, those blocks are already in your context. If you are using another agent, read the relevant sections from `CLAUDE.md` directly.
```

- [ ] **Step 2: Verify AGENTS.md no longer contains gitnexus block content**

```bash
grep -n "gitnexus:start\|gitnexus:end\|MUST run impact" /home/tchawes/goldfishh/AGENTS.md
```

Expected: No output (zero matches).

- [ ] **Step 3: Verify AGENTS.md still contains the five failures and constraints**

```bash
grep -n "five failures\|Non-negotiable\|Superpowers workflow" /home/tchawes/goldfishh/AGENTS.md
```

Expected: Three matches, confirming the project constitution content is intact.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs: strip Layer 1 tool blocks from AGENTS.md, add pointer to CLAUDE.md"
```

---

### Task 5: Manual step — update global `~/.claude/CLAUDE.md`

**Files:**
- `~/.claude/CLAUDE.md` (user's private global config — NOT touched by goldfishh)

goldfishh cannot write to this file. The user must update it manually after this implementation is complete.

- [ ] **Step 1: Note the required manual change**

The global `~/.claude/CLAUDE.md` currently instructs the agent to call `omega_welcome()` and `omega_protocol()` at session start. With the four-layer model, this instruction now lives in the Layer 2 goldfishh block of each project's `CLAUDE.md`. The global file's session-start rule can be simplified to a short pointer.

Open `~/.claude/CLAUDE.md` and find the `## Memory (OMEGA)` section. The existing rule is correct and does not contradict the new model — the new Layer 2 block in each project reinforces it. No breaking change. This is an optional cleanup: the user may simplify the global rule to remove redundancy, but it is not required for the system to work correctly.

Document this in the spec by appending the following section to `docs/superpowers/specs/2026-05-25-instruction-architecture-design.md` using the Edit tool:

```
## Post-Implementation Note

The global ~/.claude/CLAUDE.md OMEGA startup rule is now reinforced by the Layer 2 goldfishh block
in every project. No breaking change. The global rule may be simplified to remove redundancy,
but is not required for the system to work correctly.
```

- [ ] **Step 2: Commit the spec note**

```bash
git add docs/superpowers/specs/2026-05-25-instruction-architecture-design.md
git commit -m "docs: note manual global CLAUDE.md step as optional cleanup post-implementation"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd /home/tchawes/goldfishh && python -m pytest --tb=short -q
```

Expected: All tests pass.

- [ ] **Step 2: Verify layer structure across all three files**

```bash
grep -n "layer 0\|layer 1\|layer 2\|layer 3\|Layer 0\|Layer 1\|Layer 2\|Layer 3" /home/tchawes/goldfishh/CLAUDE.md /home/tchawes/goldfishh/AGENTS.md /home/tchawes/goldfishh/src/goldfishh/init.py
```

Expected: Hits in all three files. `CLAUDE.md` has the comment markers. `AGENTS.md` has "Layer 1" in the pointer section. `init.py` has all four layers in `_CLAUDE_MD_BLOCK`.

- [ ] **Step 3: Verify GitNexus block is only in CLAUDE.md, not AGENTS.md**

```bash
grep -l "gitnexus:end" /home/tchawes/goldfishh/CLAUDE.md /home/tchawes/goldfishh/AGENTS.md
```

Expected: Only `CLAUDE.md` is listed.

- [ ] **Step 4: Verify `append_claude_md_block` still works with new block**

```bash
cd /home/tchawes/goldfishh && python -c "
from goldfishh.init import _CLAUDE_MD_BLOCK
from goldfishh.claude_md import GOLDFISH_SENTINEL, append_claude_md_block
import tempfile, pathlib
with tempfile.NamedTemporaryFile(suffix='.md', delete=False, mode='w') as f:
    f.write('# Test\n')
    tmp = f.name
p = pathlib.Path(tmp)
append_claude_md_block(p, _CLAUDE_MD_BLOCK)
content = p.read_text()
assert GOLDFISH_SENTINEL in content, 'sentinel missing'
assert 'omega_welcome()' in content, 'session start missing'
assert 'Layer 0' in content, 'layer 0 missing'
print('OK — block installs correctly')
"
```

Expected: `OK — block installs correctly`
