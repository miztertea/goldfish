# OMEGA — Episodic Memory for AI Agents

> Local-first persistent memory system. No cloud. No daemon. Single SQLite database.

**Source:** https://omegamax.co/docs/  
**Install:** `uv tool install "omega-memory[server]"` (the `[server]` extra includes the `mcp` package)  
**Package:** `omega-memory` on PyPI

---

## Architecture

- **Storage:** `~/.omega/omega.db` (SQLite, single file)
- **Embeddings:** bge-small-en-v1.5, 384 dimensions, ONNX CPU-only (~90MB model, ~337MB RAM post-init)
- **Search:** 70% vector similarity (cosine via sqlite-vec) + 30% BM25 (FTS5)
- **MCP:** stdio server, spawned on-demand, 3600s idle timeout
- **No daemon** — server process exits when idle

**Data paths:**
| Path | Purpose |
|------|---------|
| `~/.omega/omega.db` | All memories, edges, embeddings |
| `~/.omega/profile.json` | User profile (name, timezone, role) |
| `~/.omega/secrets.json` | Router API keys (chmod 600) |
| `~/.omega/hooks.log` | Hook error log |
| `~/.omega/documents/` | Auto-ingestion folder |
| `~/.omega/backups/` | Weekly auto-backups |
| `~/.cache/omega/models/` | ONNX model files |

**Environment variables:**
| Variable | Default | Purpose |
|----------|---------|---------|
| `OMEGA_HOME` | `~/.omega` | Relocate storage directory |
| `OMEGA_IDLE_TIMEOUT` | `3600` | MCP server idle timeout (seconds) |
| `OMEGA_MODE` | `solo` | Tool surface profile |

---

## Memory Types & TTLs

| Type | TTL | Priority |
|------|-----|---------|
| `decision` | Permanent | High |
| `lesson_learned` | Permanent | High |
| `error_pattern` | Permanent | High |
| `user_preference` | Permanent | High |
| `task_completion` | 180 days | Medium |
| `session_summary` | 1 day | Low |
| `checkpoint` | 7 days | Low |

---

## CLI Commands

### Setup & Health

```bash
omega setup                          # Full setup: dirs + model + MCP + hooks + CLAUDE.md
omega setup --download-model         # Download embedding model only (~90MB)
omega setup --client claude-code     # Register MCP server in ~/.claude.json
omega setup --uninstall              # Remove all OMEGA configuration
omega setup --uninstall-hooks        # Disable hooks only
omega setup --install-hooks          # Reinstall hooks
omega doctor                         # Verify: imports, model, DB, MCP registration, hooks
omega doctor --client claude-code    # Verify Claude Code registration specifically
omega status                         # Memory count, DB size, model status, edge count
```

> `omega setup` is **idempotent** — safe to re-run.

### Memory Operations

```bash
omega query <text>                   # Semantic search (70% vector + 30% BM25)
omega query <text> --exact           # Exact phrase/substring match
omega query <text> --limit N         # Limit results (default: varies)
omega query <text> --json            # JSON output

omega store <content>                # Store as generic "memory" type
omega store <content> -t decision    # Store as decision (permanent)
omega store <content> -t lesson      # Store as lesson_learned (permanent)
omega store <content> -t error       # Store as error_pattern (permanent)
omega store <content> -t preference  # Store as user_preference (permanent)
omega store <content> -t task        # Store as task_completion (180 days)

omega remember <text>                # Permanent user preference (shorthand)
omega timeline [--days N] [--json]   # Memory timeline grouped by day
```

### Maintenance

```bash
omega consolidate          # Deduplicate and prune stale memories
omega compact              # Cluster related memories; flags: -t TYPE, --threshold, --dry-run
omega backup               # Backup to ~/.omega/backups/
omega validate             # Validate DB integrity; --repair
omega stats                # Memory type distribution
omega activity             # Session activity overview
omega logs [-n LINES]      # Hook error log
```

### Knowledge

```bash
omega knowledge scan       # Auto-ingest new/changed files in ~/.omega/documents/
omega knowledge list       # List ingested documents
omega knowledge search <query> [--limit N]
```

### Commands That Do NOT Exist

> These were in goldfishh's dead code and have been removed:

