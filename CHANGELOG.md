# Changelog

All notable changes to goldfish are documented here.
Generated automatically by [git-cliff](https://git-cliff.org).

## [0.10.0] - 2026-06-04

### Bug Fixes

- Correct Layer 1 activation note and split omega session start steps
- Update _CLAUDE_MD_BLOCK with memory division, session-start clarification, layer boundary
- Correct _CLAUDE_MD_BLOCK opening sentence and tighten memory division note
- Tighten CLAUDE.md layers — remove hook routing, refresh goldfish block, drop orphaned gitnexus duplicate
- Move 'What goldfish contributes' and 'Further reading' to Layer 3 in AGENTS.md
- Correct Layer 1 handoff line — only GitNexus injects below, OMEGA/Semble via MCP context
- Update goldfish CLAUDE.md — layer table split, Memory Router, omega_protocol framing
- Sync _CLAUDE_MD_BLOCK in init.py with updated CLAUDE.md
- Close remaining diagnostic gaps — four-layer arch doc, subagent MCP note, stale module count
- Remove stale omega flush from PreCompact flow in architecture.md
- Tighten Memory Router — routing fog tiebreaker, boundary blur rule, arrival gap note, GitNexus staleness cadence
- Sync _CLAUDE_MD_BLOCK in init.py with updated CLAUDE.md
- Update README — reflect four-layer architecture model
- Correct repo name typo in plan Task 11 (miztertee → miztertea)
- Catch FileNotFoundError in check_dependency for missing commands
- Three Windows/macOS CI failures
- Harden Windows npm crash, register gitnexus MCP explicitly, remove duplicate claude-review job
- Reconfigure stdout/stderr to UTF-8 on Windows at CLI startup
- Comprehensive Windows compat — _run() helper, UTF-8 encoding everywhere, sequential CI
- Suppress bandit B602 on intentional shell=True in _run()
- Skip self-install when goldfish already on PATH (Windows Access Denied)
- Guard release against empty NEW_TAG; add [bump] section to cliff.toml
- Replace git-cliff --bumped-version with bash version computation
- Restore git-cliff --bumped-version; add GITHUB_TOKEN to fix empty output
- Work around git-cliff-action jq parse error in --bumped-version step
- Extract version from CHANGELOG instead of --bumped-version

### Documentation

- Add instruction architecture design spec (four-layer stack)
- Fix three accuracy issues in instruction architecture spec
- Add instruction architecture implementation plan
- Add layer boundary markers to CLAUDE.md
- Strip Layer 1 tool blocks from AGENTS.md, add pointer to CLAUDE.md
- Add layer boundary markers to AGENTS.md, embrace GitNexus auto-management
- Update spec with post-implementation notes and Task 4 revision
- Add layer-tightening design spec
- Add layer-tightening implementation plan
- Add memory diagnostic framework design spec
- Add memory diagnostic framework implementation plan
- Add Six Memory Failure Modes framework document
- Add memory tuning design spec — diagnostic run 3 fixes
- Add GitNexus staleness section to memory tuning spec
- Add memory tuning implementation plan
- Tighten memory-diagnostic framework + update Run 4 scorecard
- Add CI/CD pipeline design spec
- Update CI/CD spec — changelog, branch rulesets, roadmap, dev containers
- Replace devcontainer phase with act-based local CI
- Fix 9 design bugs found in multi-angle spec review
- Restore hatch-vcs, replace PSR with git-cliff
- Add container testing research findings + uvbox distribution note
- Document why Linux-local testing is sufficient for goldfish
- Add CI/CD pipeline implementation plan (11 tasks, 4 phases)
- Add CONTRIBUTING.md with branch, worktree, and commit conventions
- Add CONTRIBUTING.md with branch, worktree, and commit conventions
- Add ROADMAP.md with current focus and long-term direction

### Features

- Update _CLAUDE_MD_BLOCK to four-layer model with session start sequence
- Auto-install Claude Code in goldfish init when missing

### Testing

- Add failing test for four-layer _CLAUDE_MD_BLOCK

### Style

- Apply ruff format to test assertion
## [0.9.6] - 2026-05-25

### Documentation

- Archive PRD and DESIGN-COMPANION to docs/internal/
- Add five-failures.md standalone reference
- Add architecture.md from PRD system architecture sections
- Add tool-selection.md with gates and evaluation record
- Add design-decisions.md condensed from DESIGN-COMPANION Part 12
- Add obsidian.md optional viewer guide
- Trim CLAUDE.md to Layer 3 operational content, fix layer ordering
- Rewrite AGENTS.md as Layer 3 agent constitution with superpowers workflow
- Rewrite README — hero image, quick start first, three-layer model, platform note
- Add CONTRIBUTING.md for human contributors
- Add SECURITY.md with responsible disclosure process

### Refactoring

- Optimize _CLAUDE_MD_BLOCK to Layer 2 coordination only — remove per-tool API signatures
## [0.9.5] - 2026-05-24

### Bug Fixes

- Drain.py safe queue processing and error handling
- Detect full goldfish binary path at hook registration time
- Detect goldfish path once per register_hooks call
- Correct wake-up frontmatter date format and guard omega mine
- Register_hooks upserts full path, registers all 9 hook events
- Tighten _is_goldfish_hook, fix set equality test, fix preservation test event
- Init sets bootstrap_complete, handles subprocess failures gracefully
- Handle FileNotFoundError when omega/semble not installed
- Remove chonkie direct dep — transitive via semble, Python 3.14 incompatible
- Use sys.executable -m pip for omega install, works in uvx env
- Update test to match sys.executable -m pip install pattern
- Test captures full cmd lists to find omega-memory arg
- Install omega-memory via uv tool install, consistent with semble
- Catch FileNotFoundError in MCP registration calls
- Add missing Agent Knowledge Tools heading to CLAUDE.md block
- Filter to .md files only and use consistent encoding in wake-up reads
- Write semble_indexed_at in post_tool_use reindex, use UTC-aware datetime
- Reset replay resume state if resume file no longer exists
- Catch FileNotFoundError in doctor OMEGA check
- Add Path.home patch to venv bin path test
- Correct omega MCP key name to omega-memory in doctor
- Run omega setup --download-model before client registration; remove Obsidian ref
- Replace deprecated datetime.utcnow() with datetime.now(UTC)
- Use shutil.which for semble check (--version flag not supported)
- Install omega-memory[server] extra to include mcp package for MCP server
- Read hook_event_name and transcript_path from real Claude Code event payloads
- Semble vault search flag and add chonkie dependency
- Remove duplicate CLAUDE.md goldfish block, add semble init
- Remove type field fallback from hook.py event routing
- Pin Python to 3.13 so uvx resolves the right runtime
- Re-read manifest before each write and document list-content skip
- Resolve final review issues — DEFAULT_SETTINGS source, double read, silent timeout

### Documentation

- Write proper README and add Phase 9 plan
- Add goldfish v1.0 design spec
- Add goldfish v1.0 implementation plan
- Rewrite README against current architecture and spec
- Add verified tool references for semble/omega/gitnexus and v1.0 polish plan
- Add goldfish mine design spec
- Add goldfish mine implementation plan
- Update README — goldfish mine, fix stale counts and hook table
- Clarify PostToolUse hook registration vs handler status in CLAUDE.md

### Features

- Hook.py appends events to queue.jsonl
- Drain.py reads queue and dispatches to semble subprocess
- Config.py with manifest read/write and project identity
- Vault.py with scaffold, write_note, read_note
- Typer CLI with hook, drain, and stub commands
- Claude_md.py registers hooks in settings.json idempotently
- Init wizard installs GitNexus, OMEGA, Semble, scaffolds vault
- SessionStart and PreCompact sync handlers with wake-up note
- Hook.py sync/async dispatch with stdout for sync events
- Stop handler advances manifest offset
- Enricher.py — Chonkie decomposition and Semble fan-out
- Goldfish status command
- Goldfish doctor command
- Goldfish replay command — rebuilds vault from JSONL transcripts
- Time-budgeted drain with auto-trigger in SessionStart and PreCompact
- Enricher fans out to OMEGA memory layer alongside Semble
- Idempotent init — skips already-installed tools, status output
- Prefer ~/.local/bin/goldfish for stable hook path
- Self-install goldfish as stable uv tool during init
- Register MCP servers for GitNexus, OMEGA, and Semble during init
- Update CLAUDE.md block to reference MCP tool names
- Add open tasks and recent decisions to session wake-up
- Write semble_indexed_at to manifest after index
- Add Semble check, MCP registration check, and vault health to doctor
- Add replay resumability with last_byte_offset tracking
- Add mined_sessions to manifest defaults
- Add miner.py — replay JSONL sessions through OMEGA hooks
- Add goldfish mine CLI command
- Call mine_project on init for existing projects

### Refactoring

- Drain.py event-type routing with async handlers
- Clean up drain.py imports and remove wrapper indirection
- Simplify hook routing condition
- Replay — module-level imports, stronger route assertion in test
- Remove dead CLI calls from drain.py

### Testing

- UserPromptSubmit, PostToolUse, and task lifecycle coverage
- Comprehensive append_claude_md_block update-in-place coverage
- Simplify _detect_goldfish_bin mock to patch only Path.home
- Update events to use hook_event_name field
- Remove dead-code tests and fix assertions after drain.py cleanup
- Add mine command error-path coverage

