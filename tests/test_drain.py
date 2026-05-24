import json
from pathlib import Path
from unittest.mock import patch

from goldfish.drain import drain, handle_pre_compact, handle_session_start


def test_drain_returns_zero_for_missing_queue(tmp_path):
    queue = tmp_path / "nonexistent.jsonl"
    assert drain(queue=queue) == 0


def test_drain_returns_zero_for_empty_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text("")
    assert drain(queue=queue) == 0


def test_drain_processes_one_event(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "cwd": "/home/user/project", "session_id": "s1"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 1
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "omega"


def test_drain_clears_queue_after_processing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps({"type": "Stop", "cwd": "."}) + "\n")
    with patch("goldfish.drain.subprocess.run"):
        drain(queue=queue)
    assert queue.read_text() == ""


def test_drain_processes_multiple_events(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        {"type": "Stop", "cwd": "/p", "session_id": "s1"},
        {"type": "Stop", "cwd": "/p", "session_id": "s2"},
    ]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 2
    assert mock_run.call_count == 2


def test_drain_routes_post_tool_use_write_to_semble(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {
        "type": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/my/project/src/auth.py"},
        "cwd": "/my/project",
    }
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        drain(queue=queue)
    args = mock_run.call_args[0][0]
    assert args[0] == "semble"
    assert "/my/project/src/auth.py" in args


def test_drain_unknown_event_type_does_nothing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "UnknownEvent", "cwd": "/p"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 1  # event was processed (no exception)
    mock_run.assert_not_called()  # but nothing happened


def test_drain_skips_bad_json_and_continues(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        "not-valid-json",
        json.dumps({"type": "Stop", "cwd": "/p"}),
    ]
    queue.write_text("\n".join(events) + "\n")
    with patch("goldfish.drain.subprocess.run"):
        count = drain(queue=queue)
    assert count == 1  # only the valid event processed


def test_drain_preserves_failed_lines_on_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text("not-valid-json\n")
    count = drain(queue=queue)
    assert count == 0
    assert "not-valid-json" in queue.read_text()


def test_session_start_new_project_creates_wake_up(tmp_path):
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        result = handle_session_start(event, vaults_root=tmp_path)
    wake_up = tmp_path / "myapp" / "_context" / "wake-up.md"
    assert wake_up.exists()
    assert isinstance(result, str) and len(result) > 0


def test_session_start_new_project_returns_first_session_message(tmp_path):
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        result = handle_session_start(event, vaults_root=tmp_path)
    assert "first session" in result.lower() or "new project" in result.lower()


def test_session_start_existing_project_calls_omega_mine(tmp_path):
    from goldfish.config import write_manifest
    write_manifest("myapp", {
        "last_byte_offset": 100, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=tmp_path)
    event = {"type": "SessionStart", "cwd": "/project/myapp", "session_id": "s2"}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        handle_session_start(event, vaults_root=tmp_path)
    cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(c[0] == "omega" for c in cmds)


def test_pre_compact_writes_checkpoint_note(tmp_path):
    from goldfish.vault import scaffold
    scaffold("myapp", vaults_root=tmp_path)
    event = {"type": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        handle_pre_compact(event, vaults_root=tmp_path)
    checkpoints = list((tmp_path / "myapp" / "Memory" / "Checkpoints").glob("*.md"))
    assert len(checkpoints) == 1
    assert "s1" in checkpoints[0].name


from goldfish.drain import _handle_post_tool_use


def test_post_tool_use_edit_calls_semble_reindex():
    event = {
        "type": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/project/src/main.py"},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfish.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "semble"
    assert cmd[1] == "reindex"
    assert "/project/src/main.py" in cmd


def test_post_tool_use_bash_git_commit_calls_omega_note():
    event = {
        "type": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'fix auth'"},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfish.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "omega"
    assert "note" in cmd


def test_post_tool_use_bash_non_commit_does_nothing():
    event = {
        "type": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfish.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    mock_run.assert_not_called()


def test_post_tool_use_unknown_tool_does_nothing():
    event = {
        "type": "PostToolUse",
        "tool_name": "WebFetch",
        "tool_input": {},
        "cwd": "/project",
        "session_id": "s1",
    }
    with patch("goldfish.drain.subprocess.run") as mock_run:
        _handle_post_tool_use(event)
    mock_run.assert_not_called()


from goldfish.drain import _handle_task_created, _handle_task_completed


def test_task_created_writes_note_to_vault(tmp_path):
    event = {
        "type": "TaskCreated",
        "task_id": "task-abc",
        "task_description": "Implement auth middleware",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        _handle_task_created(event, vaults_root=tmp_path)
    note = tmp_path / "myapp" / "Tasks" / "task-abc.md"
    assert note.exists()
    assert "Implement auth middleware" in note.read_text()


def test_task_completed_appends_completed_marker(tmp_path):
    from goldfish.vault import scaffold, write_note
    scaffold("myapp", vaults_root=tmp_path)
    write_note(
        "myapp",
        "Tasks/task-abc.md",
        {
            "id": "task-abc", "type": "task", "valid_from": "2026-05-24",
            "superseded_by": None, "confidence": 1.0, "source_session": "s1",
            "source_offset": 0, "related": [],
        },
        "Task body.",
        vaults_root=tmp_path,
    )
    event = {
        "type": "TaskCompleted",
        "task_id": "task-abc",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        _handle_task_completed(event, vaults_root=tmp_path)
    content = (tmp_path / "myapp" / "Tasks" / "task-abc.md").read_text()
    assert "Completed" in content


def test_stop_advances_manifest_offset(tmp_path):
    from goldfish.config import write_manifest as wm, get_manifest as gm
    # Seed the manifest
    wm("myapp", {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=tmp_path)
    # Create a fake JSONL file with some content
    jsonl_file = tmp_path / "session1.jsonl"
    jsonl_file.write_text('{"type":"Stop"}\n{"type":"Stop"}\n')

    from goldfish.drain import _handle_stop
    event = {
        "type": "Stop",
        "cwd": "/project/myapp",
        "session_id": "s1",
        "jsonl_file": str(jsonl_file),
    }
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        _handle_stop(event, vaults_root=tmp_path)

    manifest = gm("myapp", vaults_root=tmp_path)
    assert manifest["last_byte_offset"] == jsonl_file.stat().st_size
    assert manifest["last_jsonl_file"] == "session1.jsonl"
