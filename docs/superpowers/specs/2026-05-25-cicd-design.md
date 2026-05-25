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

Semantic-release runs after all gates pass on `main`. It:
1. Determines the next version from conventional commits since the last tag
2. Commits an updated `CHANGELOG.md` to `main`
3. Creates a git tag and GitHub Release

Because it pushes the CHANGELOG.md commit directly to `main`, it requires a branch protection bypass. A Personal Access Token (PAT) with `repo` scope is stored as `GH_TOKEN` in repo secrets and configured as a bypass actor in the branch protection ruleset.

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

### Branch protection and rulesets

Configure via GitHub API after Phase 1 CI is green. The following `gh api` calls set the required rules:

```bash
# Set branch protection on main
gh api repos/miztertea/goldfish/branches/main/protection \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  -f 'required_status_checks={"strict":true,"contexts":["quality","test"]}' \
  -f 'enforce_admins=false' \
  -f 'required_pull_request_reviews=null' \
  -f 'restrictions=null' \
  -f 'allow_force_pushes=false' \
  -f 'allow_deletions=false'
```

The semantic-release PAT (stored as `GH_TOKEN`) must be added as a bypass actor in the GitHub repo settings UI (Settings → Branches → Edit rule → Bypass list). This cannot be set via the API on the free plan.

Rules enforced:
- Required status checks (`quality`, `test`) must pass before merging
- Force pushes blocked
- Branch deletions blocked
- No required approving reviews (solo project — CI is the gate)
- Semantic-release PAT bypasses the rule to push the CHANGELOG.md commit

### CHANGELOG.md

Semantic-release writes and commits `CHANGELOG.md` to `main` on every release. Entries are grouped by version and auto-generated from conventional commit messages. The file accumulates over time and becomes the canonical public changelog — no manual maintenance required.

Each entry looks like:

```
## [0.2.0] - 2026-06-01

### Features
- add Claude Code detection to goldfish init (#12)

### Bug Fixes
- fix hook routing for PreCompact events (#11)
```

`CHANGELOG.md` is committed to the repo root and published on the GitHub Release page.

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

### Phase 3 — In-repo docs + roadmap
- `CONTRIBUTING.md` (branch naming, worktree workflow, commit conventions)
- `ROADMAP.md` (high-level public intent — see Roadmap section below)
- GitHub Issues labels configured (bug, enhancement, idea, breaking, good first issue)
- GitHub Milestones created for next two planned releases

### Phase 4 — Local CI with `act`
`act` (github.com/nektos/act) runs GitHub Actions workflows locally using Docker, pulling the same runner images GitHub uses. No custom devcontainer required.

```bash
brew install act      # or apt-get / scoop on Windows

act push              # simulate a full push event locally
act -j quality        # run just the quality job
act -j test           # run just the test job
act -j matrix         # run the matrix job (Linux container, macOS/Windows mapped to Linux)
```

Phase 4 deliverable: add `act` to CONTRIBUTING.md with the local workflow commands above.

**Limitation:** `act` maps all runner types to Linux containers — macOS/Windows-specific path behavior still requires real GitHub CI runners. For goldfish's init flow, pytest, and CLI smoke tests, Linux is sufficient for local validation.

---

## Roadmap and Feature Tracking

### Tools

| Purpose | Tool |
|---------|------|
| Bugs and feature requests | GitHub Issues |
| Release planning | GitHub Milestones (one per upcoming version) |
| Public intent and direction | `ROADMAP.md` in repo root |
| Community discussion (once public) | GitHub Discussions |
| Session decisions and agent context | OMEGA + goldfish vault |

### Issue labels

Configure at repo setup:
- `bug` — something is broken
- `enhancement` — new capability
- `idea` — not yet committed, open for discussion
- `breaking` — will require major version bump
- `chore` — maintenance, deps, CI
- `good first issue` — small, well-scoped, good for new contributors

### ROADMAP.md

A file in the repo root, updated manually by the human at each milestone. Covers:
- Current focus (what's being built now)
- Near-term goals (next 1-2 releases)
- Long-term direction (no dates — intent only)
- Explicitly out of scope

This is the public-facing "where is this going" document. Agents should read it before proposing new features. OMEGA and vault handle tactical session tracking; ROADMAP.md handles strategic intent.

---

## Open Prerequisites (manual steps before implementation)

1. **PyPI package name:** verify `goldfish` is available on PyPI before Phase 2. If taken, choose an alternative (e.g., `goldfish-agent`) and update `pyproject.toml`.
2. **PyPI Trusted Publisher:** configure in PyPI account settings after Phase 1 CI is green.
3. **Branch protection bypass:** create a PAT with `repo` scope, store as `GH_TOKEN` secret, add as bypass actor in GitHub branch protection settings UI. Run the `gh api` protection command from the spec after Phase 1 CI is green.
4. **`ANTHROPIC_API_KEY` secret:** add to GitHub repo secrets for Claude PR review.
5. **Verify `anthropics/claude-code-action` version tag** at implementation time — use the latest published release tag, not `@main`.
