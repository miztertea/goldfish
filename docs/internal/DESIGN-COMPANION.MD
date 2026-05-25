> **Archived.** This is the original design session narrative. Design decisions extracted to [docs/design-decisions.md](../design-decisions.md) and seeded into OMEGA episodic memory.

---

# Goldfish — Design Session Companion Document

**Purpose:** This document captures the complete design conversation that produced the Goldfish PRD. It records every major decision, every tool evaluated, every approach rejected, and the reasoning behind each. Claude Code agents building Goldfish should read this document to understand not just what to build but why every architectural choice was made.

**Date:** May 24, 2026  
**Format:** Chronological narrative of the design session

---

## Part 1 — The Problem Origin

The conversation started with a question about MemPalace, a GitHub project that gives AI agents structured memory using a "memory palace" metaphor — wings, halls, and rooms organized as markdown files, traversed via ChromaDB vector search. The initial instinct was: could we enhance this with SurrealDB as a richer graph backend?

**First pivot:** Rather than SurrealDB (a server, operational overhead), what about Obsidian? MemPalace's wing/hall/room hierarchy maps almost perfectly to Obsidian's folder structure. Wikilinks become edges. YAML frontmatter becomes node properties. Obsidian already has a graph view. And crucially — Obsidian exists. We don't have to build it.

This was the founding insight: **use existing tools that already solve the problem rather than building from scratch.**

---

## Part 2 — Tool Research: The Memory Layer

**MemPalace** was evaluated first. It uses ChromaDB (an always-on vector database) and achieves 96.6% LongMemEval recall. However, ChromaDB requires a running process. MemPalace is also a memory-only tool with no code search or prompt enrichment.

**OMEGA** was identified as the superior alternative:
- Local SQLite + ONNX embeddings (no running process)
- 95.4% LongMemEval
- 25 MCP tools out of the box
- Already exports memory to Obsidian with wikilinks
- Python API (not just CLI)

**Decision: OMEGA over MemPalace.** OMEGA does everything MemPalace does, requires no always-on process, and has native Obsidian export.

**Graphiti (Zep)** was evaluated for temporal knowledge graphs — bi-temporal modeling, incremental updates, MCP native. It was initially appealing for tracking "what we decided and when." 

**Graphiti was eliminated** for a concrete reason: it requires Neo4j or FalkorDB running as a server. The FalkorDB Lite embedded option is an open unmerged GitHub issue. KuzuDB (the only truly embedded graph database option) was archived in October 2025 and has crash reports. The decision: use Obsidian vault wikilinks with `valid_from` / `superseded_by` YAML frontmatter fields. Same expressiveness, zero operational overhead.

---

## Part 3 — Tool Research: Code Search

**Semble** was discovered during research into the MinishLab ecosystem. Key findings:
- Uses `potion-code-16M` (Model2Vec static embeddings) + BM25, fused via RRF
- 1.5ms query time, 250ms index time
- CPU only — no GPU, no API key
- Single command: `uvx semble`
- Internally uses Chonkie for code-aware file chunking

**Chonkie** was discovered as a consequence of Semble research. It's a fast text chunking library from chonkie-inc. SentenceChunker splits multi-topic paragraphs into discrete semantic queries. Critically: Chonkie is already a transitive dependency of Semble, so adding it costs nothing.

**The MinishLab coherence insight:** Semble, Model2Vec, and Chonkie form a coherent ecosystem. They share embedding spaces, which means prompt chunks and code chunks are semantically comparable. This was not designed for goldfish — it's inherited for free by composing these tools.

---

## Part 4 — The Architecture Takes Shape

**Claude Code hooks** were identified as the event bus. Claude Code fires 27 lifecycle events (SessionStart, UserPromptSubmit, PostToolUse, PreCompact, Stop, etc.) as JSON to stdin of registered commands. Anything written to stdout by a UserPromptSubmit handler is injected as Claude's context before it processes the prompt. This is the passive enrichment mechanism.

