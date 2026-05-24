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
    event = {"hook_event_name": "Stop", "cwd": "/home/user/project", "session_id": "s1"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 1
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "omega"


def test_drain_clears_queue_after_processing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps({"hook_event_name": "Stop", "cwd": "."}) + "\n")
    with patch("goldfish.drain.subprocess.run"):
        drain(queue=queue)
    assert queue.read_text() == ""


def test_drain_processes_multiple_events(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s1"},
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s2"},
    ]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 2
    assert mock_run.call_count == 2


def test_drain_routes_post_tool_use_write_to_semble(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {
        "hook_event_name": "PostToolUse",
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
    event = {"hook_event_name": "UnknownEvent", "cwd": "/p"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfish.drain.subprocess.run") as mock_run:
        count = drain(queue=queue)
    assert count == 1  # event was processed (no exception)
    mock_run.assert_not_called()  # but nothing happened


def test_drain_skips_bad_json_and_continues(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        "not-valid-json",
        json.dumps({"hook_event_name": "Stop", "cwd": "/p"}),
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
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        result = handle_session_start(event, vaults_root=tmp_path)
    wake_up = tmp_path / "myapp" / "_context" / "wake-up.md"
    assert wake_up.exists()
    assert isinstance(result, str) and len(result) > 0


def test_session_start_new_project_returns_first_session_message(tmp_path):
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
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
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s2"}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        handle_session_start(event, vaults_root=tmp_path)
    cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(c[0] == "omega" for c in cmds)


def test_pre_compact_writes_checkpoint_note(tmp_path):
    from goldfish.vault import scaffold
    scaffold("myapp", vaults_root=tmp_path)
    event = {"hook_event_name": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
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
        "hook_event_name": "PostToolUse",
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
        "hook_event_name": "PostToolUse",
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
        "hook_event_name": "PostToolUse",
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
        "hook_event_name": "PostToolUse",
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
        "hook_event_name": "TaskCreated",
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
        "hook_event_name": "TaskCompleted",
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
        "hook_event_name": "Stop",
        "cwd": "/project/myapp",
        "session_id": "s1",
        "transcript_path": str(jsonl_file),
    }
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path):
        _handle_stop(event, vaults_root=tmp_path)

    manifest = gm("myapp", vaults_root=tmp_path)
    assert manifest["last_byte_offset"] == jsonl_file.stat().st_size
    assert manifest["last_jsonl_file"] == "session1.jsonl"


def test_drain_budget_zero_processes_all(tmp_path):
    """budget_ms=0 (default) means no time limit — all events processed."""
    queue = tmp_path / "queue.jsonl"
    events = [{"hook_event_name": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfish.drain.subprocess.run"):
        count = drain(queue=queue, budget_ms=0)
    assert count == 3
    assert queue.read_text().strip() == ""


def test_drain_budget_ms_leaves_unprocessed_events(tmp_path):
    """When budget expires, remaining events stay in queue for next cycle."""
    queue = tmp_path / "queue.jsonl"
    events = [{"hook_event_name": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    # Make deadline expire immediately: first call sets deadline, second check returns huge value
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.time.monotonic", side_effect=[0, 100]):
        count = drain(queue=queue, budget_ms=1)

    assert count == 0
    remaining = [l for l in queue.read_text().splitlines() if l.strip()]
    assert len(remaining) == 3


def test_session_start_auto_drains_queue(tmp_path):
    """handle_session_start must call drain(budget_ms=200) before processing."""
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path), \
         patch("goldfish.drain.drain") as mock_drain:
        mock_drain.return_value = 0
        handle_session_start(event, vaults_root=tmp_path)
    mock_drain.assert_called_once_with(budget_ms=200)


def test_pre_compact_auto_drains_queue(tmp_path):
    """handle_pre_compact must call drain(budget_ms=200) before snapshotting."""
    from goldfish.vault import scaffold
    scaffold("myapp", vaults_root=tmp_path)
    event = {"hook_event_name": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
    with patch("goldfish.drain.subprocess.run"), \
         patch("goldfish.drain.VAULTS_ROOT", tmp_path), \
         patch("goldfish.config.VAULTS_ROOT", tmp_path), \
         patch("goldfish.drain.drain") as mock_drain:
        mock_drain.return_value = 0
        handle_pre_compact(event, vaults_root=tmp_path)
    mock_drain.assert_called_once_with(budget_ms=200)


def test_session_start_includes_open_tasks_in_wakeup(tmp_path):
    """Tasks/ with an incomplete note → body contains the task stem."""
    from goldfish.config import write_manifest
    project = "myapp"
    vaults_root = tmp_path / "vaults"
    tasks_dir = vaults_root / project / "Tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "implement-auth.md").write_text("# implement-auth\n\nDo the thing.\n")
    write_manifest(project, {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=vaults_root)

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", vaults_root), \
         patch("goldfish.config.VAULTS_ROOT", vaults_root):
        mock_run.return_value = None
        result = handle_session_start(event, vaults_root=vaults_root)

    assert "implement-auth" in result


def test_session_start_includes_recent_decisions(tmp_path):
    """Decisions/ with files → body lists their headings."""
    from goldfish.config import write_manifest
    project = "myapp"
    vaults_root = tmp_path / "vaults"
    decisions_dir = vaults_root / project / "Memory" / "Decisions"
    decisions_dir.mkdir(parents=True)
    (decisions_dir / "use-jwt.md").write_text("# Use JWT for auth\n\nBecause stateless.\n")
    write_manifest(project, {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=vaults_root)

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", vaults_root), \
         patch("goldfish.config.VAULTS_ROOT", vaults_root):
        mock_run.return_value = None
        result = handle_session_start(event, vaults_root=vaults_root)

    assert "Use JWT for auth" in result


def test_semble_indexed_at_written_after_index(tmp_path):
    """manifest semble_indexed_at is updated after semble index runs."""
    from goldfish.drain import handle_session_start
    from goldfish.config import get_manifest, write_manifest
    project = "myapp"
    vaults_root = tmp_path / "vaults"
    # Bootstrap so handle_session_start takes the existing-project path
    write_manifest(project, {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=vaults_root)

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", vaults_root), \
         patch("goldfish.config.VAULTS_ROOT", vaults_root), \
         patch("goldfish.drain.drain"):
        mock_run.return_value = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock(returncode=0)
        handle_session_start(event, vaults_root=vaults_root)

    manifest = get_manifest(project, vaults_root=vaults_root)
    assert manifest.get("semble_indexed_at"), "semble_indexed_at must be set after index"


def test_session_start_excludes_completed_tasks(tmp_path):
    """Tasks marked **Completed.** must not appear in the wake-up body."""
    from goldfish.config import write_manifest
    project = "myapp"
    vaults_root = tmp_path / "vaults"
    tasks_dir = vaults_root / project / "Tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "done-task.md").write_text("# done-task\n\n**Completed.**\n")
    (tasks_dir / "open-task.md").write_text("# open-task\n\nStill to do.\n")
    write_manifest(project, {
        "last_byte_offset": 0, "bootstrap_complete": True,
        "semble_indexed_at": "", "last_jsonl_file": ""
    }, vaults_root=vaults_root)

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with patch("goldfish.drain.subprocess.run") as mock_run, \
         patch("goldfish.drain.VAULTS_ROOT", vaults_root), \
         patch("goldfish.config.VAULTS_ROOT", vaults_root):
        mock_run.return_value = None
        result = handle_session_start(event, vaults_root=vaults_root)

    assert "done-task" not in result
    assert "open-task" in result
