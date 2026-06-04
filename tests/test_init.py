from unittest.mock import MagicMock, patch

import pytest

from goldfishh.init import check_dependency, run


def test_check_dependency_returns_true_when_found():
    with patch("goldfishh.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert check_dependency("node") is True


def test_check_dependency_returns_false_when_not_found():
    with patch("goldfishh.init.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        assert check_dependency("gitnexus-nonexistent") is False


def test_run_exits_early_if_node_missing(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    stable = tmp_path / "goldfish"
    stable.touch()

    def dep_missing_node(cmd):
        return cmd != "node"  # node absent, claude and others present

    with (
        patch("goldfishh.init.check_dependency", side_effect=dep_missing_node),
        patch("goldfishh.init._goldfish_stable_path", return_value=stable),
        patch("goldfishh.init.subprocess.run") as mock_run,
        pytest.raises(SystemExit),
    ):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path)

    cmds = [c[0][0] for c in mock_run.call_args_list]
    gitnexus_ran = any(isinstance(c, list) and "gitnexus" in c for c in cmds)
    assert not gitnexus_ran, "gitnexus must not run when node is missing"


def test_run_calls_install_steps_in_order(tmp_path):
    all_cmds = []

    def fake_run(cmd, **kwargs):
        all_cmds.append(cmd if isinstance(cmd, list) else [cmd])

        class R:
            returncode = 0

        return R()

    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    (tmp_path / "CLAUDE.md").write_text("# Existing\n")

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value=None),
        patch("goldfishh.init.subprocess.run", side_effect=fake_run),
    ):
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path)

    flat = [tok for cmd in all_cmds for tok in cmd]
    assert "npm" in flat  # npm install -g gitnexus
    assert "npx" in flat  # npx gitnexus analyze
    assert "omega-memory[server]" in flat  # uv tool install omega-memory[server]


def test_init_skips_gitnexus_if_already_indexed(tmp_path):
    """If .gitnexus/ exists, npx gitnexus analyze must NOT run."""
    (tmp_path / ".gitnexus").mkdir()
    settings = tmp_path / "settings.json"

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_analyze_ran = any(isinstance(c, list) and "gitnexus" in c and "analyze" in c for c in cmds)
    assert not gitnexus_analyze_ran, "gitnexus analyze must not run when .gitnexus/ already exists"


def test_init_skips_omega_if_already_installed(tmp_path):
    """If omega CLI is found on PATH, pip install omega-memory must NOT run."""
    settings = tmp_path / "settings.json"

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    pip_install_ran = any(isinstance(c, list) and "pip" in c and "omega-memory" in c for c in cmds)
    assert not pip_install_ran, "pip install omega-memory must not run when omega already on PATH"


def test_init_skips_semble_if_already_installed(tmp_path):
    """If semble CLI is found on PATH, uv tool install semble must NOT run."""
    settings = tmp_path / "settings.json"

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    semble_install_ran = any(isinstance(c, list) and "semble" in c and "install" in c for c in cmds)
    assert not semble_install_ran, "uv tool install semble must not run when semble already on PATH"


def test_init_runs_gitnexus_when_not_indexed(tmp_path):
    """If .gitnexus/ does not exist, npx gitnexus analyze must run."""
    settings = tmp_path / "settings.json"

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value=None),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_analyze_ran = any(isinstance(c, list) and "gitnexus" in c and "analyze" in c for c in cmds)
    assert gitnexus_analyze_ran, "gitnexus analyze must run when .gitnexus/ does not exist"


def test_init_does_not_rescaffold_existing_vault(tmp_path):
    """On re-run, scaffold must not overwrite the existing vault."""
    from goldfishh.config import write_manifest

    project_dir = tmp_path / "goldfish"
    project_dir.mkdir()
    vaults_root = tmp_path / "vaults"
    write_manifest(
        "goldfish",
        {"last_byte_offset": 0, "bootstrap_complete": True, "semble_indexed_at": "", "last_jsonl_file": ""},
        vaults_root=vaults_root,
    )
    settings = tmp_path / "settings.json"

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.config.VAULTS_ROOT", vaults_root),
        patch("goldfishh.init.VAULTS_ROOT", vaults_root),
        patch("goldfishh.init.scaffold") as mock_scaffold,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(project_dir), settings_path=settings, vaults_root=vaults_root)

    mock_scaffold.assert_not_called()


