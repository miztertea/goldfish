import json
import sys
from pathlib import Path
from unittest.mock import patch

from goldfish.claude_md import register_hooks, append_claude_md_block

GOLDFISH_SENTINEL = "## Agent Knowledge Tools (managed by goldfish)"


def test_register_hooks_adds_entries(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    assert "hooks" in data
    assert "Stop" in data["hooks"]


def test_register_hooks_is_idempotent(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    register_hooks(settings_path=settings)
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"]
    goldfish_entries = [h for h in stop_hooks[0]["hooks"] if "goldfish" in str(h)]
    assert len(goldfish_entries) == 1


def test_append_claude_md_block_adds_block(tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing content\n")
    append_claude_md_block(claude_md, GOLDFISH_SENTINEL + "\nsome content\n")
    assert GOLDFISH_SENTINEL in claude_md.read_text()


def test_append_claude_md_block_is_idempotent(tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Existing content\n")
    block = GOLDFISH_SENTINEL + "\nsome content\n"
    append_claude_md_block(claude_md, block)
    append_claude_md_block(claude_md, block)
    assert claude_md.read_text().count(GOLDFISH_SENTINEL) == 1


def test_register_hooks_uses_venv_bin_path(tmp_path):
    """When goldfish binary is found next to sys.executable, that full path is used."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({}))

    fake_venv_bin = tmp_path / "bin"
    fake_venv_bin.mkdir()
    fake_goldfish = fake_venv_bin / "goldfish"
    fake_goldfish.touch()

    fake_executable = str(fake_venv_bin / "python")

    # shutil.which returns None → fall back to venv sibling
    with patch("goldfish.claude_md.shutil.which", return_value=None), \
         patch("goldfish.claude_md.sys.executable", fake_executable):
        register_hooks(settings_path=settings)

    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"][0]["hooks"]
    assert len(stop_hooks) == 1
    command = stop_hooks[0]["command"]
    assert str(fake_goldfish) in command
    assert command.endswith(" hook")
