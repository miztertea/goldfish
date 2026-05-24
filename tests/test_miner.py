import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# These imports will fail until miner.py exists — that's the point
from goldfish.miner import (
    _extract_assistant_text,
    _extract_user_text,
    _find_hook_cmd,
    mine_project,
)


def _make_settings(auto_cmd: str, asst_cmd: str) -> dict:
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": auto_cmd}]}],
            "Stop": [{"hooks": [{"type": "command", "command": asst_cmd}]}],
        }
    }


def test_find_hook_cmd_returns_matching_command():
    settings = _make_settings("/python/fast_hook.py auto_capture", "/python/fast_hook.py assistant_capture")
    result = _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture")
    assert result == "/python/fast_hook.py auto_capture"


def test_find_hook_cmd_returns_none_when_not_found():
    settings = {"hooks": {"UserPromptSubmit": [{"hooks": [{"command": "other_tool"}]}]}}
    assert _find_hook_cmd(settings, "UserPromptSubmit", "auto_capture") is None


def test_extract_user_text_returns_string_content():
    obj = {"type": "user", "message": {"content": "hello world"}}
    assert _extract_user_text(obj) == "hello world"


def test_extract_user_text_returns_empty_for_list_content():
    obj = {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}}
    assert _extract_user_text(obj) == ""


def test_extract_assistant_text_joins_text_blocks():
    obj = {
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": "First part."},
            {"type": "tool_use", "name": "Read"},
            {"type": "text", "text": "Second part."},
        ]},
    }
    result = _extract_assistant_text(obj)
    assert "First part." in result
    assert "Second part." in result


def test_extract_assistant_text_returns_empty_for_empty_content():
    obj = {"type": "assistant", "message": {"content": []}}
    assert _extract_assistant_text(obj) == ""


def test_mine_project_returns_zero_when_sessions_dir_missing(tmp_path):
    # tmp_path has no .claude/projects/... subdirectory
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({}))
    n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=tmp_path / "nonexistent")
    assert n == 0


def test_mine_project_processes_user_messages(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "abc123.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "fix the auth middleware"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings(
        "/python fast_hook.py auto_capture",
        "/python fast_hook.py assistant_capture",
    )))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                         _sessions_dir=sessions_dir)

    assert n == 1
    assert mock_pipe.call_count >= 1
    payload = mock_pipe.call_args_list[0][0][1]
    assert payload["prompt"] == "fix the auth middleware"
    assert payload["session_id"] == "abc123"
    assert payload["cwd"] == "/home/tchawes/goldfish"


def test_mine_project_processes_assistant_messages(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "abc123.jsonl").write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "I fixed the auth middleware by updating JWT rotation."}]},
        }) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings(
        "/python fast_hook.py auto_capture",
        "/python fast_hook.py assistant_capture",
    )))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=sessions_dir)

    assert mock_pipe.call_count >= 1
    payload = mock_pipe.call_args_list[0][0][1]
    assert "last_assistant_message" in payload
    assert "JWT rotation" in payload["last_assistant_message"]


def test_mine_project_skips_already_mined_sessions(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "already-done.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "some prompt"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": ["already-done"]}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                         _sessions_dir=sessions_dir)

    assert n == 0
    mock_pipe.assert_not_called()


def test_mine_project_skips_non_message_entries(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    entries = [
        {"type": "ai-title", "title": "Session Title"},
        {"type": "permission-mode", "mode": "default"},
        {"type": "file-history-snapshot", "files": []},
        {"type": "user", "message": {"content": "real prompt"}},
    ]
    (sessions_dir / "sess1.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))

    with patch("goldfish.miner._pipe_to_hook") as mock_pipe, \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest"), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=sessions_dir)

    assert mock_pipe.call_count == 1  # only the user message


def test_mine_project_timeout_skips_manifest_write(tmp_path):
    """If OMEGA times out mid-session, the session is not marked as mined so it can be retried."""
    import subprocess
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "sess_timeout.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "some prompt"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))
    written = []

    with patch("goldfish.miner._pipe_to_hook", side_effect=subprocess.TimeoutExpired("cmd", 10)), \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest", side_effect=lambda proj, data, **kw: written.append(data)), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        n = mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                         _sessions_dir=sessions_dir)

    assert n == 0
    assert written == []  # manifest never updated for timed-out session


def test_mine_project_updates_manifest_with_session_id(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "sess1.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "prompt"}}) + "\n"
    )
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps(_make_settings("auto_capture", "assistant_capture")))
    written = []

    with patch("goldfish.miner._pipe_to_hook"), \
         patch("goldfish.miner.get_manifest", return_value={"mined_sessions": []}), \
         patch("goldfish.miner.write_manifest", side_effect=lambda proj, data, **kw: written.append(data)), \
         patch("goldfish.miner.project_name", return_value="goldfish"):
        mine_project("/home/tchawes/goldfish", settings_path=settings_path,
                     _sessions_dir=sessions_dir)

    assert written
    assert "sess1" in written[-1]["mined_sessions"]