**The queue pattern** was established: hook handlers should write to a JSONL queue file and exit immediately (never blocking Claude), with a separate drain process running opportunistically on subsequent hook calls with a time budget (default 200ms). This decouples all downstream processing from Claude's execution.

**The chain of record:**
```
Claude Code JSONL logs → OMEGA → Obsidian vault ← Semble ← Chonkie
```

JSONL logs are immutable source of truth. Everything else is a derived index that can be rebuilt.

---

## Part 5 — Key Simplifications

**Simplification 1: One vault per project.**
Claude Code organizes JSONL transcripts at `~/.claude/projects/{encoded-cwd}/`. The encoding is `/Users/dev/my-project` → `-Users-dev-my-project`. Project identity is simply `cwd`. This means no mid-session project switching, no multi-project manifest complexity. One session = one project = one vault. The new-vs-existing distinction only affects startup time.

**Simplification 2: Obsidian becomes optional.**
The Obsidian Local REST API plugin was initially planned for vault search during prompt enrichment. But: the plugin requires API key setup, a running Obsidian instance, and manual plugin installation. The question was asked: can we just write files directly?

Yes. The vault is just a folder of markdown files. `pathlib.Path.write_text()` is the entire write API. Obsidian watches the directory and picks up changes automatically. It doesn't need to be running. It doesn't need any plugins.

The vault search problem (searching vault notes during prompt enrichment) was solved differently: **Semble has a `--content docs` flag** that indexes and searches markdown, rst, and prose files. `semble search "query" ~/.goldfish/vaults/my-project --content docs` searches the vault. The Obsidian REST API plugin was eliminated entirely.

**Result:** Obsidian is now a pure optional viewer. The developer opens the vault folder in Obsidian to get a visual graph, installs nothing, provides no API key. Everything works identically whether Obsidian is open, closed, or not installed at all.

**Simplification 3: goldfish_search never needs to be built.**
At one point, a custom vault search module was planned (goldfish_search) using Model2Vec + BM25. This was eliminated when the `--content docs` flag in Semble was discovered. Semble already does this. The entire custom search module was removed.

---

## Part 6 — The Five Failures Framework

A framework for tool selection was developed to prevent scope creep and redundancy. The premise: every agent context failure maps to one of exactly five problems.

```
1. Session amnesia     — agent starts blank every session
2. Codebase blindness  — agent doesn't know the shape of the code
3. Decision blindness  — agent doesn't know why things are built this way
4. Impact blindness    — agent doesn't know what breaks when it changes something
5. Prompt deafness     — agent gets generic context, not prompt-specific context
```

Every tool must solve at least one of these five failures. If it doesn't, it doesn't belong in the stack.

**The tool selection gates** were defined:
1. Necessity — solves a failure better than existing tools?
2. Local first — no cloud, no API keys
3. No always-on — no daemon, no server, no Docker
4. Install simplicity — uvx / npm / brew / single binary
5. No overlap — doesn't duplicate an already-selected tool
6. Maintainable — not a 1-star solo repo, active, MIT or Apache

---

## Part 7 — The Prompt Enrichment Problem

A key insight surfaced: simple keyword matching on prompts doesn't work for power users. A typical developer prompt looks like:

> "ok and then once that's fixed we need to refactor the auth middleware to handle the new JWT rotation policy we discussed, also the tests are broken in CI and Sarah mentioned something about the rate limiter"

This is one prompt containing multiple tasks, references to past conversations, person names, and multiple distinct code systems. A keyword scan misses most of it. Sending the full paragraph as a single Semble query returns noisy results.

**The solution: Chonkie.SentenceChunker decomposes the prompt first.**

The paragraph becomes:
- "refactor auth middleware JWT rotation policy"
- "CI tests broken"
- "Sarah rate limiter"

Each chunk is then a targeted, clean search query. All three are searched in parallel against Semble (code), Semble --content docs (vault), and OMEGA (memory). Results are deduplicated by source path and formatted into a context block injected before Claude processes the prompt.

