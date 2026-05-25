# CI/CD Pipeline Design — goldfish

**Date:** 2026-05-25
**Status:** Approved for implementation

---

## Overview

Full GitHub Actions CI/CD pipeline for the goldfish project. Covers quality gates, cross-platform testing, automated versioning via git-cliff + hatch-vcs, PyPI publishing via Trusted Publisher (OIDC), Claude PR review, and the in-repo branch/worktree practices agents must follow.

Designed for the GitHub free tier while private; once the repo goes public, macOS runner restrictions lift automatically.

---

## Versioning Strategy

### Reset to `0.1.0`

Current version `0.9.6` carries no semantic meaning. Reset to `0.1.0` at pipeline launch to signal pre-stable development. The `0.x.y` range means "no API stability guarantees" — no pressure to hit 1.0 until the API is genuinely stable.

### hatch-vcs: version from git tags

Version is derived from the nearest git tag at build time. No version number lives in any source file — the tag IS the version, and hatch-vcs reads it during `uv build`.

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
```

### git-cliff: CHANGELOG and tag automation

`git-cliff` is the natural pairing for hatch-vcs. It reads conventional commits, computes the next semver tag, and generates `CHANGELOG.md` — without needing to write a version to any source file. The tag becomes the single source of truth that hatch-vcs reads at build time.

> **Why not python-semantic-release?** PSR is designed for projects with a static `version = "..."` field it can read and overwrite. hatch-vcs removes that field with `dynamic = ["version"]`. The two are architecturally incompatible — PSR has no supported mode for tag-only versioning with hatch-vcs. git-cliff was designed for exactly this pattern.

Commit prefixes and version bumps (configured in `cliff.toml`):

| Commit prefix | Version bump |
|---------------|-------------|
| `feat:` | minor (0.1.0 → 0.2.0) |
| `fix:` | patch (0.1.0 → 0.1.1) |
| `chore:`, `docs:`, `refactor:`, `test:` | no release |
| `BREAKING CHANGE:` in footer | major (0.1.0 → 1.0.0) |

The release job in CI runs:

```bash
# Compute next version from conventional commits
NEW_TAG=$(git cliff --bumped-version)

# Generate CHANGELOG.md
git cliff --bump -o CHANGELOG.md

# Commit changelog and tag
git add CHANGELOG.md
git commit -m "chore: update changelog for ${NEW_TAG}"
git tag "${NEW_TAG}"
git push --follow-tags

# Create GitHub Release (triggers publish.yml)
gh release create "${NEW_TAG}" --generate-notes
```

Because it commits `CHANGELOG.md` directly to `main`, the release job requires a branch protection bypass. A PAT with `repo` scope is stored as `GH_TOKEN` in repo secrets and configured as a bypass actor in the branch protection ruleset.

`git-cliff` is added to the release job via `orhun/git-cliff-action@v4` (no local install needed).

---

## Repository Practices

### Branch naming

All work lives on a branch. Direct pushes to `main` are prohibited (with one exception: the semantic-release release commit, which uses a configured token bypass).

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

### Branch protection (GitHub Rulesets API)

Configure via GitHub Rulesets API after Phase 1 CI is green. Rulesets are the forward-looking approach (protection rules API is not deprecated but receives no new features).

```bash
gh api repos/miztertea/goldfish/rulesets \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  --input - <<'EOF'
{
  "name": "main branch protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {"required_approving_review_count": 0, "dismiss_stale_reviews_on_push": false, "require_code_owner_review": false, "require_last_push_approval": false, "required_review_thread_resolution": false}},
    {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": true, "required_status_checks": [{"context": "quality"}, {"context": "test"}]}}
  ],
  "bypass_actors": []
}
EOF
```

The semantic-release PAT (stored as `GH_TOKEN`) must be added as a bypass actor manually in GitHub repo settings UI after the ruleset is created (Settings → Rules → Edit → Bypass list). Rulesets support bypass actors but the actor must exist before it can be referenced by ID in the API.

Rules enforced:
- Required status checks (`quality`, `test`) must pass before merging
- Force pushes blocked (non_fast_forward rule)
- Branch deletions blocked
- No required approving reviews (solo project — CI is the gate)
- Semantic-release PAT bypasses the rule for its release commit

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

`CHANGELOG.md` is committed to the repo root and also included on the GitHub Release page.

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
  mypy src/goldfish/ (lenient — see below)
  bandit -r src/ -ll                        ← medium+ severity only (skips B603/B607)
  uv run pip-audit                          ← run inside uv venv

claude-review (ubuntu-latest)               ← runs on pull_request events only (parallel)
  anthropics/claude-code-action@v1
  → posts inline review comments
  → responds to @claude mentions
  continue-on-error: true                   ← never gates merge

test (ubuntu-latest, needs: quality)
  uv run pytest

matrix (needs: test)
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  strategy.matrix.os: [macos-latest, windows-latest]
  steps (all use shell: bash for cross-platform glob/path compatibility):
    uv sync --group dev
    uv run pytest                           ← full suite
    actions/setup-node@v4                   ← npm required for goldfish init
    uv build
    uv tool install dist/goldfish-*.whl     ← shell: bash ensures glob works on Windows
    goldfish --help
    goldfish init                           ← requires ANTHROPIC_API_KEY secret injected
    goldfish status
    goldfish doctor

release (ubuntu-latest, needs: matrix)
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  orhun/git-cliff-action@v4                 ← compute next tag, generate CHANGELOG.md
  git commit CHANGELOG.md + git tag         ← commit + tag (uses GH_TOKEN bypass)
  git push --follow-tags
  gh release create                         ← creates GitHub Release
  → GitHub Release event triggers publish.yml
```

