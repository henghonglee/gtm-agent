"""Codebase search tool using osgrep (semantic code search)."""

import re
import subprocess
from dataclasses import dataclass

from src.config import get_config


@dataclass
class CodeSnippet:
    """A code snippet from the codebase search."""

    file: str
    line: int
    text: str
    tags: list[str] | None = None


async def code_search(query: str, max_snippets: int = 6) -> list[CodeSnippet]:
    """
    Search the product codebase for relevant context using semantic search.

    Uses osgrep for natural language code search. Unlike literal text matching,
    osgrep understands concepts and behavior (e.g., "where is auth validated",
    "how are users created").

    Args:
        query: Natural language search query describing what you're looking for
        max_snippets: Maximum number of snippets to return (default 6)

    Returns:
        List of CodeSnippet objects with file, line number, text, and optional tags
    """
    config = get_config()
    repo_path = config.product_repo_path

    # Build osgrep command
    # osgrep "query" [optional_path]
    cmd = ["osgrep", query, str(repo_path)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,  # semantic search can take longer
        )
        output = result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if not output:
        return []

    # Check for indexing message
    if "Still Indexing" in output:
        return [
            CodeSnippet(
                file="",
                line=0,
                text="Codebase is still being indexed. Results may be partial.",
                tags=["warning"],
            )
        ]

    return _parse_osgrep_output(output, max_snippets)


_HEADER_RE = re.compile(r"^(.+?):(\d+)\s*(?:\[([^\]]+)\])?\s*$")


def _parse_osgrep_output(output: str, max_snippets: int) -> list[CodeSnippet]:
    """Parse osgrep's block output format.

    Each match is a header line (file:line [Tags]) followed by indented
    snippet lines, e.g.:

        src/auth.py:42 [Definition]
          def validate_token(token):
              ...

    followed by a blank line before the next match.
    """
    lines = output.split("\n")
    snippets: list[CodeSnippet] = []

    i = 0
    while i < len(lines) and len(snippets) < max_snippets:
        line = lines[i]
        is_header = bool(line.strip()) and line[:1] not in (" ", "\t")
        match = _HEADER_RE.match(line) if is_header else None

        if not match:
            i += 1
            continue

        file_path = match.group(1)
        line_num = int(match.group(2))
        tags_str = match.group(3)
        tags = [t.strip() for t in tags_str.split(",")] if tags_str else None

        i += 1
        body_lines = []
        while i < len(lines) and lines[i].strip() and lines[i][:1] in (" ", "\t"):
            body_lines.append(lines[i].strip())
            i += 1

        snippets.append(
            CodeSnippet(file=file_path, line=line_num, text="\n".join(body_lines), tags=tags)
        )

    return snippets


def _format_snippets_for_agent(snippets: list[CodeSnippet]) -> str:
    """Format snippets as a string for the agent."""
    if not snippets:
        return "No relevant code found."

    lines = []
    for s in snippets:
        tag_str = f" [{', '.join(s.tags)}]" if s.tags else ""
        lines.append(f"- {s.file}:{s.line}{tag_str}: {s.text}")
    return "\n".join(lines)