A simulation was built and run: BM25 + TF-IDF cosine (as a Model2Vec proxy) over realistic vault notes. Key findings:
- The "Sarah rate limiter" query correctly found the ADR that mentioned "Sarah proposed sliding window counters" even with no exact keyword match
- Superseded notes (marked `superseded_by`) were correctly excluded from results
- Query times: 0.71ms average across 20 diverse queries

---

## Part 8 — Structural Analysis Gap

After the core stack was established (OMEGA + Semble + Chonkie + vault), a gap was identified: **impact blindness** was not yet solved. The agent could find code semantically, but couldn't determine what would break if it changed something.

Semble's `find-related` returns semantically similar code. That is not the same as "what calls this function." Blast radius requires structural analysis — call graphs, import graphs, transitive dependency traversal. That requires AST parsing, not embedding search.

**Tools evaluated for the structural slot:**

**Cymbal** (1broseidon/cymbal): Structurally excellent. Go binary, SQLite, JIT refresh, `cymbal investigate`, `cymbal impact`, `cymbal trace`. Exactly the right design. **Eliminated: 1 star, 1 contributor, v0.8.** Too early-stage.

**scantool**: `claude mcp add scantool -- uvx scantool`. Simple, tree-sitter based. Good fallback but less capable than cymbal for blast radius.

**tree-sitter-analyzer** (aimasteracc): uvx installable, 17 languages, well-tested. **Eliminated: 30 stars, solo contributor.** Low trust for a critical dependency.

**Arbor**: `analyze_impact` and `get_logic_path`. Correct capabilities. **Eliminated: install path unclear, not on PyPI cleanly.**

The structural slot was left explicitly open rather than filled with a weak tool. The recommendation was: v1 ships without a dedicated structural tool, using Semble + grep as an adequate (if imperfect) substitute for most solo dev workflows.

---

## Part 9 — GitNexus Discovery

GitNexus was initially evaluated and dismissed based on a misidentified fork. The correct repository is `abhigyanpatwari/GitNexus`.

**What was actually found:**

- **38.7k stars, 4.4k forks, 265 releases, v1.6.5**
- Enterprise offering at akonlabs.com
- Actively maintained, multiple contributors, Discord community

**Critical corrected understanding — it is not Docker-based:**

```bash
npx gitnexus analyze
```

That single command:
- Indexes the codebase into LadybugDB (embedded graph database, `.gitnexus/` in repo)
- Installs Claude Code PreToolUse + PostToolUse hooks automatically
- Writes CLAUDE.md and AGENTS.md context blocks
- Installs agent skills in `.claude/skills/gitnexus/`
- Generates repo-specific SKILL.md files per functional community (via Leiden clustering)

**No Docker. No server. MCP via stdio — Claude Code starts it as a subprocess on demand.**

**16 MCP tools including:**
- `query` — hybrid BM25 + semantic + RRF over the code graph
- `context` — 360° symbol view (callers, callees, processes, clusters)
- `impact` — blast radius with depth grouping and confidence scoring
- `detect_changes` — maps staged git changes to affected processes
- `rename` — multi-file coordinated rename using the graph

**LadybugDB** is the embedded graph database (the production evolution of KuzuDB after it was archived — the GitNexus team evolved their own solution). No Neo4j. No server. Files in `.gitnexus/`.

**The `--skills` feature** was identified as particularly powerful: `gitnexus analyze --skills` detects functional communities in the codebase (auth module, payment module, etc.) and generates a specific SKILL.md for each. The agent arrives at any module with targeted context about its structure, entry points, and cross-area connections.

**GitNexus mapping to the five failures:**
- Session amnesia: ❌ GitNexus doesn't do this → OMEGA still needed
- Codebase blindness: ✅ Completely solved
- Decision blindness: ✅ Partial (structural/architectural decisions visible in code, wiki generation)
- Impact blindness: ✅ Completely solved
- Prompt deafness: ✅ Partial (process-grouped query), Chonkie still needed for decomposition

