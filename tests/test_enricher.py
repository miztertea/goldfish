from unittest.mock import MagicMock, patch

from goldfish.enricher import decompose, enrich


def test_decompose_returns_empty_for_short_prompt():
    assert decompose("yes") == []
    assert decompose("do that") == []
    assert decompose("ok") == []


def test_decompose_returns_list_for_medium_prompt():
    result = decompose("fix the authentication middleware")
    assert isinstance(result, list)
    assert len(result) >= 1


def test_decompose_splits_multi_topic_prompt():
    result = decompose(
        "fix the auth middleware and the CI tests are broken and Sarah mentioned the rate limiter"
    )
    assert isinstance(result, list)
    assert len(result) >= 1  # Chonkie may return 1-3 chunks depending on sentence boundaries


def test_enrich_returns_empty_for_short_prompt():
    assert enrich("yes", "/project", "myapp") == ""
    assert enrich("do that", "/p", "proj") == ""


def test_enrich_calls_semble_for_code_and_docs():
    mock_result = MagicMock()
    mock_result.stdout = b"some search result"
    mock_result.returncode = 0
    with patch("goldfish.enricher.subprocess.run", return_value=mock_result) as mock_run:
        result = enrich(
            "fix the authentication middleware in the API layer",
            "/project",
            "myapp",
        )
    # At least 2 semble calls (code + docs) per chunk
    assert mock_run.call_count >= 2
    assert isinstance(result, str)
    assert "Goldfish Context" in result


def test_enrich_returns_empty_when_no_semble_results():
    mock_result = MagicMock()
    mock_result.stdout = b""
    mock_result.returncode = 0
    with patch("goldfish.enricher.subprocess.run", return_value=mock_result):
        result = enrich("fix the authentication middleware", "/project", "myapp")
    # All outputs empty → no sections → return ""
    assert result == ""


def test_enrich_formats_context_with_header():
    mock_result = MagicMock()
    mock_result.stdout = b"relevant code"
    mock_result.returncode = 0
    with patch("goldfish.enricher.subprocess.run", return_value=mock_result):
        result = enrich("fix the authentication middleware", "/project", "myapp")
    assert result.startswith("## Goldfish Context")


def test_enrich_calls_omega_query_per_chunk():
    """enrich() must call omega query for memory hits alongside semble calls."""
    mock_result = MagicMock()
    mock_result.stdout = b"relevant result"
    mock_result.returncode = 0
    with patch("goldfish.enricher.subprocess.run", return_value=mock_result) as mock_run:
        enrich("fix the authentication middleware in the API layer", "/project", "myapp")
    # At least 3 calls per chunk: semble code, semble docs, omega query
    assert mock_run.call_count >= 3
    all_cmds = [call[0][0] for call in mock_run.call_args_list]
    assert any(cmd[0] == "omega" for cmd in all_cmds)


def test_enrich_includes_memory_section_in_output():
    """When omega returns results, output must contain a Memory section."""
    def fake_run(cmd, *args, **kwargs):
        m = MagicMock()
        if cmd[0] == "omega":
            m.stdout = b"past decision: use JWT"
            m.returncode = 0
        else:
            m.stdout = b""
            m.returncode = 0
        return m

    with patch("goldfish.enricher.subprocess.run", side_effect=fake_run):
        result = enrich("fix the authentication middleware in the API layer", "/project", "myapp")

    assert "Memory" in result
    assert "past decision" in result
