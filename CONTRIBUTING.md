# Contributing to goldfish

## Prerequisites

- Python 3.13+
- Node.js 18+ (required for GitNexus and Claude Code)
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Branch naming

Every unit of work lives on a branch — never commit directly to `main`.

```
feat/<name>       → minor version bump on merge
fix/<name>        → patch bump on merge
chore/<name>      → maintenance, no release
docs/<name>       → documentation, no release
refactor/<name>   → restructuring, no release
```

## Worktree workflow (for coding agents)

Every agent coding session uses a git worktree so each session has its own
`.gitnexus/` index and doesn't interfere with the main working tree.

```bash
# Start of session
git checkout -b feat/<name>
git worktree add ../goldfish-<name> feat/<name>
cd ../goldfish-<name>

# ... all work happens here ...

# After PR merges — clean up
cd /path/to/goldfish
git worktree remove ../goldfish-<name>
```

See the `superpowers:using-git-worktrees` skill for full details.

## Conventional commits (required)

Commit messages determine the next version bump via git-cliff:

```
feat: add Claude Code detection to goldfish init
fix: correct hook routing for PreCompact events
chore: update dependencies
docs: add CONTRIBUTING.md
refactor: extract dependency check into helper
```

For breaking changes, add `BREAKING CHANGE:` to the commit footer:

```
feat!: change init API to require explicit project name

BREAKING CHANGE: run() now requires the project argument.
```

## Local development

```bash
uv sync --group dev      # install all dependencies including dev tools
uv run pytest            # run test suite (~110 tests, ~0.3s)
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy src/goldfish/ # type check
uv run bandit -r src/ -ll # security scan
uv run pip-audit         # dependency vulnerability scan
```

## Local CI with act

[act](https://github.com/nektos/act) runs GitHub Actions workflows locally using
Docker, pulling the same runner images GitHub uses.

```bash
# Install
brew install act   # macOS/Linux
# or: scoop install act  (Windows)

# Run specific jobs
act -j quality     # run the quality job
act -j test        # run the test job
act push           # simulate a full push event
```

**Note:** `act` maps macOS and Windows runners to Linux containers. This is
sufficient for goldfish — the platform-specific risk (shell path formatting
in settings.json) is validated by the real GitHub macOS/Windows runners on
push to main.