**License:** PolyForm Noncommercial. Not MIT. Commercial use requires a license. For personal/non-commercial use, installing via `npm install -g gitnexus` is compliant. goldfish must not bundle, include, or redistribute GitNexus. It calls it as an external CLI dependency installed through the official npm channel.

---

## Part 10 — The Ansible Playbook Clarity

The final and most important architectural clarification came from this question: doesn't adding another search tool (goldfish_search, or a custom vault index) violate the principle of not building what already exists?

Yes. It does.

The clarification that locked the architecture:

**Goldfish is an Ansible playbook, not an application.** It selects tools, installs them via their official methods, configures them to communicate, and routes events between them. It writes no search code, no embedding code, no graph code. Those problems are solved by tools their own teams maintain.

**The concrete implication for every module:**

```python
# This is what Goldfish's code looks like:

def handle_prompt_submit(event):
    prompt = event["prompt"]
    chunks = subprocess("chonkie", prompt)              # Chonkie owns decomposition
    code   = subprocess("semble search", chunks, cwd)  # Semble owns code search
    docs   = subprocess("semble search --content docs", chunks, vault)  # Semble owns vault search
    mem    = omega.query(chunks)                        # OMEGA owns memory search
    sys.stdout.write(format(code, docs, mem))           # goldfish owns formatting

def install_gitnexus():
    run("npm install -g gitnexus")   # GitNexus installs itself
    run("npx gitnexus analyze")      # GitNexus registers its own hooks

def install_omega():
    run("pip install omega-memory")  # OMEGA installs itself
    run("omega setup")               # OMEGA writes its own MCP config
```

Every line is a subprocess call, an API call, or a file write. No algorithms invented here.

**The Code/ directory in the vault was removed.** GitNexus already maintains `.gitnexus/` as a code intelligence store inside the project. Writing a separate `Code/` directory of markdown notes would duplicate this. Remove it.

**The Obsidian bridge module became 30 lines.** Without the REST API, without retry logic, without availability concerns — just `pathlib.Path.write_text()` with YAML frontmatter rendering.

---

## Part 11 — The Final Stack

```
Five Failures    Tool              How Installed
─────────────────────────────────────────────────────────
Session amnesia  OMEGA             pip install omega-memory
                                   omega setup → MCP via stdio

Codebase         GitNexus          npm install -g gitnexus
blindness                          npx gitnexus analyze →
                                   code graph + hooks + skills

Decision         OMEGA             omega flush on Stop/PreCompact
blindness        + vault           pathlib writes to Memory/
                 (conversational)

Impact           GitNexus          gitnexus impact() MCP tool
blindness                          already included in analyze

Prompt           Chonkie           pip install chonkie
deafness         + Semble          uv tool install semble
                 + OMEGA           fan-out to all three,
                                   collect, format, stdout
```

**Optional:**
- Obsidian: open `~/.goldfish/vaults/{project}/` as a vault. No plugins. No config. Free app.

**Goldfish's own code:**
- ~400–600 lines Python
- 7 modules: cli, init, hook, drain, vault, claude_md, config
- No search. No embeddings. No graph. No models.
- Every function: subprocess call, file write, or config read.

---

## Part 12 — Decisions Summary

A complete record of every significant decision made during the design session.

