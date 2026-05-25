# Security

## Scope

goldfish is a local CLI orchestration tool. It:
- Does not handle user authentication or store credentials
- Does not transmit data over the network
- Does not run as a server or daemon
- Writes files only to `~/.goldfish/` and the project directory

The primary security surface is the **hook integration**: goldfish registers shell commands that Claude Code executes on lifecycle events. A compromised goldfish binary or malicious `CLAUDE.md` could execute arbitrary commands in your shell.

## Responsible disclosure

Please report security vulnerabilities via GitHub's private vulnerability reporting:

**[github.com/miztertea/goldfish/security/advisories/new](https://github.com/miztertea/goldfish/security/advisories/new)**

Do not open public issues for security vulnerabilities.

## What's in scope

- Vulnerabilities in goldfish's Python dependencies
- Hook command injection via malformed event payloads from stdin
- Vault path traversal (writing outside `~/.goldfish/vaults/`)
- Any scenario where goldfish execution could escalate privileges

## What's out of scope

- Vulnerabilities in GitNexus, OMEGA, or Semble — report to their maintainers
- Issues requiring physical access to the machine
- Social engineering

## Response

We aim to acknowledge reports within 48 hours and provide a fix or workaround within 14 days for confirmed issues.
