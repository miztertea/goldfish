import shutil
import subprocess
import sys
from pathlib import Path

from goldfish.claude_md import GOLDFISH_SENTINEL, append_claude_md_block, register_hooks
from goldfish.config import (
    DEFAULT_SETTINGS,
    VAULTS_ROOT,
    get_manifest,
    is_new_project,
    project_name,
    write_manifest,
)
from goldfish.miner import mine_project
from goldfish.vault import scaffold

_PACKAGE_SOURCE = "git+https://github.com/miztertea/goldfish"


def _goldfish_stable_path() -> Path:
    return Path.home() / ".local" / "bin" / "goldfish"


_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

goldfish coordinates four layers of agent intelligence. All four are available from session start.

| Layer | What it is | When it loads |
|-------|-----------|--------------|
| Layer 0 — MEMORY.md | File-based: user prefs, behavioral feedback, reference pointers | Automatic — zero latency |
| Layer 1 — OMEGA | Episodic memory: decisions, sessions, known issues | Required at session start (step 2) |
| Layer 1 — GitNexus / Semble | Code graph + semantic search | MCP on demand |
| Layer 2 — Goldfish | This coordination block — session sequence, layer routing | Always present |
| Layer 3 — Project | Project constitution — constraints, architecture rules, five failures | Always present |

### Memory Router

| Content type | System | How |
|---|---|---|
| User preferences, behavioral feedback, reference pointers | Auto-memory (Write tool → `memory/*.md`) | Write file directly |
| Session decisions, lessons, known issues | OMEGA | `omega_store()` |
| Architectural summaries, design notes | Goldfish vault | explicit `write_note()` when human audience warrants it |

For reads: auto-memory is authoritative for user preferences; `omega_profile()` is supplemental — additional signal, not ground truth.

Vault = consumer is human (Obsidian-readable narrative, long-form). OMEGA = consumer is agent (machine-queryable, episodic). Write to vault when a human should find and read this note. Architectural decisions may warrant both; session facts warrant OMEGA only. Goldfish hooks automatically write vault notes for task events and session checkpoints — architectural summaries require explicit agent writes.

Before acting on a project memory that makes code-specific claims (file paths, function names, shipped state), verify against `git log` or a file read.

### Session Start (required)

Steps 2–3 are initialization calls, not task responses. The skill-check in step 4 applies to the user's first request.

1. MEMORY.md loads automatically — no action needed
2. Call `omega_welcome()` — context briefing and recent activity
3. Call `omega_protocol()` — supplements CLAUDE.md with any session-specific rules; on free tier this is minimal, CLAUDE.md is the authoritative protocol
4. Check for applicable skills before responding to the user's first request
5. Work begins

> GitNexus/Semble load on-demand — intentional just-in-time delivery, not a gap. Targeted context arrives exactly when the relevant question is asked.

### Before Any Non-Trivial Task

Query all three intelligence tools:
- **GitNexus** — call graph, blast radius, execution flows
- **OMEGA** — prior decisions, session history, known issues
- **Semble** — code by meaning, vault notes

> **GitNexus staleness:** The stale warning fires after every commit — expected during active development. Re-analyze (`npx gitnexus analyze`) before code intelligence tasks (impact analysis, exploration), not after every commit. Prefer worktrees for feature development — each worktree has its own `.gitnexus/` index. See `superpowers:using-git-worktrees`.

Before spawning subagents: `omega_query()` first, inject results into agent prompt — subagents cannot call MCP tools (OMEGA, GitNexus, Semble).

