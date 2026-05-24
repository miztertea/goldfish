import json
from unittest.mock import MagicMock, patch

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
    # Create ~/.claude.json with all three MCPs registered
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"mcpServers": {"omega-memory": {}, "semble": {}, "gitnexus": {}}}))
    # Create full vault structure
    project = tmp_path.name
    vaults_root = tmp_path / "vaults"
    for d in ["Memory/Decisions", "Memory/Lessons", "Memory/Errors", "Tasks", "Specs", "_context"]:
        (vaults_root / project / d).mkdir(parents=True)
    with patch("goldfish.cli.shutil.which", return_value="/usr/bin/node"), \
         patch("goldfish.cli.sp.run") as mock_run, \
         patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.QUEUE_PATH", tmp_path / "queue.jsonl"), \
         patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.cli.VAULTS_ROOT", vaults_root):
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output


def test_doctor_flags_missing_node(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {}}))
    (tmp_path / ".gitnexus").mkdir()
    # Provide minimal claude.json and vaults so only node check fails
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {}}))
    with patch("goldfish.cli.shutil.which", return_value=None), \
         patch("goldfish.cli.sp.run") as mock_run, \
         patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.QUEUE_PATH", tmp_path / "queue.jsonl"), \
         patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.cli.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "node" in result.output.lower() or "nodejs" in result.output.lower()


def test_replay_processes_jsonl_events(tmp_path):
    encoded = "/project/myapp".replace("/", "-")
    jsonl_dir = tmp_path / ".claude" / "projects" / encoded
    jsonl_dir.mkdir(parents=True)
    events = [
        {"type": "TaskCreated", "task_id": "t1", "task_description": "auth", "cwd": "/project/myapp", "session_id": "s1"},
    ]
    jsonl_file = jsonl_dir / "session1.jsonl"
    jsonl_file.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    vaults_root = tmp_path / ".goldfish" / "vaults"
    with patch("goldfish.cli.os.getcwd", return_value="/project/myapp"), \
         patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.cli.VAULTS_ROOT", vaults_root), \
         patch("goldfish.config.VAULTS_ROOT", vaults_root), \
         patch("goldfish.drain.VAULTS_ROOT", vaults_root), \
         patch("goldfish.drain._route") as mock_route:
        result = runner.invoke(app, ["replay"])

    assert result.exit_code == 0
    assert "processed" in result.output.lower()
    mock_route.assert_called_once_with(events[0])


def test_replay_resumes_from_offset(tmp_path):
    """replay skips lines before last_byte_offset in the resume file."""
    import json as json_mod
    from goldfish.config import write_manifest, get_manifest

    project = "myapp"
    vaults_root = tmp_path / "vaults"
    # cwd encodes to "-home-myapp" when slashes are replaced with dashes
    fake_cwd = "/home/myapp"
    encoded = fake_cwd.replace("/", "-")
    jsonl_dir = tmp_path / ".claude" / "projects" / encoded
    jsonl_dir.mkdir(parents=True)

    # Write a JSONL file with 3 lines; resume offset after line 1
    line1 = json_mod.dumps({"type": "Stop", "session_id": "s1"}) + "\n"
    line2 = json_mod.dumps({"type": "Stop", "session_id": "s2"}) + "\n"
    line3 = json_mod.dumps({"type": "Stop", "session_id": "s3"}) + "\n"
    jsonl_file = jsonl_dir / "20260101T000000.jsonl"
    jsonl_file.write_text(line1 + line2 + line3)

    # Resume after line 1
    write_manifest(project, {
        "last_byte_offset": len(line1.encode()),
        "last_jsonl_file": jsonl_file.name,
        "bootstrap_complete": True,
        "semble_indexed_at": "",
    }, vaults_root=vaults_root)

    routed_events = []

    def fake_route(event):
        routed_events.append(event)

    with patch("goldfish.cli.drain._route", side_effect=fake_route), \
         patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.cli.os.getcwd", return_value=fake_cwd), \
         patch("goldfish.cli.project_name", return_value=project), \
         patch("goldfish.cli.VAULTS_ROOT", vaults_root):
        result = runner.invoke(app, ["replay"])

    assert result.exit_code == 0, result.output

    # Only lines 2 and 3 should have been routed (line 1 was before the offset)
    assert len(routed_events) == 2
    assert routed_events[0]["session_id"] == "s2"
    assert routed_events[1]["session_id"] == "s3"

    # Manifest updated to end of file
    updated = get_manifest(project, vaults_root=vaults_root)
    assert updated["last_jsonl_file"] == jsonl_file.name
    assert updated["last_byte_offset"] == jsonl_file.stat().st_size


