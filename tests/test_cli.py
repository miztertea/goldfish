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
