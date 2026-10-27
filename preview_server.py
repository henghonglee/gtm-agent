"""Minimal web preview for the Twitter Reply Agent CLI.

Wraps the CLI's core agent flow (src.agent.react_to_tweet_simple) behind a
small HTTP form so the preview sandbox (which only supports a web preview
platform) can expose this CLI tool's real behavior in a browser. Always
runs with dry_run=True; no tweet is ever posted to X/Twitter from here.
"""

import html
import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from src.agent import react_to_tweet_simple
from src.tools.code_search import code_search as do_code_search, _format_snippets_for_agent

SAMPLE_TEXT = "Just shipped a new feature for semantic code search!"
SAMPLE_AUTHOR = "someone"

_MODEL_BLOCKED_MARKERS = ("api key", "authentication", "unauthorized", "invalid x-api-key")


def _looks_model_blocked(result) -> bool:
    if not result.transcript:
        return not result.success
    joined = " ".join(result.transcript).lower()
    return any(marker in joined for marker in _MODEL_BLOCKED_MARKERS)


def _page(body: str) -> str:
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>gtm-agent preview</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }}
  textarea, input {{ width: 100%; box-sizing: border-box; padding: 8px; margin-bottom: 12px; font-family: inherit; font-size: 14px; }}
  button {{ padding: 8px 16px; font-size: 14px; cursor: pointer; }}
  pre {{ background: #f5f5f5; padding: 12px; white-space: pre-wrap; word-break: break-word; }}
  .note {{ color: #555; font-size: 14px; }}
  .error {{ color: #b00020; }}
</style>
</head>
<body>
<h2>gtm-agent &mdash; Twitter Reply Agent (CLI preview)</h2>
<p class="note">
  This repository is a terminal CLI with no web UI of its own. This page is a thin preview
  wrapper around the agent's real reply flow (<code>src.agent.react_to_tweet_simple</code>),
  so it can be exercised from a browser. It always runs with <code>dry_run=True</code> &mdash;
  no reply is ever posted to X/Twitter.
</p>
{body}
</body>
</html>"""


FORM = f"""
<form method="post" action="/run">
  <label>Sample tweet author (no @)</label>
  <input name="author" value="{html.escape(SAMPLE_AUTHOR)}">
  <label>Sample tweet text</label>
  <textarea name="text" rows="3">{html.escape(SAMPLE_TEXT)}</textarea>
  <button type="submit">Run agent (dry run)</button>
</form>
<p class="note">
  The agent runs its real workflow: semantic code search over this repo (via osgrep),
  optional web search (Tavily), then drafts and would-post a reply. It needs a real
  <code>ANTHROPIC_API_KEY</code> to produce an actual model-written reply; without one it
  still runs end to end and reports the model provider's error.
</p>
"""


async def index(request: Request) -> HTMLResponse:
    return HTMLResponse(_page(FORM))


async def run(request: Request) -> HTMLResponse:
    form = await request.form()
    text = (form.get("text") or SAMPLE_TEXT).strip()
    author = (form.get("author") or SAMPLE_AUTHOR).strip()

    # Step 1: real semantic code search (osgrep), independent of any model call.
    # This runs and returns genuine results even when the model step below is blocked.
    snippets = await do_code_search(text, max_snippets=6)
    search_output = html.escape(_format_snippets_for_agent(snippets))

    # Step 2: the full agent flow (code_search + web_search + drafted reply + dry-run post).
    result = await react_to_tweet_simple("1", text, author, dry_run=True)

    lines = [
        f"success: {result.success}",
        f"error: {result.error}",
        "",
        "transcript:",
        *(result.transcript or ["(no messages)"]),
    ]
    agent_output = html.escape("\n".join(lines))

    blocked_banner = ""
    if _looks_model_blocked(result):
        blocked_banner = """
<p class="error">
  The model step is blocked: this preview's <code>ANTHROPIC_API_KEY</code> is a placeholder,
  so the Claude Agent SDK call below fails authentication before it can draft a reply. Add a
  real key in Configure &rarr; Secrets to see an actual model-written reply here. Step 1 above
  (semantic code search) does not depend on this key and ran for real.
</p>
"""

    body = f"""
<h3>Step 1 &mdash; code_search (osgrep), run directly against this repo</h3>
<p class="note">Real semantic search results for the tweet text above, independent of the model step below.</p>
<pre>{search_output}</pre>

<h3>Step 2 &mdash; full agent run (code_search + web_search + drafted reply + dry-run post)</h3>
{blocked_banner}
<pre class="{'error' if not result.success else ''}">{agent_output}</pre>
<p><a href="/">&laquo; Run again</a></p>
"""
    return HTMLResponse(_page(body))


app = Starlette(routes=[Route("/", index), Route("/run", run, methods=["POST"])])

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
