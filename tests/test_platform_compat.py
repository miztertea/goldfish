"""Tests for cross-platform compatibility — Windows batch-file subprocess handling and UTF-8 encoding.

These run on Linux CI but cover Windows-specific code paths by mocking sys.platform
and subprocess.run to simulate the FileNotFoundError raised when calling npm.cmd/npx.cmd
without shell=True on Windows.
"""

from unittest.mock import MagicMock, patch

import pytest

from goldfishh.init import _run, check_dependency, run

# ---------------------------------------------------------------------------
# _run() helper
# ---------------------------------------------------------------------------


def test_run_returns_result_on_success():
    ok = MagicMock(returncode=0)
    with patch("goldfishh.init.subprocess.run", return_value=ok):
        result = _run(["node", "--version"])
    assert result is ok


def test_run_returns_none_on_file_not_found_non_windows():
    with (
        patch("goldfishh.init.subprocess.run", side_effect=FileNotFoundError),
        patch("sys.platform", "linux"),
    ):
        result = _run(["missing-command"])
    assert result is None


def test_run_returns_none_on_os_error_non_windows():
    with (
        patch("goldfishh.init.subprocess.run", side_effect=OSError),
        patch("sys.platform", "linux"),
    ):
        result = _run(["missing-command"])
    assert result is None


def test_run_retries_shell_true_on_windows_when_first_call_fails():
    """On Windows, FileNotFoundError triggers a shell=True retry (for npm.cmd / npx.cmd)."""
    ok = MagicMock(returncode=0)

    def fake_run(cmd, **kwargs):
        if kwargs.get("shell"):
            return ok
        raise FileNotFoundError

    with (
        patch("goldfishh.init.subprocess.run", side_effect=fake_run),
        patch("sys.platform", "win32"),
    ):
        result = _run(["npm", "install", "-g", "gitnexus"])

    assert result is ok


def test_run_returns_none_when_shell_retry_also_fails_on_windows():
    with (
        patch("goldfishh.init.subprocess.run", side_effect=FileNotFoundError),
        patch("sys.platform", "win32"),
    ):
        result = _run(["npm", "install", "-g", "gitnexus"])
    assert result is None


def test_run_passes_kwargs_through():
    ok = MagicMock(returncode=0)
    with patch("goldfishh.init.subprocess.run", return_value=ok) as mock_run:
        _run(["npm", "install"], capture_output=True, cwd="/tmp")
    mock_run.assert_called_once_with(["npm", "install"], capture_output=True, cwd="/tmp")


# ---------------------------------------------------------------------------
# check_dependency
# ---------------------------------------------------------------------------


def test_check_dependency_returns_false_on_file_not_found():
    with patch("goldfishh.init.subprocess.run", side_effect=FileNotFoundError):
        assert check_dependency("nonexistent-tool") is False


def test_check_dependency_returns_false_on_nonzero_returncode():
    with patch("goldfishh.init.subprocess.run", return_value=MagicMock(returncode=1)):
        assert check_dependency("broken-tool") is False


def test_check_dependency_returns_true_on_zero_returncode():
    with patch("goldfishh.init.subprocess.run", return_value=MagicMock(returncode=0)):
        assert check_dependency("node") is True


# ---------------------------------------------------------------------------
# init.run() — Windows npm/npx path
# ---------------------------------------------------------------------------


def test_init_npm_file_not_found_does_not_crash(tmp_path):
    """On Windows, FileNotFoundError from npm/npx must not propagate — _run() absorbs it."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")

    ok = MagicMock(returncode=0)

    def fake_run(cmd, **kwargs):
        # npm/npx raise FileNotFoundError on Windows without shell=True
        if not kwargs.get("shell") and isinstance(cmd, list) and cmd[0] in ("npm", "npx"):
            raise FileNotFoundError
        # shell=True retry succeeds
        return ok

    with (
        patch("goldfishh.init.subprocess.run", side_effect=fake_run),
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
        patch("sys.platform", "win32"),
    ):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")


def test_init_gitnexus_analyze_failure_causes_exit(tmp_path):
    """If npx gitnexus analyze returns non-zero, init must exit with code 1."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")

    fail = MagicMock(returncode=1)

    def fake_run(cmd, **kwargs):
        return fail

    with (
        patch("goldfishh.init.subprocess.run", side_effect=fake_run),
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value=None),
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
        pytest.raises(SystemExit),
    ):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")


# ---------------------------------------------------------------------------
# UTF-8 encoding — drain queue file
# ---------------------------------------------------------------------------


def test_drain_writes_queue_with_utf8(tmp_path):
    from goldfishh.drain import drain

    queue = tmp_path / "queue.jsonl"
    # Write an event that contains a non-ASCII checkpoint symbol
    queue.write_text('{"hook_event_name": "Stop", "note": "✓"}\n', encoding="utf-8")
    drain(queue=queue)
    # After draining, queue should still be readable as UTF-8
    remaining = queue.read_text(encoding="utf-8")
    assert isinstance(remaining, str)


def test_miner_reads_jsonl_with_utf8(tmp_path):
    from goldfishh.miner import mine_project

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    # Write a session JSONL with non-ASCII content
    session = sessions_dir / "abc123.jsonl"
    session.write_text(
        '{"type": "user", "message": {"content": "✓ hello"}}\n',
        encoding="utf-8",
    )
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    # mine_project should not raise on non-ASCII content
    mine_project(str(tmp_path), settings_path=settings, _sessions_dir=sessions_dir)
