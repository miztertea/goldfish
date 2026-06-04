import json
from unittest.mock import patch

from goldfishh.drain import _handle_task_completed, _handle_task_created, drain, handle_pre_compact, handle_session_start


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
    count = drain(queue=queue)
    assert count == 1
    assert queue.read_text().strip() == ""


def test_drain_clears_queue_after_processing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps({"hook_event_name": "Stop", "cwd": "."}) + "\n")
    drain(queue=queue)
    assert queue.read_text() == ""


def test_drain_processes_multiple_events(tmp_path):
    queue = tmp_path / "queue.jsonl"
    events = [
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s1"},
        {"hook_event_name": "Stop", "cwd": "/p", "session_id": "s2"},
    ]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    count = drain(queue=queue)
    assert count == 2
    assert queue.read_text().strip() == ""


def test_drain_unknown_event_type_does_nothing(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"hook_event_name": "UnknownEvent", "cwd": "/p"}
    queue.write_text(json.dumps(event) + "\n")
    with patch("goldfishh.drain.subprocess.run") as mock_run:
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
    with patch("goldfishh.drain.subprocess.run"):
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
    with (
        patch("goldfishh.drain.subprocess.run"),
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
    ):
        result = handle_session_start(event, vaults_root=tmp_path)
    wake_up = tmp_path / "myapp" / "_context" / "wake-up.md"
    assert wake_up.exists()
    assert isinstance(result, str) and len(result) > 0


def test_session_start_new_project_returns_first_session_message(tmp_path):
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with (
        patch("goldfishh.drain.subprocess.run"),
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
    ):
        result = handle_session_start(event, vaults_root=tmp_path)
    assert "first session" in result.lower() or "new project" in result.lower()


