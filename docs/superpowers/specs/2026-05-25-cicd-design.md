# CI/CD Pipeline Design — goldfish

**Date:** 2026-05-25
**Status:** Approved for implementation

---

## Overview

Full GitHub Actions CI/CD pipeline for the goldfish project. Covers quality gates, cross-platform testing, automated versioning via semantic-release, PyPI publishing via Trusted Publisher (OIDC), Claude PR review, and the in-repo branch/worktree practices agents must follow.

Designed for the GitHub free tier while private; once the repo goes public, macOS runner restrictions lift automatically.

---

## Versioning Strategy

### Reset to `0.1.0`

Current version `0.9.6` carries no semantic meaning. Reset to `0.1.0` at pipeline launch to signal pre-stable development. The `0.x.y` range means "no API stability guarantees" — no pressure to hit 1.0 until the API is genuinely stable.

### hatch-vcs: version from git tags

Replace the hardcoded version in `pyproject.toml` with tag-derived versioning:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
```

The version is derived from the nearest git tag at build time. No version number lives in any source file — the tag IS the version. This eliminates stale version references in docs and code.

### python-semantic-release: automated bumping

Semantic-release reads conventional commit prefixes to determine the next version:

| Commit prefix | Version bump |
|---------------|-------------|
| `feat:` | minor (0.1.0 → 0.2.0) |
| `fix:` | patch (0.1.0 → 0.1.1) |
| `chore:`, `docs:`, `refactor:`, `test:` | no release |
| `BREAKING CHANGE:` in footer | major (0.1.0 → 1.0.0) |

Semantic-release creates a tag and GitHub Release automatically after all gates pass on `main`. It never pushes a version-bump commit (because hatch-vcs reads the tag, not a file), so no branch protection bypass is required.

---

## Repository Practices

### Branch naming

All work lives on a branch. Direct pushes to `main` are prohibited (with one exception: the semantic-release tag push, which uses a configured token bypass).

Branch names match conventional commit prefixes:

```
feat/<name>       new capability → minor bump on merge
fix/<name>        bug fix → patch bump on merge
chore/<name>      maintenance, CI, deps → no release
docs/<name>       documentation → no release
refactor/<name>   code restructuring → no release
```

### Worktree workflow (agents)

Every agent coding session uses a git worktree. Worktrees live outside the repo directory to avoid gitignore complications and to give each agent its own `.gitnexus/` index.

```bash
# Start of session
git checkout -b feat/<name>
git worktree add ../goldfish-<name> feat/<name>
cd ../goldfish-<name>

# ... all work happens here ...

# End of session — after PR merge
cd /home/tchawes/goldfish
git worktree remove ../goldfish-<name>
```

See `superpowers:using-git-worktrees` skill for full details.

### Conventional commits (required)

Semantic-release reads commit messages to determine version bumps. All commits must follow the format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer: BREAKING CHANGE: <description>]
```

This is already in use — git history confirms compliance.

### Branch protection on `main` (configure in GitHub repo settings)

- Require pull request before merging
- Required passing status checks: `quality`, `test`
- No direct pushes (semantic-release token gets a bypass rule)

### PR template

File: `.github/pull_request_template.md`

Checklist prompts contributors to identify the commit type (which determines the version bump) and confirm local test passage.

---

## CI Pipeline

### Workflow files

```
.github/workflows/
├── ci.yml       # All gates + semantic-release
└── publish.yml  # PyPI publish (fires on GitHub Release event)
```

### `ci.yml` — job chain

```
quality (ubuntu-latest)                     ← runs on every push + PR
  ruff check .
  ruff format --check .
  mypy src/ (lenient config — see below)
  bandit -r src/
  pip-audit
        ↓
test (ubuntu-latest, needs: quality)
  uv run pytest
        ↓ conditional: push to main only
matrix (macos-latest + windows-latest, parallel, needs: test)
  uv run pytest                             ← full suite on each OS
  uv build
  uv tool install dist/goldfish-*.whl
  goldfish --help
  goldfish init                             ← installs Claude Code, GitNexus, OMEGA, Semble
  goldfish status
  goldfish doctor
        ↓ conditional: push to main only, after matrix
release (ubuntu-latest, needs: matrix)
  python-semantic-release
  → determines next version from commits since last tag
  → creates git tag + GitHub Release
  → GitHub Release event triggers publish.yml
```

