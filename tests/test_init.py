import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

from goldfish.init import check_dependency, run


def test_check_dependency_returns_true_when_found():
    with patch("goldfish.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert check_dependency("node") is True


def test_check_dependency_returns_false_when_not_found():
    with patch("goldfish.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        assert check_dependency("gitnexus-nonexistent") is False


def test_run_exits_early_if_node_missing(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with patch("goldfish.init.check_dependency", return_value=False), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         pytest.raises(SystemExit):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path)
    mock_run.assert_not_called()


def test_run_calls_install_steps_in_order(tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[0] if isinstance(cmd, list) else cmd)
        class R:
            returncode = 0
        return R()

    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    (tmp_path / "CLAUDE.md").write_text("# Existing\n")

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value=None), \
         patch("goldfish.init.subprocess.run", side_effect=fake_run):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path)

    assert "npm" in calls        # npm install -g gitnexus
    assert "npx" in calls        # npx gitnexus analyze
    assert "pip" in calls        # pip install omega-memory


def test_init_skips_gitnexus_if_already_indexed(tmp_path):
    """If .gitnexus/ exists, npx gitnexus analyze must NOT run."""
    (tmp_path / ".gitnexus").mkdir()
    settings = tmp_path / "settings.json"

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value="/usr/bin/omega"), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_analyze_ran = any(
        isinstance(c, list) and "gitnexus" in c and "analyze" in c
        for c in cmds
    )
    assert not gitnexus_analyze_ran, "gitnexus analyze must not run when .gitnexus/ already exists"


def test_init_skips_omega_if_already_installed(tmp_path):
    """If omega CLI is found on PATH, pip install omega-memory must NOT run."""
    settings = tmp_path / "settings.json"

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    pip_install_ran = any(
        isinstance(c, list) and "pip" in c and "omega-memory" in c
        for c in cmds
    )
    assert not pip_install_ran, "pip install omega-memory must not run when omega already on PATH"


def test_init_skips_semble_if_already_installed(tmp_path):
    """If semble CLI is found on PATH, uv tool install semble must NOT run."""
    settings = tmp_path / "settings.json"

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    semble_install_ran = any(
        isinstance(c, list) and "semble" in c and "install" in c
        for c in cmds
    )
    assert not semble_install_ran, "uv tool install semble must not run when semble already on PATH"


def test_init_runs_gitnexus_when_not_indexed(tmp_path):
    """If .gitnexus/ does not exist, npx gitnexus analyze must run."""
    settings = tmp_path / "settings.json"

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value=None), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / "vaults"), \
         patch("goldfish.init.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_analyze_ran = any(
        isinstance(c, list) and "gitnexus" in c and "analyze" in c
        for c in cmds
    )
    assert gitnexus_analyze_ran, "gitnexus analyze must run when .gitnexus/ does not exist"


def test_init_does_not_rescaffold_existing_vault(tmp_path):
    """On re-run, scaffold must not overwrite the existing vault."""
    from goldfish.config import write_manifest
    project_dir = tmp_path / "goldfish"
    project_dir.mkdir()
    vaults_root = tmp_path / "vaults"
    write_manifest("goldfish", {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=vaults_root)
    settings = tmp_path / "settings.json"

    with patch("goldfish.init.check_dependency", return_value=True), \
         patch("goldfish.init.shutil.which", return_value="/usr/bin/omega"), \
         patch("goldfish.init.subprocess.run") as mock_run, \
         patch("goldfish.config.VAULTS_ROOT", vaults_root), \
         patch("goldfish.init.VAULTS_ROOT", vaults_root), \
         patch("goldfish.init.scaffold") as mock_scaffold:
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(project_dir), settings_path=settings, vaults_root=vaults_root)

    mock_scaffold.assert_not_called()
