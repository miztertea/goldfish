import json
import sys
from pathlib import Path
from unittest.mock import patch

from goldfish.hook import handle


def test_hook_appends_event_to_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "session_id": "abc123"}
    handle(event, queue=queue)
    lines = queue.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == event


def test_hook_appends_multiple_events_in_order(tmp_path):
    queue = tmp_path / "queue.jsonl"
    handle({"type": "Stop", "n": 1}, queue=queue)
    handle({"type": "Stop", "n": 2}, queue=queue)
    lines = queue.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["n"] == 1
    assert json.loads(lines[1])["n"] == 2


def test_hook_creates_parent_dirs(tmp_path):
    queue = tmp_path / "nested" / "dir" / "queue.jsonl"
    handle({"type": "Stop"}, queue=queue)
    assert queue.exists()


def test_async_event_appends_to_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "Stop", "session_id": "s1", "cwd": "/p"}
    from goldfish.hook import main_with_event
    main_with_event(event, queue=queue)
    assert queue.exists()
    assert len(queue.read_text().splitlines()) == 1


def test_sync_session_start_writes_stdout_not_queue(tmp_path, capsys):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "SessionStart", "session_id": "s1", "cwd": "/project/myapp"}
    with patch("goldfish.hook.handle_session_start", return_value="wake-up content"):
        from goldfish.hook import main_with_event
        main_with_event(event, queue=queue)
    captured = capsys.readouterr()
    assert "wake-up content" in captured.out
    # Sync events do NOT go to the queue
    assert not queue.exists()


def test_sync_pre_compact_calls_handler(tmp_path, capsys):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "PreCompact", "session_id": "s1", "cwd": "/p"}
    with patch("goldfish.hook.handle_pre_compact") as mock_handler:
        from goldfish.hook import main_with_event
        main_with_event(event, queue=queue)
    mock_handler.assert_called_once_with(event)
    captured = capsys.readouterr()
    assert captured.out == ""  # PreCompact returns nothing to stdout


def test_unknown_event_type_goes_to_queue(tmp_path):
    queue = tmp_path / "queue.jsonl"
    event = {"type": "SomeNewEvent", "cwd": "/p"}
    from goldfish.hook import main_with_event
    main_with_event(event, queue=queue)
    assert queue.exists()
    assert len(queue.read_text().splitlines()) == 1


def test_hook_short_prompt_produces_no_stdout(tmp_path, capsys):
    event = {"type": "UserPromptSubmit", "prompt": "yes", "cwd": "/p", "session_id": "s1"}
    with patch("goldfish.hook.enrich", return_value=""):
        from goldfish.hook import main_with_event
        main_with_event(event, queue=tmp_path / "queue.jsonl")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_hook_long_prompt_calls_enrich_and_writes_stdout(tmp_path, capsys):
    event = {
        "type": "UserPromptSubmit",
        "prompt": "fix the authentication middleware and refactor the JWT rotation policy",
        "cwd": "/project/myapp",
        "session_id": "s1",
    }
    with patch("goldfish.hook.enrich", return_value="## Goldfish Context\n\nsome results"):
        from goldfish.hook import main_with_event
        main_with_event(event, queue=tmp_path / "queue.jsonl")
    captured = capsys.readouterr()
    assert "Goldfish Context" in captured.out