def test_register_hooks_command(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({}))
    with patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.claude_md.shutil.which", return_value="/usr/local/bin/goldfish"):
        result = runner.invoke(app, ["register-hooks"])
    assert result.exit_code == 0
    assert "hooks" in result.output.lower() or "registered" in result.output.lower()
    data = json.loads(settings.read_text())
    assert "Stop" in data.get("hooks", {})


def test_doctor_checks_mcp_registration(tmp_path):
    """~/.claude.json missing omega-memory → prints ✗ omega-memory MCP."""
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"mcpServers": {"semble": {}, "gitnexus": {}}}))

    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "/path/goldfish hook", "async": True}]}]
        }
    }))
    (tmp_path / ".gitnexus").mkdir()

    with patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.cli.sp.run") as mock_run, \
         patch("goldfish.cli.shutil.which", return_value="/usr/bin/node"), \
         patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.QUEUE_PATH", tmp_path / "queue.jsonl"), \
         patch("goldfish.cli.project_name", return_value="myapp"), \
         patch("goldfish.cli.VAULTS_ROOT", tmp_path / "vaults"):
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["doctor"])

    assert "✗ omega-memory MCP" in result.output
    assert "✓ semble MCP" in result.output


def test_doctor_checks_vault_structure(tmp_path):
    """Missing Tasks/ directory → prints ✗ vault/Tasks."""
    vaults_root = tmp_path / "vaults"
    # Create vault but omit Tasks/
    (vaults_root / "myapp" / "Memory" / "Decisions").mkdir(parents=True)
    (vaults_root / "myapp" / "Memory" / "Lessons").mkdir(parents=True)
    (vaults_root / "myapp" / "Memory" / "Errors").mkdir(parents=True)
    (vaults_root / "myapp" / "Specs").mkdir(parents=True)
    (vaults_root / "myapp" / "_context").mkdir(parents=True)
    # No Tasks/ dir

    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": "/path/goldfish hook", "async": True}]}]
        }
    }))
    (tmp_path / ".gitnexus").mkdir()

    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"mcpServers": {"omega": {}, "semble": {}, "gitnexus": {}}}))

    with patch("goldfish.cli.Path.home", return_value=tmp_path), \
         patch("goldfish.cli.sp.run") as mock_run, \
         patch("goldfish.cli.shutil.which", return_value="/usr/bin/node"), \
         patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.QUEUE_PATH", tmp_path / "queue.jsonl"), \
         patch("goldfish.cli.project_name", return_value="myapp"), \
         patch("goldfish.cli.VAULTS_ROOT", vaults_root):
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(app, ["doctor"])

    assert "✗ vault/Tasks" in result.output


def test_mine_command_reports_no_new_sessions(tmp_path):
    """mine prints 'no new sessions' and exits 0 when mine_project returns 0."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"command": "/python fast_hook.py auto_capture"}]}],
            "Stop": [{"hooks": [{"command": "/python fast_hook.py assistant_capture"}]}],
        }
    }))
    with patch("goldfish.cli.os.getcwd", return_value=str(tmp_path)), \
         patch("goldfish.cli.DEFAULT_SETTINGS", settings), \
         patch("goldfish.cli.mine_project", return_value=0) as mock_mine:
        result = runner.invoke(app, ["mine"])
    assert result.exit_code == 0
    assert "no new sessions" in result.output.lower()
    mock_mine.assert_called_once_with(str(tmp_path))