- ~~`omega flush`~~ — not a command
- ~~`omega mine`~~ — not a command  
- ~~`omega note`~~ — not a command

---

## How OMEGA Self-Manages via Hooks

OMEGA registers **7 hooks** into `~/.claude/settings.json` during `omega setup`:

| Hook event | OMEGA's purpose |
|------------|----------------|
| `SessionStart` | Registration + git sync + surface prior context |
| `UserPromptSubmit` | Auto-capture: detect decisions/lessons in prompts |
| `PreToolUse` | Guard against divergence |
| `PostToolUse` | Heartbeat + surface relevant context |

**Goldfish does NOT need to replicate OMEGA's memory capture.** OMEGA's hooks handle:
- Mining JSONL transcript files
- Capturing decisions and lessons automatically
- Storing session summaries

Goldfish's role is only to **query OMEGA for context** (`omega query`) during `handle_session_start`.

---

## MCP Tools (12 total)

### Session & Context
| Tool | Key Parameters | Purpose |
|------|---------------|---------|
| `omega_welcome` | `project`, `session_id` | Session briefing with recent memories + profile |
| `omega_protocol` | `section`, `project` | Operating instructions / coordination playbook |

**Sections for `omega_protocol`:** `memory`, `coordination`, `coordination_gate`, `teamwork`, `context`, `reminders`, `diagnostics`, `entity`, `heuristics`, `git`, `what_next`

### Memory Operations
| Tool | Key Parameters | Purpose |
|------|---------------|---------|
| `omega_store` | `content`, `event_type`, `priority` (1-5), `entity_id` | Persist a memory |
| `omega_query` | `query`, `mode` (`semantic`/`phrase`/`timeline`), `limit`, `event_type`, `days` | Search memories |
| `omega_memory` | `action` (`edit`/`delete`/`feedback`/`similar`/`traverse`), `memory_id` | Manage individual memory nodes |

### Workflow
| Tool | Key Parameters | Purpose |
|------|---------------|---------|
| `omega_checkpoint` | `task_title`, `progress`, `plan`, `decisions`, `files_touched`, `next_steps` | Capture task state for continuity |
| `omega_resume_task` | `task_title`, `limit`, `verbosity` | Retrieve checkpointed task state |
| `omega_lessons` | `task`, `project_path`, `limit`, `cross_project` | Ranked lessons from past sessions |
| `omega_remind` | `action` (`set`/`list`/`dismiss`), `text`, `duration` | Time-based reminders |

### System
| Tool | Key Parameters | Purpose |
|------|---------------|---------|
| `omega_profile` | `action` (`read`/`update`/`list_preferences`) | Read/update encrypted user profile |
| `omega_maintain` | `action` (`health`/`consolidate`/`compact`/`backup`/`clear_session`) | System maintenance |
| `omega_stats` | `action` (`types`/`sessions`/`digest`/`forgetting_log`) | Memory analytics |
| `omega_reflect` | `action` (`contradictions`/`evolution`/`stale`), `topic` | (Pro) Memory health analysis |

---

## Memory Deduplication Behavior

OMEGA auto-deduplicates on ingestion:
- **Exact match:** SHA256 hash comparison — duplicate dropped
- **Near-duplicate:** cosine similarity ≥ 0.85 — merged
- **Similar content (55-95%):** appended to existing memory (Zettelkasten evolution)
- **Auto-relate:** edges created to top 3 similar memories (similarity ≥ 0.45)

---

## Python API (from `omega.bridge`)

```python
from omega.bridge import store, query, remember, auto_capture

store(content, event_type="memory", metadata=None, session_id=None)
remember(text, session_id=None)           # permanent user_preference
query(query_text)                          # returns markdown string
auto_capture(content, event_type, ...)     # primary ingestion with dedup
```

---

## Goldfish Integration Points

| Goldfish function | OMEGA interaction |
|-------------------|------------------|
| `goldfishh init` | `omega setup --download-model`, then `omega setup --client claude-code` |
| `handle_session_start` | `omega query "current project state tasks decisions"` |
| CLAUDE.md enrichment block | `omega_query()` via MCP (per-session) |
| Post-task | `omega_store()` via MCP for key decisions |
