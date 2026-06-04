# Semble — Code Search CLI & MCP

> Verified against installed binary. The official docs site (minish.ai) shows a `--content` flag that does NOT exist in the installed CLI. Trust this file over the website.

**Source:** https://minish.ai/packages/semble/  
**Install:** `uv tool install semble`  
**MCP extra:** `uv tool install "semble[mcp]"` (or use `uvx --from "semble[mcp]" semble`)

---

## CLI Commands

### `semble search`

```
semble search <query> [path] [options]
```

| Argument/Flag | Description |
|---------------|-------------|
| `query` | Natural language or code query (required) |
| `path` | Local directory path or https:// git URL (default: current directory) |
| `-k, --top-k N` | Number of results (default: 5) |
| `-m, --mode {hybrid,semantic,bm25}` | Search mode (default: hybrid) |
| `--include-text-files` | Also index `.md`, `.yaml`, `.json`, and other non-code text files |

**Examples:**
```bash
# Search code in project
semble search "authentication flow" ./src

# Search vault notes (requires --include-text-files for markdown)
semble search "session start" ~/.goldfishh/vaults/goldfishh --include-text-files

# Search remote repo
semble search "save_pretrained" https://github.com/huggingface/transformers

# Limit results
semble search "JWT rotation" ./src --top-k 10
```

> **IMPORTANT:** Vault/markdown search REQUIRES `--include-text-files`. Without it, semble only indexes code files and will return no results for `.md` notes.

### `semble find-related`

```
semble find-related <file_path> <line> [path] [options]
```

| Argument/Flag | Description |
|---------------|-------------|
| `file_path` | File path as shown in search results |
| `line` | Line number (1-indexed) |
| `path` | Local path or git URL (default: current directory) |
| `-k, --top-k N` | Number of results (default: 5) |
| `--include-text-files` | Also index non-code text files |

```bash
semble find-related src/goldfishh/drain.py 61 .
```

### `semble init`

```
semble init [--force]
```

Writes `.claude/agents/semble-search.md` in the current directory — a Claude Code sub-agent specification that allows Claude to dispatch search tasks to a dedicated Semble agent.

```bash
semble init              # creates .claude/agents/semble-search.md (skips if exists)
semble init --force      # overwrites existing file
```

**Goldfish uses this during `goldfishh init`** to wire up the sub-agent automatically.

### `semble savings`

```
semble savings [--verbose]
```

Shows token savings and usage statistics from cached index use.

---

## MCP Server

Register with Claude Code:
```bash
claude mcp add semble -s user -- uvx --from "semble[mcp]" semble
```

**MCP Tools exposed:**

| Tool | Description |
|------|-------------|
| `search` | Search a codebase with natural-language or code query. `repo` = local directory path or https:// git URL |
| `find_related` | Given a `file_path` and `line` number, return semantically similar code chunks |

**Key behaviors:**
- Repositories are indexed on first search and cached per session
- Local paths are auto-reindexed when files change
- `--include-text-files` is passed as a server flag to include markdown/docs in the index

---

## Goldfish Integration Points

| Goldfish function | Semble call |
|-------------------|-------------|
| `goldfishh init` | `semble init` (creates sub-agent file in cwd) |
| `enricher.enrich()` — code search | `semble search <chunk> <cwd>` |
| `enricher.enrich()` — vault search | `semble search <chunk> <vault_path> --include-text-files` |

---

## Known Docs/Reality Gaps

| What docs say | What CLI actually has | Verified |
|---------------|-----------------------|---------|
| `--content {code,docs,config,all}` flag | Does NOT exist | `semble search --help` |
| `--include-text-files` | EXISTS and is the correct flag | `semble search --help` |
| `semble init` command | EXISTS (not on docs homepage) | `semble --help` |