| Decision | What Was Chosen | What Was Rejected | Reason |
|---|---|---|---|
| Memory engine | OMEGA | MemPalace | OMEGA has no always-on dependency (ChromaDB) |
| Graph DB | Obsidian vault + frontmatter | Graphiti/Neo4j | No server required |
| Graph DB | GitNexus LadybugDB | SurrealDB, KuzuDB | Embedded, no server, battle-tested |
| Code search | Semble | Custom embedding search | Already built, 1.5ms, MinishLab team |
| Prompt decomp | Chonkie SentenceChunker | Custom NLP, spaCy, SmolLM2 | Already inside Semble, <1ms, no model needed |
| Vault search | Semble --content docs | Obsidian REST API, goldfish_search | Already in Semble, zero marginal cost |
| Obsidian role | Optional viewer | Required service | REST API plugin eliminated; pure file writes work |
| Project isolation | Per-project vault | Single shared vault | No cross-project context bleeding |
| Project identity | cwd = identity | Config file | Mirrors Claude Code's own JSONL organization |
| Structural analysis | GitNexus | cymbal, Arbor, scantool, tree-sitter-analyzer | 38.7k stars, correct arch, covers two failures |
| Architecture | Ansible playbook | Custom search/graph code | Don't build what already exists |
| License approach | Install via npm | Bundle/redistribute | PolyForm Noncommercial compliance |
| MCP registration | GitNexus + OMEGA + Semble | Obsidian MCP plugin | Obsidian plugin eliminated (no search needed) |
| Queue format | JSONL append-only | SQLite, Redis | Zero dependencies, atomic, human-readable |

---

## Part 13 — Things That Were Considered and Eliminated

**Tools evaluated and rejected (with reasons):**

- **MemPalace** — ChromaDB always-on, OMEGA is superior and overlaps
- **SurrealDB** — always-on server, violates no-always-on principle
- **Graphiti/Zep** — requires Neo4j or FalkorDB server
- **KuzuDB** — archived October 2025, crash reports
- **FalkorDB Lite in Graphiti** — unmerged GitHub issue as of design session
- **Obsidian Local REST API plugin** — eliminated when Semble --content docs was discovered
- **goldfish_search (custom)** — eliminated when Semble --content docs was discovered
- **spaCy for NER** — Chonkie SentenceChunker covers the use case without a separate pipeline
- **SmolLM2-135M for query extraction** — 10-50 tokens/sec on CPU = 500ms-3s, too slow for synchronous hook
- **Model2Vec directly** — already inside Semble and Chonkie; no need to call directly
- **Cymbal** — 1 star, 1 contributor, too early-stage for a critical dependency
- **Sverklo** — overlaps OMEGA (memory) + Semble (semantic search) + GitNexus (structural); good tool, wrong fit
- **tree-sitter-analyzer** — 30 stars, solo contributor; GitNexus fills this slot
- **Arbor** — install path unclear, not on PyPI; GitNexus fills this slot
- **scantool** — less capable than GitNexus for blast radius; kept as fallback option
- **GitNexus via Docker** — Docker is optional; CLI via npm is the right mode for goldfish

**Architectural patterns rejected:**

- **Wrapper around Claude Code** (`goldfish claude [args]`) — unnecessary, hooks are global
- **Always-on daemon** — no user should need to remember to start a service
- **HTTP server for inter-process communication** — JSONL queue file is simpler, more resilient
- **Code/ directory in vault** — GitNexus already maintains this in `.gitnexus/`
- **Bidirectional vault sync** — Obsidian edits flowing back to OMEGA; vault is a derived index

---

## Part 14 — What goldfish Actually Contributes

The five tools (GitNexus, OMEGA, Semble, Chonkie, Obsidian) each solve one or two of the five failures independently. What none of them do:

1. Run a wizard that installs all of them via their official methods
2. Write the CLAUDE.md that explains all of them together, in one coherent active-layer instruction
3. Process the 27 Claude Code lifecycle events that should trigger each of them
4. Maintain the queue that decouples those events from blocking Claude
5. Write the vault notes that connect OMEGA episodic memory to human-readable markdown
6. Enrich prompts by fanning out to all three search layers simultaneously (GitNexus query + Semble + OMEGA)
7. Maintain the per-project manifest that tracks sync state across sessions
8. Generate the wake-up context note that brief Claude at the start of each session
9. Handle the new-vs-existing project distinction at SessionStart

That is what goldfish does. It is modest work. It is the right work.

---

## Part 15 — Simulations Run During Design

**Vault search simulation** was built and run during the session to validate the search approach. A realistic vault with 8 notes (decisions, errors, lessons, specs, tasks) was created. BM25 + TF-IDF cosine similarity (as a Model2Vec proxy) was used.

