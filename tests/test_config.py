from pathlib import Path

from goldfish.config import is_new_project, project_name, write_manifest, get_manifest


def test_is_new_project_returns_true_when_no_manifest(tmp_path):
    assert is_new_project("myproject", vaults_root=tmp_path) is True


def test_is_new_project_returns_false_when_manifest_exists(tmp_path):
    write_manifest("myproject", {"bootstrap_complete": True}, vaults_root=tmp_path)
    assert is_new_project("myproject", vaults_root=tmp_path) is False


def test_write_and_get_manifest_roundtrip(tmp_path):
    data = {"last_byte_offset": 48291, "bootstrap_complete": False, "semble_indexed_at": ""}
    write_manifest("myproject", data, vaults_root=tmp_path)
    result = get_manifest("myproject", vaults_root=tmp_path)
    assert result["last_byte_offset"] == 48291
    assert result["bootstrap_complete"] is False


def test_project_name_from_cwd():
    assert project_name("/home/user/goldfish") == "goldfish"
    assert project_name("/home/user/my-project") == "my-project"


def test_get_manifest_default_includes_mined_sessions(tmp_path):
    result = get_manifest("newproject", vaults_root=tmp_path)
    assert result["mined_sessions"] == []


def test_manifest_roundtrip_preserves_mined_sessions(tmp_path):
    data = {
        "mined_sessions": ["session-abc", "session-def"],
        "bootstrap_complete": True,
    }
    write_manifest("myproject", data, vaults_root=tmp_path)
    result = get_manifest("myproject", vaults_root=tmp_path)
    assert result["mined_sessions"] == ["session-abc", "session-def"]
