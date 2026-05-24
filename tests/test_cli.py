import json
from unittest.mock import patch

from typer.testing import CliRunner

from goldfish.cli import app

runner = CliRunner()


def test_status_shows_queue_depth(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text('{"type":"Stop"}\n{"type":"Stop"}\n')
    with patch("goldfish.cli.QUEUE_PATH", queue), \
         patch("goldfish.cli.project_name", return_value="myapp"), \
         patch("goldfish.cli.get_manifest", return_value={
             "last_byte_offset": 100,
             "bootstrap_complete": True,
             "semble_indexed_at": "2026-05-24",
         }):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_status_shows_bootstrap_complete(tmp_path):
    with patch("goldfish.cli.QUEUE_PATH", tmp_path / "empty.jsonl"), \
         patch("goldfish.cli.project_name", return_value="myapp"), \
         patch("goldfish.cli.get_manifest", return_value={
             "last_byte_offset": 0,
             "bootstrap_complete": True,
             "semble_indexed_at": "",
         }):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "complete" in result.output.lower()


def test_status_shows_bootstrap_pending(tmp_path):
    with patch("goldfish.cli.QUEUE_PATH", tmp_path / "empty.jsonl"), \
         patch("goldfish.cli.project_name", return_value="newapp"), \
         patch("goldfish.cli.get_manifest", return_value={
             "last_byte_offset": 0,
             "bootstrap_complete": False,
             "semble_indexed_at": "",
         }):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "pending" in result.output.lower()


def test_doctor_all_healthy(tmp_path):
    # Create fake .gitnexus dir in tmp_path
    (tmp_path / ".gitnexus").mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "/path/goldfish hook", "async": True}]}]
        }
    }))
    with patch("goldfish.cli.shutil.which", return_value="/usr/bin/node"), \
         patch("goldfish.cli.sp.run") as mock_run, \
         patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.QUEUE_PATH", tmp_path / "queue.jsonl"):
        mock_run.return_value.returncode = 0  # omega status succeeds
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output


def test_doctor_flags_missing_node(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {}}))
    (tmp_path / ".gitnexus").mkdir()
    with patch("goldfish.cli.shutil.which", return_value=None), \
         patch("goldfish.cli.sp.run") as mock_run, \
         patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.QUEUE_PATH", tmp_path / "queue.jsonl"):
        mock_run.return_value.returncode = 0
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "node" in result.output.lower() or "nodejs" in result.output.lower()


def test_replay_processes_jsonl_events(tmp_path):
    # Create a fake JSONL transcript
    encoded = "/project/myapp".replace("/", "-")
    jsonl_dir = tmp_path / ".claude" / "projects" / encoded
    jsonl_dir.mkdir(parents=True)
    events = [
        {"type": "TaskCreated", "task_id": "t1", "task_description": "auth", "cwd": "/project/myapp", "session_id": "s1"},
    ]
    jsonl_file = jsonl_dir / "session1.jsonl"
    jsonl_file.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    with patch("goldfish.cli.os.getcwd", return_value="/project/myapp"), \
         patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path / ".goldfish" / "vaults"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path / ".goldfish" / "vaults"):
        result = runner.invoke(app, ["replay"])

    assert result.exit_code == 0
    assert "processed" in result.output.lower()
