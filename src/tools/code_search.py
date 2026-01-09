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

    snippets = []
    for line in output.strip().split("\n"):
        if not line:
            continue

        # osgrep format: path/to/file:line [Tags] Code Snippet
        # Example: src/auth.py:42 [Definition] def validate_token(token):
        parsed = _parse_osgrep_line(line)
        if parsed:
            snippets.append(parsed)
            if len(snippets) >= max_snippets:
                break

    return snippets


def _parse_osgrep_line(line: str) -> CodeSnippet | None:
    """Parse a single line of osgrep output."""
    # Match pattern: file:line [optional tags] content
    # The file:line part is required, tags are optional
    match = re.match(r"^(.+?):(\d+)\s*(?:\[([^\]]+)\])?\s*(.*)$", line)
    if not match:
        return None

    file_path = match.group(1)
    line_num = int(match.group(2))
    tags_str = match.group(3)
    text = match.group(4).strip()

    tags = None
    if tags_str:
        tags = [t.strip() for t in tags_str.split(",")]

    return CodeSnippet(file=file_path, line=line_num, text=text, tags=tags)


def _format_snippets_for_agent(snippets: list[CodeSnippet]) -> str:
    """Format snippets as a string for the agent."""
    if not snippets:
        return "No relevant code found."

    lines = []
    for s in snippets:
        tag_str = f" [{', '.join(s.tags)}]" if s.tags else ""
        lines.append(f"- {s.file}:{s.line}{tag_str}: {s.text}")
    return "\n".join(lines)
