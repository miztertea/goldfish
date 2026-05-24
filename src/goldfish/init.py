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
from goldfish.vault import scaffold

_PACKAGE_SOURCE = "git+https://github.com/miztertea/goldfish"


def _goldfish_stable_path() -> Path:
    return Path.home() / ".local" / "bin" / "goldfish"


_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

### Before any non-trivial task — query all three layers:

#### Code + Impact Intelligence — GitNexus (MCP)
- `query({{query}})` — hybrid BM25+semantic search across code graph
- `context({{name}})` — 360° view of any symbol (callers, callees, processes)
- `impact({{target}}, direction="upstream")` — blast radius before ANY change
- `detect_changes()` — map staged changes to affected processes pre-commit

#### Episodic Memory — OMEGA (MCP)
- `omega_query("why did we choose JWT")` — past decisions
- `omega_query("rate limiter bug")` — known issues
- `omega_query("Sarah rate limiter")` — person + topic references

#### Semantic Search — Semble (MCP)
- `semble_search(query, path="./src")` — code search by meaning
- `semble_search(query, path="~/.goldfish/vaults/<project>", content="docs")` — vault notes

### Mandatory workflow before refactoring:
1. `gitnexus context({{name}})` → understand the symbol
2. `gitnexus impact({{target}})` → know what breaks
3. `omega_query(topic)` → check past decisions
4. Then act.
"""


def check_dependency(cmd: str) -> bool:
    result = subprocess.run([cmd, "--version"], capture_output=True)
    return result.returncode == 0


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
        r1 = subprocess.run(["uv", "tool", "install", "omega-memory"])
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

    # Vault
    if is_new_project(project, vaults_root=vaults_root):
        scaffold(project, vaults_root=vaults_root)
        manifest = get_manifest(project, vaults_root=vaults_root)
        manifest["bootstrap_complete"] = True
        write_manifest(project, manifest, vaults_root=vaults_root)
        print(f"✓ Vault scaffolded at {vaults_root / project}")
    else:
        print(f"✓ Vault exists at {vaults_root / project}")

    # MCP registration — each tool registers its own MCP via its own CLI
    manifest = get_manifest(project, vaults_root=vaults_root)
    if not manifest.get("mcp_registered"):
        print("  Registering MCP servers...")
        try:
            subprocess.run(["npx", "gitnexus", "setup"], cwd=cwd)
        except FileNotFoundError:
            print("  note: gitnexus setup not available; skipping")
        try:
            subprocess.run(["omega", "setup", "--client", "claude-code"])
        except FileNotFoundError:
            print("  note: omega setup not available; skipping")
        try:
            subprocess.run([
                "claude", "mcp", "add", "semble", "-s", "user",
                "--", "uvx", "--from", "semble[mcp]", "semble"
            ])
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

    print(f"\n✓ goldfish is ready.")
    print(f"  Vault:    {vaults_root / project}")
    print(f"  Obsidian: open {vaults_root / project} as a vault (optional, no plugins needed)")
