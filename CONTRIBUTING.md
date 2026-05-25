# Contributing to goldfish

## Prerequisites

- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Dev setup

```bash
git clone https://github.com/miztertea/goldfish
cd goldfish
uv sync
uv run pytest
```

Tests stub all subprocess calls and the OMEGA API. You do not need GitNexus, OMEGA, or Semble installed to run tests. ~100 tests, ~0.3s.

## Running tests

```bash
uv run pytest -v                           # verbose output
uv run pytest tests/test_hook.py -v       # single module
uv run goldfish --help                    # run CLI from source
```

## Project structure

See [CLAUDE.md](CLAUDE.md) for the module map and operational constraints.  
See [docs/architecture.md](docs/architecture.md) for the full system design and runtime flows.

## Code style

- No comments unless the WHY is non-obvious (a hidden constraint, a subtle invariant, a workaround for a specific bug)
- No docstrings
- Test at module boundaries — input/output assertions, not internal calls
- Stub subprocess calls and the OMEGA API in tests

## PR process

1. Branch from `main`
2. Tests must pass: `uv run pytest`
3. PR description covers the why, not just the what
4. If the change touches architecture or adds a dependency, link to the relevant design doc

## AI agent contributors

If you are an AI agent contributing to goldfish, read [AGENTS.md](AGENTS.md) first. It contains the agent constitution, superpowers workflow, five failures guardrail, and goldfish-specific constraints.
