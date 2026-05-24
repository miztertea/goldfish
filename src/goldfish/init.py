import subprocess
import sys
from pathlib import Path

from goldfish.claude_md import register_hooks, append_claude_md_block, GOLDFISH_SENTINEL
from goldfish.config import project_name, write_manifest, get_manifest, is_new_project, VAULTS_ROOT, DEFAULT_SETTINGS
from goldfish.vault import scaffold

_CLAUDE_MD_BLOCK = f"""{GOLDFISH_SENTINEL}

### Before any non-trivial task — query all three layers:

**GitNexus (MCP):** `query`, `context`, `impact`, `detect_changes`
**OMEGA (MCP):** `omega_query("why did we choose X")`
**Semble (MCP):** `semble_search(query, path=./src)`

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
    project = project_name(cwd)

    if not check_dependency("node"):
        print("ERROR: Node.js is required for GitNexus. Install from https://nodejs.org")
        sys.exit(1)

    print("Installing GitNexus...")
    subprocess.run(["npm", "install", "-g", "gitnexus"], check=True)
    subprocess.run(["npx", "gitnexus", "analyze"], cwd=cwd, check=True)

    print("Installing OMEGA...")
    subprocess.run(["pip", "install", "omega-memory"], check=True)
    subprocess.run(["omega", "setup"], check=True)

    print("Installing Semble...")
    subprocess.run(["uv", "tool", "install", "semble"], check=True)

    if is_new_project(project, vaults_root=vaults_root):
        scaffold(project, vaults_root=vaults_root)
        write_manifest(project, get_manifest(project, vaults_root=vaults_root), vaults_root=vaults_root)
        print(f"Vault scaffolded at {vaults_root / project}")
    else:
        print(f"Vault already exists at {vaults_root / project} — skipping scaffold")

    register_hooks(settings_path=settings_path)

    claude_md = Path(cwd) / "CLAUDE.md"
    if claude_md.exists():
        append_claude_md_block(claude_md, _CLAUDE_MD_BLOCK)

    print(f"\ngoldfish is ready. Launch Claude Code to begin.")
    print(f"Vault: {vaults_root / project}")
    print(f"Open {vaults_root / project} in Obsidian for a visual knowledge graph (optional).")