def test_init_self_installs_goldfish_when_not_at_stable_path(tmp_path):
    """When ~/.local/bin/goldfish doesn't exist and goldfish is not on PATH, self-install must be called."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")

    def which_no_goldfish(cmd):
        return None if cmd == "goldfish" else f"/usr/bin/{cmd}"

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", side_effect=which_no_goldfish),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    self_install_ran = any(
        isinstance(c, list) and "uv" in c and "tool" in c and "install" in c and "--from" in c for c in cmds
    )
    assert self_install_ran, "uv tool install --from ... goldfish must run when stable bin missing and not on PATH"


def test_init_skips_self_install_when_stable_bin_exists(tmp_path):
    """When ~/.local/bin/goldfish exists, skip self-install."""
    stable = tmp_path / "goldfish"  # stands in for the stable path
    stable.touch()
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=stable),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    self_install_ran = any(
        isinstance(c, list) and "uv" in c and "tool" in c and "install" in c and "--from" in c for c in cmds
    )
    assert not self_install_ran, "uv tool install --from must NOT run when stable bin already exists"


def test_init_registers_omega_mcp(tmp_path):
    """omega setup --client claude-code must be called (not bare omega setup)."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    omega_mcp = any(
        isinstance(c, list) and "omega" in c and "setup" in c and "--client" in c and "claude-code" in c for c in cmds
    )
    assert omega_mcp, "omega setup --client claude-code must be called"


def test_init_registers_semble_mcp(tmp_path):
    """claude mcp add semble must be called during init."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    semble_mcp = any(
        isinstance(c, list) and "claude" in c and "mcp" in c and "add" in c and "semble" in c for c in cmds
    )
    assert semble_mcp, "claude mcp add semble must be called"


def test_init_registers_gitnexus_mcp(tmp_path):
    """npx gitnexus setup must be called during init."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    gitnexus_setup = any(isinstance(c, list) and "gitnexus" in c and "setup" in c for c in cmds)
    assert gitnexus_setup, "npx gitnexus setup must be called"


