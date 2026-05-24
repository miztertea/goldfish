from pathlib import Path
import tomllib
import tomli_w

VAULTS_ROOT = Path.home() / ".goldfish" / "vaults"
CONFIG_PATH = Path.home() / ".goldfish" / "config.toml"

_MANIFEST_DEFAULTS = {
    "last_byte_offset": 0,
    "last_jsonl_file": "",
    "bootstrap_complete": False,
    "semble_indexed_at": "",
}


def project_name(cwd: str) -> str:
    return Path(cwd).name


def _manifest_path(project: str, vaults_root: Path = VAULTS_ROOT) -> Path:
    return vaults_root / project / ".manifest.toml"


def is_new_project(project: str, vaults_root: Path = VAULTS_ROOT) -> bool:
    return not _manifest_path(project, vaults_root).exists()


def get_manifest(project: str, vaults_root: Path = VAULTS_ROOT) -> dict:
    path = _manifest_path(project, vaults_root)
    if not path.exists():
        return dict(_MANIFEST_DEFAULTS)
    with path.open("rb") as f:
        return {**_MANIFEST_DEFAULTS, **tomllib.load(f)}


def write_manifest(project: str, data: dict, vaults_root: Path = VAULTS_ROOT) -> None:
    path = _manifest_path(project, vaults_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(data, f)
