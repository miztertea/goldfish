# CI/CD Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full GitHub Actions CI/CD pipeline for goldfish with quality gates, cross-platform validation, automated versioning via git-cliff + hatch-vcs, and PyPI publishing via Trusted Publisher.

**Architecture:** Sequential gate pipeline — ubuntu quality/test runs on every push and PR; macOS + Windows matrix runs on push to main only; git-cliff generates CHANGELOG and creates a release tag after matrix passes; a separate publish workflow fires on the GitHub Release event and uploads to PyPI via OIDC.

**Tech Stack:** GitHub Actions, uv, hatch-vcs, git-cliff (orhun/git-cliff-action@v4), ruff, mypy, bandit, pip-audit, pypa/gh-action-pypi-publish, anthropics/claude-code-action@v1

**Design spec:** `docs/superpowers/specs/2026-05-25-cicd-design.md`

---

## Phase 0 — Foundation

### Task 1: Switch to hatch-vcs

Version will be derived from the nearest git tag at build time. The static `version = "0.9.6"` field is replaced with `dynamic = ["version"]` and a hatch-vcs source.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml build-system and project sections**

Replace the existing `[build-system]` and `[project]` version handling:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "goldfish"
dynamic = ["version"]
requires-python = "==3.13.*"
dependencies = ["tomli-w", "PyYAML", "typer", "chonkie"]
```

Add after `[project.urls]`:

```toml
[tool.hatch.version]
source = "vcs"
```

Remove the line `version = "0.9.6"` — it must not exist alongside `dynamic = ["version"]`.

- [ ] **Step 2: Verify the build works without a version field**

```bash
uv build
```

Expected: build fails or warns about missing tag — that's fine, we create the tag in Task 2. If it outputs `0.0.0.dev0+...` that's correct hatch-vcs behavior with no tag.

- [ ] **Step 3: Run the full test suite to confirm no regressions**

```bash
uv run pytest
```

Expected: 108 passed

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: switch to hatch-vcs for tag-derived versioning"
```

---

### Task 2: Add cliff.toml, initial CHANGELOG.md, and v0.1.0 tag

git-cliff reads `cliff.toml` to know how to parse commits and format the changelog. The `v0.1.0` tag marks the starting point — all commits after it will be included in future release notes.

**Files:**
- Create: `cliff.toml`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Create cliff.toml in the repo root**

```toml
[changelog]
header = """
# Changelog

All notable changes to goldfish are documented here.
Generated automatically by [git-cliff](https://git-cliff.org).

"""
body = """
{% if version %}\
## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else %}\
## [unreleased]
{% endif %}\
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group | striptags | trim | upper_first }}
{% for commit in commits %}
- {% if commit.scope %}**{{ commit.scope }}:** {% endif %}{{ commit.message | upper_first }}\
{% endfor %}
{% endfor %}
"""
trim = true
footer = ""

[git]
conventional_commits = true
filter_unconventional = true
split_commits = false
commit_parsers = [
    { message = "^feat", group = "Features" },
    { message = "^fix", group = "Bug Fixes" },
    { message = "^docs", group = "Documentation" },
    { message = "^refactor", group = "Refactoring" },
    { message = "^perf", group = "Performance" },
    { message = "^test", group = "Testing" },
    { message = "^chore|^ci|^build", skip = true },
]
filter_commits = false
tag_pattern = "v[0-9]*"
skip_tags = ""
ignore_tags = ""
topo_order = false
sort_commits = "oldest"
```

- [ ] **Step 2: Create a stub CHANGELOG.md**

```markdown
# Changelog

All notable changes to goldfish are documented here.
Generated automatically by [git-cliff](https://git-cliff.org).
```

- [ ] **Step 3: Create the v0.1.0 tag and verify git-cliff reads it**

```bash
git add cliff.toml CHANGELOG.md
git commit -m "chore: add cliff.toml and CHANGELOG.md stub"
git tag v0.1.0
git push origin main --follow-tags
```

- [ ] **Step 4: Verify git-cliff can compute the next version**

Install git-cliff locally to verify (`cargo install git-cliff` or via brew/apt), or skip to CI validation:

```bash
git cliff --bumped-version
```

Expected: outputs `v0.1.0` (no commits since the tag yet) or `v0.1.1`/`v0.2.0` depending on commits since tag. Either is correct — the key is no error.

---

### Task 3: Add Claude Code detection to `goldfish init`

`goldfish init` should detect and auto-install Claude Code before checking Node.js, making it fully self-bootstrapping.

**Files:**
- Modify: `src/goldfish/init.py`
- Modify: `tests/test_init.py`