GitNexus usage instructions are in the auto-maintained block below. OMEGA and Semble deliver their instructions via MCP server context at session start.
"""


def check_dependency(cmd: str) -> bool:
    try:
        result = subprocess.run([cmd, "--version"], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def run(
    cwd: str = ".",
    settings_path: Path = DEFAULT_SETTINGS,
    vaults_root: Path = VAULTS_ROOT,
) -> None:
    # Self-install for stable hook path
    stable = _goldfish_stable_path()
    if stable.exists():
        print("✓ goldfish installed (stable path)")
    else:
        r = subprocess.run(["uv", "tool", "install", "--from", _PACKAGE_SOURCE, "goldfish"])
        if r.returncode != 0:
            print("  note: goldfish self-install failed; hook path may be unstable")
        else:
            print("✓ goldfish installed at ~/.local/bin/goldfish")

    project = project_name(cwd)

    # Claude Code — install via npm if missing (non-fatal, log only)
    if not check_dependency("claude"):
        print("  Installing Claude Code...")
        try:
            result = subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"])
            if result.returncode != 0:
                print("  note: Claude Code install failed; install manually from claude.ai/code")
            else:
                print("✓ Claude Code installed")
        except (FileNotFoundError, OSError):
            print("  note: npm not available; install Claude Code manually from claude.ai/code")
    else:
        print("✓ Claude Code found")

    if not check_dependency("node"):
        print("✗ Node.js missing — required for GitNexus. Install from https://nodejs.org")
        sys.exit(1)
    print("✓ Node.js found")

    # GitNexus — skip if already indexed
    gitnexus_index = Path(cwd) / ".gitnexus"
    if gitnexus_index.exists():
        print("✓ GitNexus already indexed")
    else:
        print("  Installing GitNexus...")
        result = subprocess.run(["npm", "install", "-g", "gitnexus"], capture_output=True)
        if result.returncode != 0:
            print("  note: global npm install failed; using npx")
        result2 = subprocess.run(["npx", "gitnexus", "analyze"], cwd=cwd)
        if result2.returncode != 0:
            print("✗ GitNexus analyze failed. Check npm/Node.js installation.")
            sys.exit(1)
        print("✓ GitNexus indexed")

    # OMEGA — skip if already installed
    if shutil.which("omega"):
        print("✓ OMEGA already installed")
    else:
        print("  Installing OMEGA...")
        r1 = subprocess.run(["uv", "tool", "install", "omega-memory[server]"])
        if r1.returncode != 0:
            print("✗ OMEGA install failed.")
            sys.exit(1)
        print("✓ OMEGA installed")

    # Semble — skip if already installed
    if shutil.which("semble"):
        print("✓ Semble already installed")
    else:
        print("  Installing Semble...")
        r = subprocess.run(["uv", "tool", "install", "semble"])
        if r.returncode != 0:
            print("✗ Semble install failed.")
            sys.exit(1)
        print("✓ Semble installed")

    # Semble sub-agent — creates .claude/agents/semble-search.md (idempotent)
    subprocess.run(["semble", "init"], cwd=cwd, capture_output=True)
    print("✓ Semble sub-agent configured")

    # Vault
    if is_new_project(project, vaults_root=vaults_root):
        scaffold(project, vaults_root=vaults_root)
        manifest = get_manifest(project, vaults_root=vaults_root)
        manifest["bootstrap_complete"] = True
        write_manifest(project, manifest, vaults_root=vaults_root)
        print(f"✓ Vault scaffolded at {vaults_root / project}")
    else:
        print(f"✓ Vault exists at {vaults_root / project}")
        n = mine_project(cwd)
        if n:
            print(f"✓ Mined {n} historical session(s) into OMEGA memory.")

    # MCP registration — each tool registers its own MCP via its own CLI
    manifest = get_manifest(project, vaults_root=vaults_root)
    if not manifest.get("mcp_registered"):
        print("  Registering MCP servers...")
        try:
            subprocess.run(["npx", "gitnexus", "setup"], cwd=cwd)
        except FileNotFoundError:
            print("  note: gitnexus setup not available; skipping")
        try:
            subprocess.run(["claude", "mcp", "add", "gitnexus", "-s", "user", "--", "npx", "gitnexus", "mcp"])
        except FileNotFoundError:
            print("  note: claude CLI not available; skipping gitnexus MCP registration")
        try:
            print("  Downloading OMEGA embedding model (~127 MB, one-time)...")
            subprocess.run(["omega", "setup", "--download-model"])
            subprocess.run(["omega", "setup", "--client", "claude-code"])
        except FileNotFoundError:
            print("  note: omega setup not available; skipping")
        try:
            subprocess.run(
                ["claude", "mcp", "add", "semble", "-s", "user", "--", "uvx", "--from", "semble[mcp]", "semble"]
            )
        except FileNotFoundError:
            print("  note: claude CLI not available; skipping semble MCP registration")
        manifest["mcp_registered"] = True
        write_manifest(project, manifest, vaults_root=vaults_root)
        print("✓ MCPs registered (GitNexus, OMEGA, Semble)")
    else:
        print("✓ MCPs already registered")

    # Hooks — always upsert (ensures path and events are current)
    register_hooks(settings_path=settings_path)
    print("✓ Hooks registered")

    # CLAUDE.md
    claude_md = Path(cwd) / "CLAUDE.md"
    if claude_md.exists():
        append_claude_md_block(claude_md, _CLAUDE_MD_BLOCK)
        print("✓ CLAUDE.md updated")

    print("\n✓ goldfish is ready.")
    print(f"  Vault: {vaults_root / project}")