def test_pre_compact_writes_checkpoint_note(tmp_path):
    from goldfishh.vault import scaffold

    scaffold("myapp", vaults_root=tmp_path)
    event = {"hook_event_name": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
    with (
        patch("goldfishh.drain.subprocess.run"),
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
    ):
        handle_pre_compact(event, vaults_root=tmp_path)
    checkpoints = list((tmp_path / "myapp" / "Memory" / "Checkpoints").glob("*.md"))
    assert len(checkpoints) == 1
    assert "s1" in checkpoints[0].name


def test_session_start_existing_project_calls_omega_query(tmp_path):
    from unittest.mock import MagicMock

    from goldfishh.config import write_manifest

    write_manifest(
        "myapp", {"last_byte_offset": 100, "bootstrap_complete": True, "last_jsonl_file": ""}, vaults_root=tmp_path
    )
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s2"}
    with (
        patch("goldfishh.drain.subprocess.run") as mock_run,
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
        patch("goldfishh.drain.drain"),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="some context")
        handle_session_start(event, vaults_root=tmp_path)
    cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(c[0] == "omega" and "query" in c for c in cmds), "omega query must be called for existing project"


def test_task_created_writes_note_to_vault(tmp_path):
    event = {
        "hook_event_name": "TaskCreated",
        "task_id": "task-abc",
        "task_description": "Implement auth middleware",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfishh.drain.VAULTS_ROOT", tmp_path), patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        _handle_task_created(event, vaults_root=tmp_path)
    note = tmp_path / "myapp" / "Tasks" / "task-abc.md"
    assert note.exists()
    assert "Implement auth middleware" in note.read_text()


def test_task_completed_appends_completed_marker(tmp_path):
    from goldfishh.vault import scaffold, write_note

    scaffold("myapp", vaults_root=tmp_path)
    write_note(
        "myapp",
        "Tasks/task-abc.md",
        {
            "id": "task-abc",
            "type": "task",
            "valid_from": "2026-05-24",
            "superseded_by": None,
            "confidence": 1.0,
            "source_session": "s1",
            "source_offset": 0,
            "related": [],
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
    with patch("goldfishh.drain.VAULTS_ROOT", tmp_path), patch("goldfishh.config.VAULTS_ROOT", tmp_path):
        _handle_task_completed(event, vaults_root=tmp_path)
    content = (tmp_path / "myapp" / "Tasks" / "task-abc.md").read_text()
    assert "Completed" in content


def test_stop_advances_manifest_offset(tmp_path):
    from goldfishh.config import get_manifest as gm
    from goldfishh.config import write_manifest as wm

    # Seed the manifest
    wm(
        "myapp",
        {"last_byte_offset": 0, "bootstrap_complete": True, "semble_indexed_at": "", "last_jsonl_file": ""},
        vaults_root=tmp_path,
    )
    # Create a fake JSONL file with some content
    jsonl_file = tmp_path / "session1.jsonl"
    jsonl_file.write_text('{"type":"Stop"}\n{"type":"Stop"}\n')

    from goldfishh.drain import _handle_stop

    event = {
        "hook_event_name": "Stop",
        "cwd": "/project/myapp",
        "session_id": "s1",
        "transcript_path": str(jsonl_file),
    }
    with (
        patch("goldfishh.drain.subprocess.run"),
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
    ):
        _handle_stop(event, vaults_root=tmp_path)

    manifest = gm("myapp", vaults_root=tmp_path)
    assert manifest["last_byte_offset"] == jsonl_file.stat().st_size
    assert manifest["last_jsonl_file"] == "session1.jsonl"


def test_drain_budget_zero_processes_all(tmp_path):
    """budget_ms=0 (default) means no time limit — all events processed."""
    queue = tmp_path / "queue.jsonl"
    events = [{"hook_event_name": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    with patch("goldfishh.drain.subprocess.run"):
        count = drain(queue=queue, budget_ms=0)
    assert count == 3
    assert queue.read_text().strip() == ""


def test_drain_budget_ms_leaves_unprocessed_events(tmp_path):
    """When budget expires, remaining events stay in queue for next cycle."""
    queue = tmp_path / "queue.jsonl"
    events = [{"hook_event_name": "Stop", "cwd": "/p", "session_id": f"s{i}"} for i in range(3)]
    queue.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    # Make deadline expire immediately: first call sets deadline, second check returns huge value
    with patch("goldfishh.drain.subprocess.run"), patch("goldfishh.drain.time.monotonic", side_effect=[0, 100]):
        count = drain(queue=queue, budget_ms=1)

    assert count == 0
    remaining = [line for line in queue.read_text().splitlines() if line.strip()]
    assert len(remaining) == 3


def test_session_start_auto_drains_queue(tmp_path):
    """handle_session_start must call drain(budget_ms=200) before processing."""
    event = {"hook_event_name": "SessionStart", "cwd": "/project/myapp", "session_id": "s1"}
    with (
        patch("goldfishh.drain.subprocess.run"),
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
        patch("goldfishh.drain.drain") as mock_drain,
    ):
        mock_drain.return_value = 0
        handle_session_start(event, vaults_root=tmp_path)
    mock_drain.assert_called_once_with(budget_ms=200)


def test_pre_compact_auto_drains_queue(tmp_path):
    """handle_pre_compact must call drain(budget_ms=200) before snapshotting."""
    from goldfishh.vault import scaffold

    scaffold("myapp", vaults_root=tmp_path)
    event = {"hook_event_name": "PreCompact", "cwd": "/project/myapp", "session_id": "s1"}
    with (
        patch("goldfishh.drain.subprocess.run"),
        patch("goldfishh.drain.VAULTS_ROOT", tmp_path),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path),
        patch("goldfishh.drain.drain") as mock_drain,
    ):
        mock_drain.return_value = 0
        handle_pre_compact(event, vaults_root=tmp_path)
    mock_drain.assert_called_once_with(budget_ms=200)


def test_session_start_includes_open_tasks_in_wakeup(tmp_path):
    """Tasks/ with an incomplete note → body contains the task stem."""
    from goldfishh.config import write_manifest

    project = "myapp"
    vaults_root = tmp_path / "vaults"
    tasks_dir = vaults_root / project / "Tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "implement-auth.md").write_text("# implement-auth\n\nDo the thing.\n")
    write_manifest(
        project,
        {"last_byte_offset": 0, "bootstrap_complete": True, "semble_indexed_at": "", "last_jsonl_file": ""},
        vaults_root=vaults_root,
    )

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with (
        patch("goldfishh.drain.subprocess.run") as mock_run,
        patch("goldfishh.drain.VAULTS_ROOT", vaults_root),
        patch("goldfishh.config.VAULTS_ROOT", vaults_root),
    ):
        mock_run.return_value = None
        result = handle_session_start(event, vaults_root=vaults_root)

    assert "implement-auth" in result


def test_session_start_includes_recent_decisions(tmp_path):
    """Decisions/ with files → body lists their headings."""
    from goldfishh.config import write_manifest

    project = "myapp"
    vaults_root = tmp_path / "vaults"
    decisions_dir = vaults_root / project / "Memory" / "Decisions"
    decisions_dir.mkdir(parents=True)
    (decisions_dir / "use-jwt.md").write_text("# Use JWT for auth\n\nBecause stateless.\n")
    write_manifest(
        project,
        {"last_byte_offset": 0, "bootstrap_complete": True, "semble_indexed_at": "", "last_jsonl_file": ""},
        vaults_root=vaults_root,
    )

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with (
        patch("goldfishh.drain.subprocess.run") as mock_run,
        patch("goldfishh.drain.VAULTS_ROOT", vaults_root),
        patch("goldfishh.config.VAULTS_ROOT", vaults_root),
    ):
        mock_run.return_value = None
        result = handle_session_start(event, vaults_root=vaults_root)

    assert "Use JWT for auth" in result


def test_session_start_excludes_completed_tasks(tmp_path):
    """Tasks marked **Completed.** must not appear in the wake-up body."""
    from goldfishh.config import write_manifest

    project = "myapp"
    vaults_root = tmp_path / "vaults"
    tasks_dir = vaults_root / project / "Tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "done-task.md").write_text("# done-task\n\n**Completed.**\n")
    (tasks_dir / "open-task.md").write_text("# open-task\n\nStill to do.\n")
    write_manifest(
        project,
        {"last_byte_offset": 0, "bootstrap_complete": True, "semble_indexed_at": "", "last_jsonl_file": ""},
        vaults_root=vaults_root,
    )

    event = {"session_id": "s1", "cwd": str(tmp_path / "myapp")}
    with (
        patch("goldfishh.drain.subprocess.run") as mock_run,
        patch("goldfishh.drain.VAULTS_ROOT", vaults_root),
        patch("goldfishh.config.VAULTS_ROOT", vaults_root),
    ):
        mock_run.return_value = None
        result = handle_session_start(event, vaults_root=vaults_root)

    assert "done-task" not in result
    assert "open-task" in result
