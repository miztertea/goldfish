# The Five Failures Framework

Every AI agent context failure maps to one of exactly five problems. This framework drives every tool selection and implementation decision in goldfish. A feature that doesn't address at least one failure doesn't belong in the project.

## The five failures

| Context Failure | Symptom | Tool |
|----------------|---------|------|
| 1. Session amnesia | "We discussed this last week" / "You already fixed that bug" | OMEGA |
| 2. Codebase blindness | 15 tool calls to find one function; missing a module entirely | GitNexus |
| 3. Decision blindness | "I'll use Redis for sessions" (we decided against that) | OMEGA + vault |
| 4. Impact blindness | Changes verify_jwt(), breaks 4 callers silently | GitNexus |
| 5. Prompt deafness | "Fix the auth bug" → agent searches from zero | Chonkie + Semble + OMEGA |

## How each failure is addressed

**Session amnesia → OMEGA**  
OMEGA is a local SQLite + ONNX episodic memory store. It mines Claude Code JSONL transcripts and surfaces past decisions, known issues, and prior context via natural language queries. It achieves 95.4% recall on LongMemEval. No cloud, no daemon, no API key.

**Codebase blindness → GitNexus**  
GitNexus indexes the codebase into LadybugDB (an embedded graph database) via `npx gitnexus analyze`. It provides hybrid BM25+semantic search, 360° symbol context (callers, callees, execution flows), and functional community detection. Query by concept, not by filename.

**Decision blindness → OMEGA + vault**  
OMEGA captures session decisions automatically. goldfish writes structured vault notes (plain markdown with temporal frontmatter) for architectural decisions, lessons, and errors. Vault notes are searchable by Semble and human-readable without tooling.

**Impact blindness → GitNexus**  
GitNexus `impact()` maps every upstream caller of a symbol with depth grouping and confidence scores. `detect_changes()` maps staged git changes to affected execution flows before a commit. An agent cannot change code without knowing the blast radius.

**Prompt deafness → Chonkie + Semble + OMEGA**  
Chonkie's `SentenceChunker` decomposes multi-topic prompts into discrete queries. Each chunk fans out to Semble (code search), Semble with `--include-text-files` (vault search), and OMEGA (memory search) in parallel. Results arrive before Claude processes the prompt.

## Using the framework as a contributor

Before building any feature, map it to a failure:

1. Which of the five failures does this address?
2. Is there already a tool in the stack that addresses it?
3. If yes: wire to that tool, don't rebuild it.
4. If no: evaluate new tools against the [six selection gates](tool-selection.md#selection-gates).

If a feature doesn't map to any failure — don't build it.
