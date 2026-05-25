import yaml

from goldfish.vault import read_note, scaffold, write_note

FRONTMATTER = {
    "id": "decision-jwt-2026-05-24",
    "type": "decision",
    "valid_from": "2026-05-24",
    "superseded_by": None,
    "confidence": 0.95,
    "source_session": "abc123",
    "source_offset": 100,
    "related": [],
}


def test_scaffold_creates_required_dirs(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    for d in [
        "Memory/Decisions",
        "Memory/Lessons",
        "Memory/Errors",
        "Memory/Checkpoints",
        "Specs",
        "Tasks",
        "_context",
    ]:
        assert (tmp_path / "myproject" / d).is_dir()


def test_scaffold_is_idempotent(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    scaffold("myproject", vaults_root=tmp_path)  # must not raise


def test_write_note_creates_file_at_correct_path(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    write_note("myproject", "Memory/Decisions/jwt.md", FRONTMATTER, "We chose JWT.", vaults_root=tmp_path)
    assert (tmp_path / "myproject" / "Memory" / "Decisions" / "jwt.md").exists()


def test_read_note_roundtrip(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    write_note("myproject", "Memory/Decisions/jwt.md", FRONTMATTER, "We chose JWT.", vaults_root=tmp_path)
    fm, body = read_note("myproject", "Memory/Decisions/jwt.md", vaults_root=tmp_path)
    assert fm["id"] == "decision-jwt-2026-05-24"
    assert fm["superseded_by"] is None
    assert body.strip() == "We chose JWT."


def test_write_note_produces_valid_yaml_frontmatter(tmp_path):
    scaffold("myproject", vaults_root=tmp_path)
    write_note("myproject", "Memory/Decisions/jwt.md", FRONTMATTER, "body", vaults_root=tmp_path)
    content = (tmp_path / "myproject" / "Memory" / "Decisions" / "jwt.md").read_text()
    assert content.startswith("---\n")
    parts = content.split("---\n", 2)
    assert len(parts) == 3
    parsed = yaml.safe_load(parts[1])
    assert parsed["type"] == "decision"
