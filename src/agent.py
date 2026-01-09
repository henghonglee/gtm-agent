"""Main Twitter Reply Agent using Claude Agent SDK."""

import json
from dataclasses import dataclass

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
)

from src.config import get_config
from src.tools.code_search import code_search as do_code_search, _format_snippets_for_agent
from src.tools.web_search import web_search as do_web_search, _format_results_for_agent
from src.tools.x_tools import x_reply as do_x_reply, Tweet


def _get_system_prompt() -> str:
    """Get the system prompt for the agent."""
    config = get_config()
    return f"""You are a Twitter reply agent for {config.product_name}.

Your goal: Write thoughtful, grounded replies to tweets.

Workflow:
1. First, use code_search to find relevant product context related to the tweet
2. Use web_search if the tweet references external topics you should verify
3. Formulate a concise reply (<280 chars) that adds value
4. Use x_reply to post the reply

Rules:
- Never invent features or make unsubstantiated claims
- Ground all claims in codebase or web search results
- Be helpful and friendly, not promotional or salesy
- If unsure about something, ask a clarifying question instead of asserting
- Keep replies concise and valuable
- Match the tone of the original tweet (casual vs professional)
"""


# Define tools for Claude Agent SDK
@tool(
    name="code_search",
    description="Semantic search of the product codebase. Use natural language queries to find code by concept or behavior (e.g., 'how is authentication handled', 'where are users created', 'pricing logic'). Returns relevant code snippets with file locations.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query describing what you're looking for in the codebase",
            },
            "max_snippets": {
                "type": "integer",
                "description": "Maximum number of snippets to return (default 6)",
                "default": 6,
            },
        },
        "required": ["query"],
    },
)
async def code_search_tool(args: dict) -> dict:
    """Tool wrapper for code_search."""
    query = args["query"]
    max_snippets = args.get("max_snippets", 6)

    snippets = await do_code_search(query, max_snippets)
    formatted = _format_snippets_for_agent(snippets)

    return {
        "content": [{"type": "text", "text": formatted}],
    }


@tool(
    name="web_search",
    description="Search the web for up-to-date context, citations, or explanations. Use this when the tweet references external topics or trends.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)
async def web_search_tool(args: dict) -> dict:
    """Tool wrapper for web_search."""
    query = args["query"]
    max_results = args.get("max_results", 5)

    results = await do_web_search(query, max_results)
    formatted = _format_results_for_agent(results)

    return {
        "content": [{"type": "text", "text": formatted}],
    }


# Global dry_run flag for x_reply tool
_dry_run_mode = False


def set_dry_run(enabled: bool) -> None:
    """Enable or disable dry run mode."""
    global _dry_run_mode
    _dry_run_mode = enabled


@tool(
    name="x_reply",
    description="Post a reply to the tweet on X/Twitter. The reply must be 280 characters or less.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The reply text (max 280 characters)",
                "maxLength": 280,
            },
        },
        "required": ["text"],
    },
)
async def x_reply_tool(args: dict) -> dict:
    """Tool wrapper for x_reply."""
    text = args["text"]

    # The tweet_id is passed via context, stored in a global
    global _current_tweet_id
    tweet_id = _current_tweet_id

    result = await do_x_reply(tweet_id, text, dry_run=_dry_run_mode)

    if _dry_run_mode:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[DRY RUN] Would post reply: {text}",
                }
            ],
        }

    return {
        "content": [
            {
                "type": "text",
                "text": f"Successfully posted reply (tweet ID: {result['id']}): {text}",
            }
        ],
    }


# Create the MCP server with our tools
_mcp_server = create_sdk_mcp_server(
    name="twitter-agent-tools",
    version="1.0.0",
    tools=[code_search_tool, web_search_tool, x_reply_tool],
)


@dataclass
class AgentResult:
    """Result from the agent."""

    success: bool
    reply_text: str | None
    reply_tweet_id: str | None
    error: str | None
    transcript: list[str]


# Global to pass tweet_id to x_reply tool
_current_tweet_id: str = ""


async def react_to_tweet(
    tweet: Tweet,
    dry_run: bool = False,
) -> AgentResult:
    """
    React to a tweet using the Claude Agent SDK.

    Args:
        tweet: The tweet to react to
        dry_run: If True, don't actually post (for testing)

    Returns:
        AgentResult with success status and reply info
    """
    global _current_tweet_id
    _current_tweet_id = tweet.id
    set_dry_run(dry_run)

    options = ClaudeAgentOptions(
        system_prompt=_get_system_prompt(),
        mcp_servers={"tools": _mcp_server},
        allowed_tools=[
            "mcp__tools__code_search",
            "mcp__tools__web_search",
            "mcp__tools__x_reply",
        ],
        max_turns=10,
    )

    prompt = f"""React to this tweet:
- Tweet ID: {tweet.id}
- Author: @{tweet.author_username or tweet.author_id}
- Text: {tweet.text}

Search for relevant context, formulate a grounded reply, and post it."""

    transcript = []

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            transcript.append(block.text)
                            print(f"Agent: {block.text}")

        return AgentResult(
            success=True,
            reply_text=transcript[-1] if transcript else None,
            reply_tweet_id=None,  # Would need to extract from tool result
            error=None,
            transcript=transcript,
        )

    except Exception as e:
        return AgentResult(
            success=False,
            reply_text=None,
            reply_tweet_id=None,
            error=str(e),
            transcript=transcript,
        )


async def react_to_tweet_simple(
    tweet_id: str,
    tweet_text: str,
    author: str,
    dry_run: bool = False,
) -> AgentResult:
    """
    Simplified interface to react to a tweet.

    Args:
        tweet_id: The tweet ID
        tweet_text: The tweet text
        author: The tweet author username
        dry_run: If True, don't actually post

    Returns:
        AgentResult with success status and reply info
    """
    tweet = Tweet(
        id=tweet_id,
        text=tweet_text,
        author_id="",
        author_username=author,
    )
    return await react_to_tweet(tweet, dry_run=dry_run)
