import subprocess
from pathlib import Path
from typing import Optional

from goldfish.config import VAULTS_ROOT

MIN_PROMPT_WORDS = 4


def _run(cmd: list, **kwargs) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        return None


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
    """Decompose prompt and fan out to Semble (code + vault) and OMEGA (memory) per chunk."""
    chunks = decompose(prompt)
    if not chunks:
        return ""

    vault_path = str(VAULTS_ROOT / project)
    sections: list[str] = []

    for chunk in chunks:
        code_result = _run(
            ["semble", "search", chunk, cwd],
            capture_output=True, check=False,
        )
        docs_result = _run(
            ["semble", "search", chunk, vault_path, "--content", "docs"],
            capture_output=True, check=False,
        )
        mem_result = _run(
            ["omega", "query", chunk],
            capture_output=True, check=False,
        )

        code_out = code_result.stdout.decode(errors="replace").strip() if code_result else ""
        docs_out = docs_result.stdout.decode(errors="replace").strip() if docs_result else ""
        mem_out = mem_result.stdout.decode(errors="replace").strip() if mem_result and mem_result.returncode == 0 else ""

        if code_out or docs_out or mem_out:
            section = f"### Query: {chunk}\n"
            if code_out:
                section += f"\n**Code:**\n{code_out}\n"
            if docs_out:
                section += f"\n**Vault:**\n{docs_out}\n"
            if mem_out:
                section += f"\n**Memory:**\n{mem_out}\n"
            sections.append(section)

    if not sections:
        return ""

    return "## Goldfish Context\n\n" + "\n\n".join(sections)