**Key simulation findings:**
- Query time: 0.71ms average, 1.07ms max across 20 queries
- "Sarah rate limiter" correctly found ADR-015 which mentioned "Sarah proposed sliding window counters" — a conversational reference with no exact keyword match
- Superseded notes (`superseded_by` set) were correctly excluded from all results
- "Redis session storage" query correctly did NOT surface the superseded ADR-008 (old Redis session decision)
- Abstract reasoning query ("why did we choose this approach over alternatives") still found decision notes via semantic similarity

**Conclusion:** The search approach is validated. Real Model2Vec embeddings (replacing TF-IDF) will be meaningfully better on abstract queries. Everything else works correctly on the weaker proxy.

---

## Key Quotes From the Design Session

These capture the moments where the architecture became clear:

> "We aren't trying to make money. Right now it's for personal use and maybe some friends. So I don't want to 'bundle' anything, our init should install the dependency from the official method. Consider us like an ansible playbook."

> "Our code should be as streamlined as possible, we just ingest track and process the events orchestrating the tools but not creating them. Meaning we shouldn't write our own search, we should use semble."

> "So in option A, obsidian becomes optional? The whole thing still works without it? It just gives the human UI? If that's true, then our setup is utter perfection. Truly all local and no external dependencies, just an optional obsidian visualization layer if you want it?!"

> "And our framework, the five things an agent needs. This is satisfied by omega and semble with a little python orchestrator?"

> "We will use these two documents to seed Claude Code to build the memory and then use these two documents memory to build the tool :)"

---

## Instructions for Claude Code Agents Building goldfish

If you are a Claude Code agent reading this document to build goldfish, here is what you need to know:

**The most important principle:** Do not write any search, embedding, or graph code. If you find yourself writing a search algorithm, stop. Find the right CLI tool and call it as a subprocess instead.

**The five failures** are your specification. Every feature you build should map to at least one of them. If a feature doesn't solve a failure, don't build it.

**The module structure** in the PRD is your architecture. Each module has one job. `hook.py` writes to the queue and exits. `drain.py` routes events to tools. `vault.py` writes files. `init.py` installs tools.

**GitNexus does more than you expect.** `npx gitnexus analyze` handles the code intelligence layer almost entirely on its own. Let it. Your job is to add OMEGA, the vault, and the prompt enrichment layer on top.

**Obsidian requires no integration work.** Write markdown files. Done. If Obsidian is open, it shows them. If not, `cat` and `grep` work fine.

**The queue is your safety valve.** Every hook handler should return in under 10ms. Write to the queue. Return. The drain handles everything else.

**Test at boundaries.** Test that a hook event results in a queue entry. Test that a queue entry results in the right subprocess call. Test that a subprocess call results in the right vault file. Do not test internals.

**Read the PRD alongside this document.** The PRD is the specification. This document is the reasoning. Together they contain everything needed to build Goldfish correctly.

---

## Part 16 — The Name

The project was named **Goldfish** at the end of the design session.

The name is a deliberate joke about the problem being solved. Goldfish are famous — incorrectly, as it turns out, but the myth is culturally embedded — for having a memory measured in seconds. An AI agent using Claude Code without Goldfish is, from session to session, essentially a goldfish: it forgets everything the moment the session ends.

The irony is the point. The tool that gives agents persistent memory is named after the creature with the shortest memory. It communicates the problem in one word, makes the purpose instantly memorable, and is genuinely funny in a field that takes itself too seriously.

**CLI ergonomics:** `goldfish` is short, easy to type, lowercase-friendly, and works naturally as a command:

```bash
uvx goldfish init
uvx goldfish doctor
uvx goldfish status
uvx goldfish replay
```

**The name communicates the pitch in one line:**

> *"Goldfish gives your AI agent a memory."*

Anyone who hears that immediately understands both the problem (agents are goldfish) and the solution (Goldfish fixes that). No explanation required.

The original working name was **vaultmind**, which was descriptive but generic. Goldfish is neither descriptive nor generic. It's a personality. That's better.
