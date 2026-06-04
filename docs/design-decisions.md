# Design Decisions

The durable record of significant decisions made during goldfishh's design phase.
Full narrative context is archived in [docs/internal/DESIGN-COMPANION.MD](internal/DESIGN-COMPANION.MD).
Each decision is also stored in OMEGA episodic memory and queryable via `omega query`.

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Memory engine | OMEGA | MemPalace | OMEGA has no always-on dependency (ChromaDB); SQLite + ONNX |
| Temporal knowledge graph | Obsidian vault + frontmatter `valid_from`/`superseded_by` | Graphiti/Neo4j | No server required; same expressiveness for our use case |
| Embedded graph DB | GitNexus LadybugDB | SurrealDB, KuzuDB (archived) | Embedded, no server, production-grade, ships with GitNexus |
| Code search | Semble | Custom embedding search | Already built, 1.5ms query, MinishLab team maintains it |
| Prompt decomposition | Chonkie SentenceChunker | Custom NLP, spaCy, SmolLM2 | Already inside Semble as transitive dep; <1ms; no model needed |
| Vault search | Semble `--include-text-files` | Obsidian REST API plugin, custom goldfishh_search module | Already in Semble; zero marginal cost; plugin eliminated |
| Obsidian role | Optional viewer only | Required service with REST API | Plugin eliminated; pure `pathlib.write_text()` is sufficient |
| Project isolation | Per-project vault | Single shared vault | No cross-project context bleeding |
| Project identity | `cwd` = identity | Config file | Mirrors Claude Code's own JSONL organization scheme |
| Structural analysis | GitNexus | Cymbal, Arbor, scantool, tree-sitter-analyzer | 38.7k stars, correct architecture, covers two failures |
| Architecture style | Ansible playbook (thin orchestrator) | Custom search/graph/memory code | Don't build what already exists; inherit improvements automatically |
| GitNexus license compliance | Install via `npm install -g gitnexus` | Bundle or redistribute | PolyForm Noncommercial: install from official npm only |
| MCP registration | GitNexus + OMEGA + Semble | Obsidian MCP plugin | Vault search covered by Semble; Obsidian plugin eliminated |
| Event queue format | JSONL append-only | SQLite, Redis | Zero dependencies; atomic appends; human-readable; no locking needed |
