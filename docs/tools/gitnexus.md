# GitNexus — Code Intelligence Engine

> Indexes any codebase into a knowledge graph (symbols, call chains, execution flows). Exposes it via MCP for AI agents. Local-first, no cloud, no server needed.

**Source:** https://github.com/abhigyanpatwari/GitNexus  
**License:** PolyForm Noncommercial — non-commercial use only. Never bundle or redistribute. Install via npm only.  
**Install:** `npm install -g gitnexus`  
**Web UI:** https://gitnexus.vercel.app (browser-only, no install)

---

## Quick Start

```bash
# Index your repo (run from repo root) — does everything:
npx gitnexus analyze

# Configure MCP for editors (one-time):
npx gitnexus setup
```

`gitnexus analyze` indexes the codebase, installs agent skills, registers Claude Code hooks, and creates `AGENTS.md`/`CLAUDE.md` context files.

---

## CLI Commands

### Core

```bash
gitnexus setup                            # Auto-detect editors and write global MCP config (one-time)
gitnexus analyze [path]                   # Index repo (run from repo root), update stale index
gitnexus analyze --repair-fts             # Fast path: rebuild only FTS indexes
gitnexus analyze --force                  # Full rebuild: re-parse + graph + FTS
gitnexus analyze --skills                 # Generate repo-specific skill files
gitnexus analyze --skip-embeddings        # Skip embedding generation (faster)
gitnexus analyze --skip-agents-md         # Preserve custom AGENTS.md/CLAUDE.md edits
gitnexus analyze --skip-git               # Index non-git folders
gitnexus analyze --embeddings             # Enable embeddings (slower, better semantic search)
gitnexus analyze --verbose                # Log skipped files
gitnexus analyze --workers <n>            # Parse worker pool size (default: cores-1, max 16)
gitnexus analyze --worker-timeout 60     # Increase timeout for slow parses (seconds)
gitnexus mcp                              # Start MCP server (stdio) — serves all indexed repos
gitnexus serve                            # Start local HTTP server for web UI connection
gitnexus list                             # List all indexed repositories
gitnexus status                           # Show index status for current repo
gitnexus clean                            # Delete index for current repo
gitnexus clean --all --force              # Delete all indexes
gitnexus wiki [path]                      # Generate wiki from knowledge graph
gitnexus publish                          # Notify understand-quickly registry (opt-in)
```

### Repository Groups (multi-repo)

```bash
gitnexus group create <name>
gitnexus group add <group> <groupPath> <registryName>
gitnexus group remove <group> <groupPath>
gitnexus group list [name]
gitnexus group sync <name>
gitnexus group query <name> <q>
gitnexus group status <name>
```

### Speed Tip

Install globally and use `gitnexus` directly (avoids npx download on cold cache):
```bash
npm install -g gitnexus
gitnexus setup
```

Cold `npx gitnexus` can exceed Claude Code's MCP_TIMEOUT (~30s).

### Skip slow grammar build (no C++ toolchain needed)

```bash
GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1 npm install -g gitnexus
```

Skips Dart/Proto/Swift grammar compilation. Parsing for those languages won't work but everything else does.

---

## MCP Integration

`gitnexus setup` auto-detects editors and writes the correct config. Claude Code gets the deepest integration: **MCP tools + agent skills + PreToolUse/PostToolUse hooks**.

**MCP server command:**
```bash
gitnexus mcp   # stdio mode, serves all indexed repos
```

**Claude Code registration:**
```bash
claude mcp add gitnexus -- npx -y gitnexus@latest mcp
# or (preferred, faster startup):
claude mcp add gitnexus -- gitnexus mcp
```

---

## MCP Tools (16 total)

### Per-Repo Tools (11)

| Tool | Description | When to use |
|------|-------------|-------------|
| `query` | Hybrid search: BM25 + semantic + RRF across execution flows | Finding code by concept |
| `context` | 360° symbol view: callers, callees, process participation | Understanding one function/class |
| `impact` | Blast radius: upstream/downstream changes with risk score | Before modifying anything |
| `detect_changes` | Map git diff → affected symbols and processes | Before committing |
| `rename` | Graph-assisted multi-file rename with `dry_run` preview | Renaming symbols safely |
| `cypher` | Raw Cypher queries against the graph schema | Custom graph traversals |
| `api_impact` | Pre-change impact report for an API route handler | Before changing routes |
| `route_map` | API route → handler → consumer mappings | Understanding HTTP routing |
| `tool_map` | MCP/RPC tool definitions and handlers | Analyzing MCP integrations |
| `shape_check` | Response shape vs consumer property access mismatches | Type safety audits |
| `list_repos` | Discover all indexed repositories | First call in any session |