def test_init_calls_semble_init(tmp_path):
    """semble init must be called to set up the Claude Code sub-agent."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/semble"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")
    cmds = [call[0][0] for call in mock_run.call_args_list]
    semble_init_ran = any(isinstance(c, list) and "semble" in c and "init" in c for c in cmds)
    assert semble_init_ran, "semble init must be called to set up Claude Code sub-agent"


def test_init_skips_mcp_registration_if_already_registered(tmp_path):
    """When manifest mcp_registered=True, all MCP registration commands are skipped."""
    from goldfishh.config import write_manifest

    project_dir = tmp_path / "myapp"
    project_dir.mkdir()
    vaults_root = tmp_path / "vaults"
    write_manifest(
        "myapp",
        {
            "mcp_registered": True,
            "bootstrap_complete": True,
            "last_byte_offset": 0,
            "semble_indexed_at": "",
            "last_jsonl_file": "",
        },
        vaults_root=vaults_root,
    )
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    (project_dir / ".gitnexus").mkdir()
    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", vaults_root),
        patch("goldfishh.init.VAULTS_ROOT", vaults_root),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(project_dir), settings_path=settings, vaults_root=vaults_root)
    cmds = [call[0][0] for call in mock_run.call_args_list]
    omega_mcp = any(isinstance(c, list) and "omega" in c and "--client" in c for c in cmds)
    semble_mcp = any(isinstance(c, list) and "claude" in c and "mcp" in c for c in cmds)
    gitnexus_setup = any(isinstance(c, list) and "gitnexus" in c and "setup" in c for c in cmds)
    assert not omega_mcp, "omega setup --client must be skipped when mcp_registered=True"
    assert not semble_mcp, "claude mcp add must be skipped when mcp_registered=True"
    assert not gitnexus_setup, "gitnexus setup must be skipped when mcp_registered=True"


def test_init_calls_mine_project_for_existing_project(tmp_path):
    """On re-run for an existing project, mine_project must be called."""
    from goldfishh.config import write_manifest

    project_dir = tmp_path / "goldfish"
    project_dir.mkdir()
    vaults_root = tmp_path / "vaults"
    # Existing project: manifest already written with bootstrap_complete=True
    write_manifest(
        "goldfish",
        {
            "last_byte_offset": 0,
            "bootstrap_complete": True,
            "semble_indexed_at": "",
            "last_jsonl_file": "",
            "mined_sessions": [],
        },
        vaults_root=vaults_root,
    )
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    (project_dir / ".gitnexus").mkdir()

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", vaults_root),
        patch("goldfishh.init.VAULTS_ROOT", vaults_root),
        patch("goldfishh.init.mine_project") as mock_mine,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        mock_mine.return_value = 3
        run(cwd=str(project_dir), settings_path=settings, vaults_root=vaults_root)

    mock_mine.assert_called_once_with(str(project_dir))


def test_init_installs_claude_code_when_missing(tmp_path):
    """When claude CLI is absent, npm install -g @anthropic-ai/claude-code must run."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")

    def dep_missing_claude(cmd):
        return cmd != "claude"  # claude absent, all others present

    with (
        patch("goldfishh.init.check_dependency", side_effect=dep_missing_claude),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [c[0][0] for c in mock_run.call_args_list]
    claude_install = any(isinstance(c, list) and "npm" in c and "@anthropic-ai/claude-code" in c for c in cmds)
    assert claude_install, "npm install -g @anthropic-ai/claude-code must run when claude is missing"


def test_init_skips_claude_code_install_when_present(tmp_path):
    """When claude CLI is already present, npm install for Claude Code must NOT run."""
    settings = tmp_path / "settings.json"
    settings.write_text("{}")

    with (
        patch("goldfishh.init.check_dependency", return_value=True),
        patch("goldfishh.init.shutil.which", return_value="/usr/bin/omega"),
        patch("goldfishh.init.subprocess.run") as mock_run,
        patch("goldfishh.init._goldfish_stable_path", return_value=tmp_path / "nonexistent"),
        patch("goldfishh.config.VAULTS_ROOT", tmp_path / "vaults"),
        patch("goldfishh.init.VAULTS_ROOT", tmp_path / "vaults"),
    ):
        mock_run.return_value = MagicMock(returncode=0)
        run(cwd=str(tmp_path), settings_path=settings, vaults_root=tmp_path / "vaults")

    cmds = [c[0][0] for c in mock_run.call_args_list]
    claude_install = any(isinstance(c, list) and "npm" in c and "@anthropic-ai/claude-code" in c for c in cmds)
    assert not claude_install, "npm install @anthropic-ai/claude-code must NOT run when claude is present"


def test_claude_md_block_describes_four_layer_stack():
    from goldfishh.init import _CLAUDE_MD_BLOCK

    assert "Layer 0" in _CLAUDE_MD_BLOCK, "Must reference Layer 0 (MEMORY.md)"
    assert "MEMORY.md" in _CLAUDE_MD_BLOCK, "Must name MEMORY.md explicitly"
    assert "omega_welcome()" in _CLAUDE_MD_BLOCK, "Session start must call omega_welcome()"
    assert "Session Start" in _CLAUDE_MD_BLOCK, "Must have Session Start section"
    assert "Layer 1" in _CLAUDE_MD_BLOCK, "Must reference Layer 1 (tool blocks)"
    assert "Layer 2" in _CLAUDE_MD_BLOCK, "Must reference Layer 2 (goldfish)"
    assert "Layer 3" in _CLAUDE_MD_BLOCK, "Must reference Layer 3 (project)"
