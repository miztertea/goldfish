import json
from pathlib import Path
from unittest.mock import patch

from goldfish.drain import drain


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
