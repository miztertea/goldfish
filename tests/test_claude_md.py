import json
from unittest.mock import patch

from goldfishh.claude_md import append_claude_md_block, register_hooks

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
    goldfish_entries = [h for h in stop_hooks[0]["hooks"] if "goldfishh" in str(h)]
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
    fake_goldfishh = fake_venv_bin / "goldfishh"
    fake_goldfishh.touch()

    fake_executable = str(fake_venv_bin / "python")

    # shutil.which returns None → fall back to venv sibling
    with (
        patch("goldfishh.claude_md.shutil.which", return_value=None),
        patch("goldfishh.claude_md.sys.executable", fake_executable),
        patch("goldfishh.claude_md.Path.home", return_value=tmp_path),
    ):
        register_hooks(settings_path=settings)

    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"][0]["hooks"]
    assert len(stop_hooks) == 1
    command = stop_hooks[0]["command"]
    assert str(fake_goldfishh) in command
    assert command.endswith(" hook")


def test_register_hooks_updates_bare_command_to_full_path(tmp_path):
    """Existing 'goldfish hook' (bare) must be replaced with the full detected path."""
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "goldfish hook", "async": True}]}]}})
    )
    fake_venv_bin = tmp_path / "bin"
    fake_venv_bin.mkdir()
    (fake_venv_bin / "goldfishh").touch()
    with (
        patch("goldfishh.claude_md.shutil.which", return_value=None),
        patch("goldfishh.claude_md.sys.executable", str(fake_venv_bin / "python")),
    ):
        register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    stop_cmds = [h["command"] for h in data["hooks"]["Stop"][0]["hooks"]]
    assert len(stop_cmds) == 1
    assert stop_cmds[0] != "goldfishh hook"
    assert stop_cmds[0].endswith(" hook")
    assert "goldfishh" in stop_cmds[0]


def test_register_hooks_registers_all_nine_events(tmp_path):
    """All sync + async events must be present after register_hooks."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({}))
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    registered = set(data["hooks"].keys())
    required = {
        "SessionStart",
        "UserPromptSubmit",
        "PreCompact",
        "Stop",
        "SessionEnd",
        "PostToolUse",
        "SubagentStop",
        "TaskCreated",
        "TaskCompleted",
    }
    assert required <= registered


def test_register_hooks_preserves_non_goldfish_hooks(tmp_path):
    """Non-goldfish hooks in a touched event must survive upsert."""
    settings = tmp_path / "settings.json"
    gitnexus_hook = {"type": "command", "command": "npx gitnexus hook"}
    # Put a non-goldfish hook in Stop — an event register_hooks WILL touch
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [{"hooks": [gitnexus_hook]}],
                }
            }
        )
    )
    register_hooks(settings_path=settings)
    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"][0]["hooks"]
    # GitNexus hook must still be present alongside the new goldfish hook
    assert gitnexus_hook in stop_hooks
    assert any("goldfishh" in h.get("command", "") and h.get("command", "").endswith(" hook") for h in stop_hooks)


def test_append_claude_md_block_updates_content_in_place(tmp_path):
    """Second call with different content must update the block, not duplicate it."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# Project\n\nSome existing content.\n")

    old_block = GOLDFISH_SENTINEL + "\n\nOLD CONTENT HERE\n"
    new_block = GOLDFISH_SENTINEL + "\n\nNEW CONTENT HERE\n"

    append_claude_md_block(claude_md, old_block)
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert content.count(GOLDFISH_SENTINEL) == 1
    assert "NEW CONTENT HERE" in content
    assert "OLD CONTENT HERE" not in content


def test_append_claude_md_block_preserves_content_after_block(tmp_path):
    """Content in sections after the goldfish block must be preserved on update."""
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "# Project\n\n" + GOLDFISH_SENTINEL + "\n\nOLD CONTENT\n\n" + "## Other Section\n\nKeep this.\n"
    )

    new_block = GOLDFISH_SENTINEL + "\n\nNEW CONTENT\n"
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert "Keep this." in content
    assert "NEW CONTENT" in content
    assert "OLD CONTENT" not in content
    assert content.count(GOLDFISH_SENTINEL) == 1


def test_append_claude_md_block_eof_case(tmp_path):
    """Block at EOF (no following sections) must be replaced cleanly."""
    claude_md = tmp_path / "CLAUDE.md"
    old_block = GOLDFISH_SENTINEL + "\n\nOLD\n"
    claude_md.write_text("# Header\n\n" + old_block)

    new_block = GOLDFISH_SENTINEL + "\n\nNEW\n"
    append_claude_md_block(claude_md, new_block)

    content = claude_md.read_text()
    assert "NEW" in content
    assert "OLD" not in content
    assert content.count(GOLDFISH_SENTINEL) == 1


def test_detect_goldfish_bin_prefers_local_bin(tmp_path):
    from goldfishh.claude_md import _detect_goldfish_bin

    local_bin = tmp_path / ".local" / "bin" / "goldfishh"
    local_bin.parent.mkdir(parents=True)
    local_bin.touch()
    with patch("goldfishh.claude_md.Path.home", return_value=tmp_path):
        result = _detect_goldfish_bin()
    assert result == str(local_bin)


def test_detect_goldfish_bin_falls_back_to_which(tmp_path):
    from goldfishh.claude_md import _detect_goldfish_bin

    # tmp_path/.local/bin/goldfish does NOT exist
    with (
        patch("goldfishh.claude_md.Path.home", return_value=tmp_path),
        patch("goldfishh.claude_md.shutil.which", return_value="/usr/local/bin/goldfishh"),
    ):
        result = _detect_goldfish_bin()
    assert result == "/usr/local/bin/goldfishh"