- [ ] **Step 1: Add two new tests first (TDD)**

Add to `tests/test_init.py` after the existing `test_check_dependency_returns_false_when_not_found` test:

```python
def test_init_installs_claude_code_when_missing(tmp_path):
    """When claude CLI is absent, npm install -g @anthropic-ai/claude-code must run."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")

    def dep_missing_claude(cmd):
        return cmd != "claude"  # claude absent, all others present

    with patch("goldfish.init.check_dependency", side_effect=dep_missing_claude), \
         patch("goldfish.init.shutil.which", return_value="/usr/bin/omega"), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [c[0][0] for c in mock_run.call_args_list]
    claude_install = any(
        isinstance(c, list) and "npm" in c and "@anthropic-ai/claude-code" in c
        for c in cmds
    )
    assert claude_install, "npm install -g @anthropic-ai/claude-code must run when claude is missing"


def test_init_skips_claude_code_install_when_present(tmp_path):
    """When claude CLI is already present, npm install for Claude Code must NOT run."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value="/usr/bin/omega"), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [c[0][0] for c in mock_run.call_args_list]
    claude_install = any(
        isinstance(c, list) and "npm" in c and "@anthropic-ai/claude-code" in c
        for c in cmds
    )
    assert not claude_install, "npm install @anthropic-ai/claude-code must NOT run when claude is present"
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
uv run pytest tests/test_init.py::test_init_installs_claude_code_when_missing tests/test_init.py::test_init_skips_claude_code_install_when_present -v
```

Expected: both FAIL (function not yet implemented)

- [ ] **Step 3: Update the existing broken test**

`test_run_exits_early_if_node_missing` currently asserts `mock_run.assert_not_called()`. After we add the Claude Code check (which calls subprocess.run), this assertion breaks. Update the test to use the correct assertion:

Replace the entire `test_run_exits_early_if_node_missing` function with:

```python
def test_run_exits_early_if_node_missing(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    stable = tmp_path / "goldfish"
    stable.touch()

    def dep_missing_node(cmd):
        return cmd != "node"  # node absent, claude and others present

    with patch("goldfish.init.check_dependency", side_effect=dep_missing_node), \
         patch("goldfish.init._goldfish_stable_path", return_value=stable), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         pytest.raises(SystemExit):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path)

    cmds = [c[0][0] for c in mock_run.call_args_list]
    gitnexus_ran = any(isinstance(c, list) and "gitnexus" in c for c in cmds)
    assert not gitnexus_ran, "gitnexus must not run when node is missing"
```

- [ ] **Step 4: Add Claude Code detection to init.py**

In `src/goldfish/init.py`, add the following block immediately before the `if not check_dependency("node"):` check (currently at line 101). Insert after the `project = project_name(cwd)` line:

```python
    # Claude Code — install via npm if missing (non-fatal, log only)
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

- [ ] **Step 5: Run all init tests**

```bash
uv run pytest tests/test_init.py -v
```

Expected: all pass (no regressions + 2 new tests pass)

- [ ] **Step 6: Run full suite**

```bash
uv run pytest
```

Expected: 110 passed (108 + 2 new)

- [ ] **Step 7: Commit**

```bash
git add src/goldfish/init.py tests/test_init.py
git commit -m "feat: auto-install Claude Code in goldfish init when missing"
```

---

## Phase 1 — CI Pipeline

### Task 4: Add quality dev dependencies and fix existing violations

Before writing the CI workflow, ensure the quality tools pass locally. Fix any violations now so CI is green from day one.

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dev dependencies to pyproject.toml**

Update the `[dependency-groups]` section:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "ruff>=0.9.0",
    "mypy>=1.0.0",
    "bandit[toml]>=1.7.0",
    "pip-audit>=2.7.0",
]
```

Add tool configuration sections to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.mypy]
ignore_missing_imports = true
check_untyped_defs = false

[tool.bandit]
skips = ["B603", "B607"]
```

- [ ] **Step 2: Install the new deps**

```bash
uv sync --group dev
```

Expected: resolves and installs ruff, mypy, bandit, pip-audit

- [ ] **Step 3: Run ruff and fix any violations**

```bash
uv run ruff check . --fix
uv run ruff format .
```

Expected: ruff auto-fixes import ordering and minor style issues. Review any remaining violations that need manual fixes. Re-run until clean:

```bash
uv run ruff check .
```

Expected: no output (no violations)

- [ ] **Step 4: Run mypy**

```bash
uv run mypy src/goldfish/
```

Expected: exits 0 with `Success: no issues found` or warnings only (no errors, because `check_untyped_defs = false` skips untyped function bodies). If errors appear, they are likely missing type stubs — fix by adding `# type: ignore` only for third-party imports that have no stubs, or adjust `ignore_missing_imports = true` covers them.

