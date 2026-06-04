# Tool Selection

## Selection gates

Every candidate tool must clear all six gates. Fail any gate → eliminated regardless of capability.

```
Gate 1 — NECESSITY       Solves one of the five failures, better than existing?
Gate 2 — LOCAL FIRST     No cloud, no API keys, no data leaving the machine
Gate 3 — NO ALWAYS-ON    No daemon, no server, no Docker
Gate 4 — INSTALL SIMPLE  uvx / npm / brew / single binary. One command.
Gate 5 — NO OVERLAP      Doesn't duplicate a tool already selected
Gate 6 — MAINTAINABLE    Not a one-person 3-star repo. Active. MIT or Apache.
```

## Selected tools

### GitNexus

```
Failures solved: Codebase blindness + Impact blindness
Local:          LadybugDB embedded graph, .gitnexus/ in repo, no cloud
No always-on:   MCP via stdio, started on demand by Claude Code
Install:        npm install -g gitnexus → npx gitnexus analyze
Overlap:        None — structural graph analysis not covered elsewhere
Maintained:     38.7k stars, 265 releases, enterprise backing
License:        PolyForm Noncommercial (personal/non-commercial: install via npm only, never bundle)
```

One command (`npx gitnexus analyze`) indexes the codebase, installs Claude Code hooks, writes CLAUDE.md/AGENTS.md blocks, installs skills, and generates per-community SKILL.md files.

### OMEGA

```
Failures solved: Session amnesia + Decision blindness (conversational layer)
Local:          SQLite, ONNX, no cloud
No always-on:   Opens and closes
Install:        uv tool install "omega-memory[server]" → omega setup --client claude-code
Overlap:        None — episodic memory exclusively
Maintained:     Apache 2.0, active, 95.4% LongMemEval
```

### Semble

```
Failures solved: Prompt deafness (retrieval layer)
Local:          Model2Vec (potion-code-16M) + BM25, CPU only, no API
No always-on:   CLI, exits
Install:        uv tool install semble → claude mcp add semble
Overlap:        GitNexus does structural search; Semble does semantic search. Complementary.
                Also covers vault search via --include-text-files over markdown files.
Maintained:     MIT, MinishLab
```

### Chonkie

```
Failures solved: Prompt deafness (decomposition layer)
Local:          Pure Python, no model download for SentenceChunker
No always-on:   Library call
Install:        Already a transitive Semble dependency — zero marginal cost
Overlap:        None — decomposition before fan-out
Maintained:     MIT, chonkie-inc
```

## Eliminated tools

| Tool | Reason eliminated |
|------|-----------------|
| MemPalace | ChromaDB always-on; OMEGA is superior and overlaps |
| SurrealDB | Always-on server — violates no-always-on gate |
| Graphiti/Zep | Requires Neo4j or FalkorDB server |
| KuzuDB | Archived October 2025, crash reports |
| FalkorDB Lite (in Graphiti) | Unmerged GitHub issue at time of evaluation |
| Obsidian REST API plugin | Eliminated when `semble --include-text-files` was discovered — no vault search plugin needed |
| goldfish_search (custom) | Eliminated when `semble --include-text-files` was discovered |
| spaCy | Chonkie SentenceChunker covers prompt decomposition without a separate NER pipeline |
| SmolLM2-135M | 500ms–3s on CPU — too slow for synchronous UserPromptSubmit hook |
| Model2Vec directly | Already inside Semble and Chonkie — no direct use needed |
| Cymbal | 1 star, 1 contributor, v0.8 — violates maintainability gate |
| Sverklo | Overlaps OMEGA + Semble + GitNexus; good tool, wrong fit for goldfishh |
| tree-sitter-analyzer | 30 stars, solo contributor — GitNexus fills this slot |
| Arbor | Install path unclear, not on PyPI cleanly — GitNexus fills this slot |
| scantool | Less capable than GitNexus for blast radius |
| GitNexus via Docker | Docker is optional; CLI via npm is the right mode for goldfishh |

## The MinishLab coherence note

Semble, Model2Vec, and Chonkie are from closely related teams. They share an embedding space — prompt chunks decomposed by Chonkie and code chunks indexed by Semble are semantically comparable. This coherence is inherited for free by composing these tools.
