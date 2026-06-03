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