- [ ] **Step 5: Run bandit**

```bash
uv run bandit -r src/ -ll
```

Expected: exits 0. The `[tool.bandit] skips = ["B603", "B607"]` config suppresses the subprocess-related findings that are expected in goldfish. If other findings appear, either fix the code or add them to `skips` in `pyproject.toml` with a comment explaining why.

- [ ] **Step 6: Run pip-audit**

```bash
uv run pip-audit
```

Expected: exits 0 (no known vulnerabilities). If vulnerabilities are found in dependencies, upgrade the affected package in `pyproject.toml` and re-run.

- [ ] **Step 7: Run full test suite to confirm no regressions from config changes**

```bash
uv run pytest
```

Expected: 110 passed

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml
git add -u  # any auto-fixed source files from ruff
git commit -m "chore: add ruff, mypy, bandit, pip-audit dev dependencies + fix violations"
```

---

### Task 5: Create `.github/workflows/ci.yml` — quality and test jobs

The quality and test jobs run on every push and PR. These are the required status checks for branch protection.

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create ci.yml with quality, claude-review, and test jobs**

```yaml
name: CI

on:
  push:
    branches: ['**']
  pull_request:
    branches: [main]

jobs:
  quality:
    name: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-caching: true
      - run: uv sync --group dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src/goldfish/
      - run: uv run bandit -r src/ -ll
      - run: uv run pip-audit

  claude-review:
    name: claude-review
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    continue-on-error: true
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}

  test:
    name: test
    runs-on: ubuntu-latest
    needs: quality
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-caching: true
      - run: uv sync --group dev
      - run: uv run pytest
```

> **Note on `anthropics/claude-code-action@v1`:** Verify the exact version tag in the [GitHub Marketplace](https://github.com/marketplace/actions/claude-code-action) at implementation time and pin to a specific SHA for security. The `continue-on-error: true` ensures it never gates a merge.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add quality + test + claude-review jobs to ci.yml"
```

- [ ] **Step 4: Push and verify the workflow appears in GitHub Actions**

```bash
git push origin main
```

Open the repo → Actions tab. Confirm the CI workflow triggered and quality + test jobs pass.

---

### Task 6: Add matrix and release jobs to ci.yml

Matrix (macOS + Windows) and release (git-cliff + tag + GitHub Release) run only on push to main, after the ubuntu test gate passes.

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Append the matrix job to ci.yml**

Add after the `test` job:

```yaml
  matrix:
    name: matrix (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    strategy:
      matrix:
        os: [macos-latest, windows-latest]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v5
        with:
          enable-caching: true
      - uses: actions/setup-node@v4
        with:
          node-version: 'lts/*'
      - name: Install dev dependencies
        shell: bash
        run: uv sync --group dev
      - name: Run test suite
        shell: bash
        run: uv run pytest
      - name: Build wheel
        shell: bash
        run: uv build
      - name: Install built wheel
        shell: bash
        run: uv tool install dist/goldfish-*.whl
      - name: Smoke test CLI
        shell: bash
        run: goldfish --help
      - name: Smoke test init
        shell: bash
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          goldfish init
          goldfish status
          goldfish doctor
```

> **Key details:**
> - All steps use `shell: bash` — this ensures glob patterns (`dist/goldfish-*.whl`) work on Windows (GitHub Actions ships git-bash on Windows runners).
> - `actions/setup-node@v4` is required — `goldfish init` installs Claude Code via npm.
> - `fetch-depth: 0` is needed for hatch-vcs to find the nearest git tag and produce the correct wheel version (without it, hatch-vcs produces `0.0.0.dev0`).
> - `ANTHROPIC_API_KEY` is injected so `goldfish init` can configure OMEGA.

- [ ] **Step 2: Append the release job to ci.yml**

Add after the `matrix` job:

```yaml
  release:
    name: release
    runs-on: ubuntu-latest
    needs: matrix
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GH_TOKEN }}
      - name: Check for releasable commits
        id: check
        shell: bash
        run: |
          LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
          # Skip release if HEAD was committed by the release bot (prevents loops)
          LAST_AUTHOR=$(git log -1 --format='%ae')
          if [ "${LAST_AUTHOR}" = "github-actions[bot]@users.noreply.github.com" ]; then
            echo "skip=true" >> $GITHUB_OUTPUT
            echo "Release commit detected — skipping release job"
          else
            echo "skip=false" >> $GITHUB_OUTPUT
          fi
      - uses: orhun/git-cliff-action@v4
        if: steps.check.outputs.skip == 'false'
        id: cliff
        with:
          config: cliff.toml
          args: --bumped-version
        env:
          GITHUB_REPO: ${{ github.repository }}
      - uses: orhun/git-cliff-action@v4
        if: steps.check.outputs.skip == 'false'
        with:
          config: cliff.toml
          args: --bump -o CHANGELOG.md
        env:
          GITHUB_REPO: ${{ github.repository }}
      - name: Commit, tag, and push
        if: steps.check.outputs.skip == 'false'
        shell: bash
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          NEW_TAG: ${{ steps.cliff.outputs.version }}
        run: |
          LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
          if [ "${NEW_TAG}" = "${LAST_TAG}" ]; then
            echo "No releasable commits since ${LAST_TAG} — skipping tag creation"
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add CHANGELOG.md
          git diff --staged --quiet || git commit -m "chore: update changelog for ${NEW_TAG}"
          git tag "${NEW_TAG}"
          git push --follow-tags
          gh release create "${NEW_TAG}" \
            --title "${NEW_TAG}" \
            --notes-file CHANGELOG.md
```

> **Release loop prevention:** The bot-authored changelog commit would re-trigger CI. The `check` step detects this by inspecting the last commit's author email and sets `skip=true`, which gates all subsequent steps.

- [ ] **Step 3: Run tests locally to confirm no regressions**

```bash
uv run pytest
```

Expected: 110 passed

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add matrix + release jobs to ci.yml"
```

---

### Task 7: Create PR template

**Files:**
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Create the template**

```markdown
## Summary
<!-- What changed and why (1-3 sentences) -->

## Type of change
- [ ] `feat:` — new capability (minor version bump on merge)
- [ ] `fix:` — bug fix (patch bump on merge)
- [ ] `chore:` / `docs:` / `refactor:` / `test:` — maintenance (no release)
- [ ] `feat!:` or `BREAKING CHANGE:` footer — breaking change (major bump)

## Test plan
- [ ] `uv run pytest` passes locally
- [ ] If OS-specific code changed: verified behavior described in summary

## Commit messages
Commits in this PR follow conventional commit format (`type: description`).
```

- [ ] **Step 2: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "chore: add PR template with commit type checklist"
```

---

## Phase 2 — Release Pipeline

### Task 8: Create `.github/workflows/publish.yml`

Fires on GitHub Release published event (created by the release job in ci.yml). Publishes to PyPI via OIDC — no API token needed.

**Files:**
- Create: `.github/workflows/publish.yml`

**Prerequisites before this task can produce a live publish:**
1. Create GitHub environment named `pypi` in repo Settings → Environments
2. Configure PyPI Trusted Publisher in your PyPI account: Publisher = GitHub Actions, Repository = miztertea/goldfish, Workflow = publish.yml, Environment = pypi
3. Verify `goldfish` (or chosen name) is available on PyPI

- [ ] **Step 1: Create publish.yml**

```yaml
name: Publish

on:
  release:
    types: [published]

jobs:
  build:
    name: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v5
      - name: Build wheel and sdist
        run: uv build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    name: publish
    runs-on: ubuntu-latest
    needs: build
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

> `fetch-depth: 0` in the build job is required so hatch-vcs can find the release tag and embed the correct version in the wheel metadata.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: add PyPI publish workflow via OIDC Trusted Publisher"
```

---

### Task 9: Configure branch ruleset

Enforces that `quality` and `test` status checks must pass before any PR can merge to `main`. Run this after Task 5's CI workflow is green on the remote.

**Files:** none (GitHub API call, no files changed)

**Prerequisites:** CI workflow must have run at least once so GitHub knows the check names `quality` and `test`.