### Group Tools (5)

| Tool | Description |
|------|-------------|
| `group_list` | List configured repo groups |
| `group_sync` | Rebuild Contract Registry and bridge graph |
| `group_contracts` | Inspect contracts and cross-links |
| `group_query` | Search execution flows across all repos in a group |
| `group_status` | Check staleness across group members |

### Resource Reads (instant context, no query needed)

| Resource URI | Purpose |
|--------------|---------|
| `gitnexus://repos` | List all indexed repos (read first) |
| `gitnexus://repo/{name}/context` | Stats, staleness, available tools |
| `gitnexus://repo/{name}/clusters` | Functional clusters with cohesion scores |
| `gitnexus://repo/{name}/processes` | All execution flows |
| `gitnexus://repo/{name}/process/{name}` | Full process trace with steps |
| `gitnexus://repo/{name}/schema` | Graph schema for Cypher queries |

### MCP Prompts (2)

| Prompt | Purpose |
|--------|---------|
| `detect_impact` | Pre-commit change analysis: scope, affected processes, risk level |
| `generate_map` | Architecture documentation with Mermaid diagrams |

---

## Architecture: Index → Graph → MCP Flow

1. **Ingestion** — `gitnexus analyze` runs 12-phase pipeline:
   `scan → structure → [markdown, cobol] → parse → [routes, tools, orm] → crossFile → mro → communities → processes`

2. **Storage** — LadybugDB (custom embedded graph DB in `.gitnexus/` directory). Registry: `~/.gitnexus/registry.json`.

3. **Query** — MCP server reads from `.gitnexus/` via three interfaces: MCP stdio, HTTP bridge (for web UI), CLI direct.

4. **Staleness detection** — compares indexed `lastCommit` to current `HEAD`. Warns agent when index is stale.

### What the Graph Tracks

- Every function, class, method, module (symbols)
- IMPORTS, CALLS, EXTENDS edges
- API routes, MCP tool handlers, ORM queries
- Execution flows (processes) — end-to-end call chains
- Community clusters (Leiden algorithm)
- Method resolution order (MRO)

---

## Claude Code Integration Details

GitNexus installs **4 Claude Code agent skills** in `.claude/skills/gitnexus/`:

| Skill file | Purpose |
|------------|---------|
| `gitnexus-exploring/SKILL.md` | Architecture exploration, "how does X work?" |
| `gitnexus-impact-analysis/SKILL.md` | Blast radius analysis |
| `gitnexus-debugging/SKILL.md` | Bug tracing |
| `gitnexus-refactoring/SKILL.md` | Safe refactoring workflow |

**Hooks registered during `gitnexus analyze`:**
- `PreToolUse` — enriches searches with graph context
- `PostToolUse` — detects stale index after commits, prompts reindex

These coexist with goldfish's hooks (different purposes, no conflict).

---

## Goldfish Integration Points

| Goldfish function | GitNexus interaction |
|-------------------|---------------------|
| `goldfish init` | `npm install -g gitnexus`, then `npx gitnexus analyze` (if `.gitnexus/` absent) |
| `goldfish init` | `npx gitnexus setup` (MCP registration, once) |
| CLAUDE.md | Goldfish appends the knowledge tool block; GitNexus manages its own `<!-- gitnexus:start/end -->` block |
| Per-task workflow | Agent calls `context()` + `impact()` before any edit |
| Pre-commit | Agent calls `detect_changes()` to verify scope |

---

## Supported Languages

Tree-sitter parsing: Python, TypeScript, JavaScript, Java, Rust, Go, C, C++, C#, Ruby, PHP, Swift (requires C++ toolchain), Dart (requires toolchain), Protocol Buffers (requires toolchain), Kotlin, Scala, HTML, CSS, Markdown, YAML, JSON, TOML, COBOL (regex fallback)

---

## Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GITNEXUS_SKIP_OPTIONAL_GRAMMARS` | unset | `=1` to skip Dart/Proto/Swift grammar build |
| `GITNEXUS_WORKER_POOL_SIZE` | cores-1, max 16 | Parse worker count |
| `GITNEXUS_MAX_FILE_SIZE` | 512 KB | Skip files larger than this |
| `GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS` | 30000 | Worker timeout per job |
| `GITNEXUS_VERBOSE` | unset | `=1` for verbose ingestion logs |
| `GITNEXUS_NO_GITIGNORE` | unset | Skip .gitignore parsing |