**Claude PR review** runs in parallel with `quality` (not a gate — advisory only):

```
claude-review (ubuntu-latest)               ← runs on pull_request events only
  anthropics/claude-code-action
  → posts inline review comments on the PR diff
  → responds to @claude mentions in PR comments
```

Requires `ANTHROPIC_API_KEY` secret in repo settings. Burns Anthropic API credits (~cents per review). Non-blocking — does not gate merge.

### `publish.yml` — PyPI Trusted Publisher

Triggers on `release: published` event (created by semantic-release).

```
build (ubuntu-latest)
  uv build → wheel + sdist
  upload as workflow artifact

publish (ubuntu-latest, environment: pypi)
  permissions: id-token: write    ← OIDC, no API token needed
  pypa/gh-action-pypi-publish
  → uploads to PyPI
```

Trusted Publisher setup (one-time, in PyPI account settings):
- Publisher: GitHub Actions
- Repository: miztertea/goldfish
- Workflow: publish.yml
- Environment: pypi

No `PYPI_TOKEN` secret needed — OIDC handles authentication.

### Setup action

All jobs use `astral-sh/setup-uv@v5` (official Astral action, handles caching automatically).

### mypy configuration (lenient start)

```toml
[tool.mypy]
ignore_missing_imports = true
check_untyped_defs = false
```

Tighten incrementally as type annotations are added.

### New dev dependencies

Add to `pyproject.toml` dev group:

```
ruff
mypy
bandit[toml]
pip-audit
python-semantic-release
```

Add to build dependencies:

```
hatch-vcs
```

---

## Feature Prerequisite: Claude Code Detection in `goldfish init`

### What

Add Claude Code detection and auto-install to `init.py`, making goldfish fully self-bootstrapping for new users and enabling end-to-end CI smoke tests.

### Detection logic

```python
if not check_dependency("claude"):
    print("  Installing Claude Code...")
    result = subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"])
    if result.returncode != 0:
        print("  note: Claude Code install failed; install manually from claude.ai/code")
    else:
        print("✓ Claude Code installed")
else:
    print("✓ Claude Code found")
```

Insert before the GitNexus check (Claude Code is the prerequisite for everything).

### Why this enables CI smoke tests

On a fresh macOS or Windows runner, `goldfish init` will:
1. Detect Claude Code missing → install via npm
2. Install GitNexus → analyze repo
3. Install OMEGA → configure
4. Install Semble → index
5. Register hooks in Claude Code settings

This is the real integration test — it validates the full new-user onboarding flow on each platform.

---

## Phasing

### Phase 0 — Prerequisite (implement first, separate PR)
- Add Claude Code detection to `goldfish init`
- Reset version to `0.1.0` tag, switch to hatch-vcs

### Phase 1 — CI pipeline
- `.github/workflows/ci.yml`
- Add dev dependencies (ruff, mypy, bandit, pip-audit, python-semantic-release)
- mypy + ruff configs in pyproject.toml
- `.github/pull_request_template.md`
- Branch protection rules (configured in GitHub settings, not code)

### Phase 2 — Release pipeline
- Configure python-semantic-release in pyproject.toml
- `.github/workflows/publish.yml`
- PyPI Trusted Publisher setup (in PyPI account — one-time)
- `ANTHROPIC_API_KEY` secret added to repo (for Claude PR review)

### Phase 3 — In-repo docs
- `CONTRIBUTING.md` (branch naming, worktree workflow, commit conventions)

---

## Open Prerequisites (manual steps before implementation)

1. **PyPI package name:** verify `goldfish` is available on PyPI before Phase 2. If taken, choose an alternative (e.g., `goldfish-agent`) and update `pyproject.toml`.
2. **PyPI Trusted Publisher:** configure in PyPI account settings after Phase 1 CI is green.
3. **Branch protection bypass:** configure semantic-release token bypass in GitHub repo branch protection settings.
4. **`ANTHROPIC_API_KEY` secret:** add to GitHub repo secrets for Claude PR review.
5. **Verify `anthropics/claude-code-action` version tag** at implementation time — use the latest published release tag, not `@main`.
