import json
from pathlib import Path

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