**Key job-level notes:**
- `matrix` has an explicit `if:` guard — macOS/Windows runners only fire on push to `main`, never on PRs
- `claude-review` has `continue-on-error: true` — it cannot accidentally become a required gate
- All matrix steps use `shell: bash` so glob patterns and path separators work identically on Windows
- Matrix job injects `ANTHROPIC_API_KEY` from repo secrets so `goldfish init` can configure OMEGA
- `uv run pip-audit` runs inside the uv-managed venv so goldfish's actual dependencies are audited
- `bandit -r src/ -ll` skips low-severity findings (B603/B607 subprocess patterns are expected in this codebase)

### `publish.yml` — PyPI Trusted Publisher

Triggers on `release: published` event (created by semantic-release).

```
build (ubuntu-latest)
  uv build → wheel + sdist
  upload as workflow artifact

publish (ubuntu-latest, environment: pypi)
  permissions: id-token: write    ← OIDC, no API token needed
  pypa/gh-action-pypi-publish@release/v1
  → uploads to PyPI
```

Trusted Publisher setup (one-time — two parts, both required):

**Part A — PyPI account settings:**
- Publisher: GitHub Actions
- Repository: miztertea/goldfish
- Workflow: publish.yml
- Environment: pypi

**Part B — GitHub repo settings (Settings → Environments):**
- Create environment named exactly `pypi`
- (Optional) add required reviewers or deployment protection rules

Both parts must exist. The OIDC token GitHub issues includes an `environment` claim that PyPI validates against Part A. If the GitHub environment (Part B) doesn't exist, the workflow job cannot start.

No `PYPI_TOKEN` secret needed — OIDC handles authentication.

### Tool versions

Pin at implementation time to latest stable:

| Action | Current stable | Notes |
|--------|---------------|-------|
| `astral-sh/setup-uv` | `v5` (or latest) | Verify latest tag before implementing |
| `pypa/gh-action-pypi-publish` | `release/v1` | Rolling major tag, safe to use |
| `anthropics/claude-code-action` | `v1` | Confirmed on GitHub Marketplace |
| `actions/checkout` | `v4` | |
| `actions/setup-node` | `v4` | Needed in matrix job for npm/Claude Code |

### mypy configuration (lenient start)

```toml
[tool.mypy]
ignore_missing_imports = true
check_untyped_defs = false
```

Target `src/goldfish/` not `src/` — this avoids scanning non-package files at the src root. Tighten incrementally as type annotations are added.

### bandit configuration

```toml
[tool.bandit]
skips = ["B603", "B607"]   # subprocess.run with list args — expected, not a security issue
```

Or use the CLI flag: `bandit -r src/ -ll` (medium+ severity only). The subprocess patterns in goldfish are intentional — all commands are hardcoded, not user-supplied.

### New dev dependencies

Add to `pyproject.toml` dev group:

```
ruff
mypy
bandit[toml]
pip-audit
```

Add to build dependencies:

```
hatch-vcs
```

`git-cliff` is installed in CI via `orhun/git-cliff-action@v4` — no local install needed. A `cliff.toml` config file goes in the repo root to define conventional commit parsing and CHANGELOG template.

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
1. Detect Claude Code missing → install via npm (npm pre-installed via `actions/setup-node@v4`)
2. Install GitNexus → analyze repo
3. Install OMEGA → configure (requires `ANTHROPIC_API_KEY` injected from repo secrets)
4. Install Semble → index
5. Register hooks in Claude Code settings

This is the real integration test — it validates the full new-user onboarding flow on each platform.

---

## Phasing

### Phase 0 — Prerequisite (implement first, separate PR)
- Add Claude Code detection to `goldfish init`
- Switch to hatch-vcs (`dynamic = ["version"]`, `[tool.hatch.version] source = "vcs"`)
- Create initial tag `v0.1.0` to establish baseline for git-cliff
- Add `cliff.toml` to repo root (conventional commit config + CHANGELOG template)

### Phase 1 — CI pipeline
- `.github/workflows/ci.yml`
- Add dev dependencies (ruff, mypy, bandit, pip-audit, python-semantic-release)
- mypy + ruff + bandit configs in `pyproject.toml`
- `.github/pull_request_template.md`
- Branch ruleset (via `gh api` command from spec, then bypass actor via UI)

### Phase 2 — Release pipeline
- `.github/workflows/publish.yml`
- `orhun/git-cliff-action@v4` + release script in `ci.yml`
- Create `pypi` GitHub environment (Settings → Environments)
- PyPI Trusted Publisher setup (in PyPI account — one-time, Part A)
- `ANTHROPIC_API_KEY` secret added to repo (for goldfish init in matrix job + Claude PR review)

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
2. **PyPI Trusted Publisher (Part A):** configure in PyPI account settings after Phase 1 CI is green (Publisher: GitHub Actions, repo: miztertea/goldfish, workflow: publish.yml, env: pypi).
3. **GitHub environment `pypi` (Part B):** create in GitHub repo Settings → Environments. Required for OIDC token issuance — without this the publish job cannot start.
4. **Branch protection bypass:** create a PAT with `repo` scope, store as `GH_TOKEN` secret, add as bypass actor in the ruleset via GitHub UI after running the `gh api` command.
5. **`ANTHROPIC_API_KEY` secret:** add to GitHub repo secrets — used by both the Claude PR review job and `goldfish init` in the matrix smoke test (OMEGA setup requires it).
6. **Verify `anthropics/claude-code-action` version tag** at implementation time — use the latest published release tag, not `@main`.
