import json
from pathlib import Path

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
