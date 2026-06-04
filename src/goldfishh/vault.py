from pathlib import Path

import yaml

VAULTS_ROOT = Path.home() / ".goldfish" / "vaults"

_VAULT_DIRS = [
    "Memory/Decisions",
    "Memory/Lessons",
    "Memory/Errors",
    "Memory/Checkpoints",
    "Specs",
    "Tasks",
    "_context",
]


def scaffold(project: str, vaults_root: Path = VAULTS_ROOT) -> None:
    for d in _VAULT_DIRS:
        (vaults_root / project / d).mkdir(parents=True, exist_ok=True)


def write_note(
    project: str,
    path: str,
    frontmatter: dict,
    body: str,
    vaults_root: Path = VAULTS_ROOT,
) -> None:
    note_path = vaults_root / project / path
    note_path.parent.mkdir(parents=True, exist_ok=True)
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
    note_path.write_text(f"---\n{fm_str}---\n{body}\n", encoding="utf-8")


def read_note(
    project: str,
    path: str,
    vaults_root: Path = VAULTS_ROOT,
) -> tuple[dict, str]:
    content = (vaults_root / project / path).read_text(encoding="utf-8")
    _, fm_str, body = content.split("---\n", 2)
    return yaml.safe_load(fm_str), body
