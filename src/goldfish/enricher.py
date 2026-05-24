import subprocess
from pathlib import Path

from goldfish.config import VAULTS_ROOT

MIN_PROMPT_WORDS = 4


def decompose(prompt: str) -> list[str]:
    """Split multi-topic prompt into discrete queries. Returns [] for short prompts."""
    if len(prompt.split()) < MIN_PROMPT_WORDS:
        return []
    try:
        from chonkie import SentenceChunker
        chunker = SentenceChunker()
        chunks = chunker(prompt)
        return [c.text for c in chunks if c.text.strip()]
    except Exception:
        return [prompt]


def enrich(prompt: str, cwd: str, project: str) -> str:
    """
    Decompose prompt and fan out to Semble (code + vault) per chunk.
    Returns formatted context block, or "" if prompt is too short or results are empty.
    """
    chunks = decompose(prompt)
    if not chunks:
        return ""

    vault_path = str(VAULTS_ROOT / project)
    sections: list[str] = []

    for chunk in chunks:
        code_result = subprocess.run(
            ["semble", "search", chunk, cwd],
            capture_output=True, check=False,
        )
        docs_result = subprocess.run(
            ["semble", "search", chunk, vault_path, "--content", "docs"],
            capture_output=True, check=False,
        )

        code_out = code_result.stdout.decode(errors="replace").strip()
        docs_out = docs_result.stdout.decode(errors="replace").strip()

        if code_out or docs_out:
            section = f"### Query: {chunk}\n"
            if code_out:
                section += f"\n**Code:**\n{code_out}\n"
            if docs_out:
                section += f"\n**Vault:**\n{docs_out}\n"
            sections.append(section)

    if not sections:
        return ""

    return "## Goldfish Context\n\n" + "\n\n".join(sections)
