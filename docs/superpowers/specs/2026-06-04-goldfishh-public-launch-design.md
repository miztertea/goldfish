# goldfishh Public Launch Design

**Date:** 2026-06-04  
**Status:** Approved

## Overview

goldfishh is now on PyPI and the repo is public. This spec covers the full rebrand from `goldfish` → `goldfishh` (the PyPI package name is already `goldfishh`; the CLI command and Python module are being unified to match), plus public-facing polish: README, pyproject metadata, and a CLAUDE.md routing rule tightening.

## Scope

### 1 — Full Rebrand: `goldfish` → `goldfishh`

**What changes:**

| Surface | From | To |
|---------|------|----|
| Python module directory | `src/goldfish/` | `src/goldfishh/` |
| Python imports | `from goldfish.xxx import yyy` | `from goldfishh.xxx import yyy` |
| CLI script entry (pyproject.toml) | `goldfish = "goldfish.cli:app"` | `goldfishh = "goldfishh.cli:app"` |
| pyproject `packages` | `["src/goldfish"]` | `["src/goldfishh"]` |
| CLI executable | `goldfish` | `goldfishh` |
| Vault/config root | `~/.goldfish/` | `~/.goldfishh/` |
| VAULTS_ROOT constant | `Path.home() / ".goldfish"` | `Path.home() / ".goldfishh"` |
| CLAUDE.md sentinel | `"managed by goldfish"` | `"managed by goldfishh"` |
| Binary detection paths | `~/.local/bin/goldfish` | `~/.local/bin/goldfishh` |
| Hook commands | `goldfish hook` | `goldfishh hook` |
| Hook detection | `"goldfish" in cmd` | `"goldfishh" in cmd` |
| Branding in docs/prints | `goldfish` | `goldfishh` |
| Tests imports/fixtures | `from goldfish.xxx` | `from goldfishh.xxx` |

**What does NOT change:**
- GitHub repo name stays `miztertea/goldfish` (renaming breaks existing links/forks)
- No vault data migration — no existing users to migrate

**Migration concerns for re-init users:**
- `upsert_goldfish_block()` must detect and remove the OLD sentinel (`"managed by goldfish"`) before inserting the new one to prevent duplicate blocks in CLAUDE.md
- `_is_goldfishh_hook()` (was `_is_goldfish_hook`) must also match old `"goldfish hook"` patterns during `register_hooks` to strip stale entries

### 2 — pyproject.toml Metadata

Add to `[project]`:
```toml
description = "Persistent memory for Claude Code — installs and wires GitNexus, OMEGA, and Semble"
readme = "README.md"
keywords = ["claude-code", "ai-memory", "llm-agent", "gitnexus", "omega"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.13",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
```

Python version stays `==3.13.*` — intentional pin because `chonkie` is incompatible with Python 3.14.

### 3 — README Updates

**Quick start (replace git-based install):**
```bash
# Prerequisites: Python 3.13, Node.js 18+, uv
uvx goldfishh init
```

```bash
# Or install persistently:
uv tool install goldfishh
goldfishh init
```

Note: pin is Python 3.13 because chonkie (required dependency) is incompatible with 3.14.

**Platform badges:** Linux, macOS (primary); Windows (beta)

**Platform support section:** "Tested on Ubuntu 26.04 LTS. Expected to work on macOS. Windows support is beta — CI runs on Windows but clean-install verification is pending."

**Python prerequisites:** Call out 3.13 explicitly and explain the pin.

**CLI reference:** All `goldfish <cmd>` → `goldfishh <cmd>`

**h1 and all brand references:** `goldfish` → `goldfishh`

### 4 — CLAUDE.md Routing Rule Tightening

**Location:** goldfish coordination block (`_CLAUDE_MD_BLOCK` in `init.py` and `CLAUDE.md`)

**Current text:**
> Architectural decisions may warrant both; session facts warrant OMEGA only.

**Replace with:**
> Architectural decisions may warrant both — write vault when a human should find and read this later (narrative, rationale, context for future contributors); OMEGA only when the consumer is the agent (facts, decisions, lessons). Session facts: OMEGA only.

**Both files must be updated:** `CLAUDE.md` (goldfish project) and `_CLAUDE_MD_BLOCK` in `init.py` (injected into downstream projects). These must stay in sync.

### 5 — GitHub Repository Description

Update via `gh repo edit`:
- **Description:** "Persistent memory for Claude Code — one command installs GitNexus, OMEGA, and Semble"
- **Topics:** `claude-code`, `ai-memory`, `llm-agent`, `python`, `developer-tools`

## Files Changed

| File | Type | Reason |
|------|------|--------|
| `src/goldfish/` → `src/goldfishh/` | Rename dir + all files | Python module rebrand |
| `src/goldfishh/*.py` | Edit | Update imports and `goldfish` references |
| `tests/*.py` | Edit | Update imports |
| `pyproject.toml` | Edit | Script entry, packages, metadata, classifiers |
| `src/goldfishh/claude_md.py` | Edit | Binary detection, sentinel, hook detection |
| `src/goldfishh/init.py` | Edit | Binary paths, vault root, _CLAUDE_MD_BLOCK routing rule |
| `CLAUDE.md` | Edit | CLI references, routing rule, branding |
| `docs/architecture.md` | Edit | `goldfish hook` → `goldfishh hook` in diagrams |
| `docs/memory-diagnostic.md` | Edit | `goldfish doctor` → `goldfishh doctor` |
| `README.md` | Edit | Quick start, platform, CLI reference, branding |
| `AGENTS.md` | Edit | CLI references and branding |
| `CONTRIBUTING.md` | Edit | CLI references and branding |
| `docs/five-failures.md` | Edit | Project name references |
| `docs/tool-selection.md` | Edit | Project name references |

## Success Criteria

- `uvx goldfishh init` works on a fresh machine (Python 3.13)
- `uv tool install goldfishh && goldfishh init` works
- PyPI page shows description and README
- All tests pass with renamed module
- CLAUDE.md blocks generated by `goldfishh init` say "managed by goldfishh" and contain updated routing rule
- Re-running `goldfishh init` on a project with old "managed by goldfish" block removes old block and inserts new one (no duplicates)
- GitHub repo shows updated description and topics

## Out of Scope

- Renaming the GitHub repo (`miztertea/goldfish` stays)
- Vault data migration (no existing users)
- Python version change (3.13 pin is intentional)
