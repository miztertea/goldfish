from pathlib import Path
from unittest.mock import patch, call
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
         patch("goldfish.init.subprocess.run", side_effect=fake_run):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path)

    assert "npm" in calls        # npm install -g gitnexus
    assert "npx" in calls        # npx gitnexus analyze
    assert "pip" in calls        # pip install omega-memory