- [ ] **Step 1: Create the branch ruleset via GitHub API**

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
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {"context": "quality"},
          {"context": "test"}
        ]
      }
    }
  ],
  "bypass_actors": []
}
EOF
```

Expected: `201 Created` response with the ruleset JSON.

- [ ] **Step 2: Add semantic-release PAT as bypass actor (manual UI step)**

Go to: GitHub repo → Settings → Rules → `main branch protection` → Edit → Bypass list → Add bypass → choose the PAT owner or bot account that holds `GH_TOKEN`.

This allows the release job's changelog commit to push directly to main without triggering the PR requirement.

- [ ] **Step 3: Add required secrets to GitHub repo settings (manual UI step)**

Go to: GitHub repo → Settings → Secrets and variables → Actions → New repository secret

Add:
- `GH_TOKEN` — PAT with `repo` scope (for release job push + gh release create)
- `ANTHROPIC_API_KEY` — Anthropic API key (for Claude PR review + goldfish init in matrix)

- [ ] **Step 4: Verify branch protection by opening a test PR**

Create a branch, push a trivial commit, open a PR. Confirm:
- The PR shows `quality` and `test` as required checks
- The merge button is disabled until both pass
- `claude-review` appears as a check but is not required

---

## Phase 3 — In-Repo Docs

### Task 10: Create CONTRIBUTING.md

Documents branch naming, worktree workflow, conventional commit format, and local testing with `act`.

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Create CONTRIBUTING.md**

```markdown
# Contributing to goldfish

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
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md with branch, worktree, and commit conventions"
```

---

### Task 11: Create ROADMAP.md and configure GitHub Issues

**Files:**
- Create: `ROADMAP.md`

- [ ] **Step 1: Create ROADMAP.md**

```markdown
# Goldfish Roadmap

## Current focus

Building the CI/CD pipeline: quality gates, cross-platform testing,
automated versioning (git-cliff + hatch-vcs), and PyPI publishing.

## Near-term (next 1-2 releases)

- CI/CD pipeline complete (phases 0-3)
- Windows hook path formatting validated on real runner
- PyPI first publish of v0.1.0

## Longer-term direction

- uvbox-based self-bootstrapping binary distribution (users get goldfish
  without needing Python or uv pre-installed)
- Broader platform support (ARM runners once GitHub Actions free tier
  includes them)
- Dev container spec for local environment standardization

## Out of scope

- goldfish does not build search, embeddings, or graph functionality —
  those are provided by Semble, GitNexus, and OMEGA respectively
- No always-on processes or daemons — every operation opens, executes, closes
```

- [ ] **Step 2: Configure GitHub Issues labels**

```bash
# Create project-specific labels
gh label create "enhancement" --description "New capability" --color "a2eeef"
gh label create "idea" --description "Not yet committed, open for discussion" --color "e4e669"
gh label create "breaking" --description "Will require major version bump" --color "d73a4a"
gh label create "chore" --description "Maintenance, deps, CI" --color "ffffff"
gh label create "good first issue" --description "Small, well-scoped" --color "7057ff"
```

Expected: each command outputs the created label. Some labels (`bug`, `documentation`, `enhancement`) may already exist — `gh label create` will error if duplicate. Use `gh label edit` to update existing ones if needed.

- [ ] **Step 3: Create initial milestones**

```bash
gh api repos/miztertea/goldfish/milestones \
  -X POST \
  -f title="v0.1.0 — CI/CD pipeline" \
  -f description="First public release with full CI/CD pipeline"

gh api repos/miztertee/goldfish/milestones \
  -X POST \
  -f title="v0.2.0 — Platform validation" \
  -f description="Windows hook path fix, full cross-platform green CI"
```

- [ ] **Step 4: Commit ROADMAP.md**

```bash
git add ROADMAP.md
git commit -m "docs: add ROADMAP.md with current focus and long-term direction"
git push origin main
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| hatch-vcs dynamic version | Task 1 |
| Reset to 0.1.0 via git tag | Task 2 |
| cliff.toml + CHANGELOG.md | Task 2 |
| Claude Code detection in init | Task 3 |
| ruff, mypy, bandit, pip-audit | Task 4 |
| ci.yml quality + test + claude-review | Task 5 |
| ci.yml matrix (macOS + Windows) | Task 6 |
| ci.yml release (git-cliff + tag + GH Release) | Task 6 |
| Release loop prevention | Task 6 |
| fetch-depth: 0 for hatch-vcs | Task 6, Task 8 |
| shell: bash on all matrix steps | Task 6 |
| publish.yml OIDC Trusted Publisher | Task 8 |
| GitHub environment 'pypi' created | Task 8 (manual prerequisite) |
| Branch rulesets API | Task 9 |
| GH_TOKEN + ANTHROPIC_API_KEY secrets | Task 9 |
| CONTRIBUTING.md | Task 10 |
| ROADMAP.md | Task 11 |
| GitHub Issues labels + Milestones | Task 11 |
| act local CI documented | Task 10 |

### No placeholders confirmed ✓

All code blocks contain complete, runnable content. All commands show expected output. No TBDs.

### Type/name consistency ✓

- `check_dependency` used consistently throughout
- `GH_TOKEN` and `ANTHROPIC_API_KEY` secret names consistent across ci.yml and Task 9
- `quality`, `test` job names in ci.yml match the required_status_checks in the ruleset JSON
